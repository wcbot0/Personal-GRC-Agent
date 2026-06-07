"""Linear live ticket adapter — gated writes via ToolGuard + approved CPO."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from connectors.interfaces.ticket import TicketCapabilities, TicketConnector
from connectors.tickets.linear.client import LinearGraphQLClient
from connectors.tickets.linear.config import LinearConfig, LinearConfigError
from spa.tools.guard import ToolBlockedError
from spa.tools.write import guarded_write

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

_CREATE_LIVE_TOOL = "create_ticket_live"
_ASSIGN_TOOL = "assign_human"


class LinearTicketProvider(TicketConnector):
    def __init__(
        self,
        guard: "ToolGuard | None" = None,
        *,
        config: LinearConfig | None = None,
        client: LinearGraphQLClient | None = None,
    ) -> None:
        super().__init__(
            provider="linear",
            enabled=True,
            capabilities=TicketCapabilities(read=True, create_draft=False, create_live=True),
            gated_capabilities=["create_live", "assign", "transition"],
        )
        self.guard = guard
        self._config = config
        self._client = client

    def _load_config(self) -> LinearConfig:
        if self._config is None:
            self._config = LinearConfig.from_env()
        return self._config

    def _get_client(self) -> LinearGraphQLClient:
        if self._client is None:
            cfg = self._load_config()
            self._client = LinearGraphQLClient(cfg.api_key)
        return self._client

    def _emit_connector_audit(
        self,
        operation: str,
        *,
        status: str,
        tool_name: str,
        risk_class: str,
        cpo_id: str | None = None,
        outputs: dict[str, Any] | None = None,
    ) -> None:
        if not self.guard:
            return
        payload = {"status": status, "provider": "linear"}
        if outputs:
            payload.update(outputs)
        self.guard.audit.emit(
            f"ticket_{operation}",
            task_class="connector",
            risk_class=risk_class,
            tools_called=[tool_name],
            approval_required=True,
            cpo_id=cpo_id,
            outputs=payload,
        )

    def _refuse_gated(
        self,
        operation: str,
        tool_name: str,
        risk_class: str,
        *,
        cpo_id: str | None = None,
        reason: str,
    ) -> None:
        self._emit_connector_audit(
            operation,
            status="refused",
            tool_name=tool_name,
            risk_class=risk_class,
            cpo_id=cpo_id,
            outputs={"reason": reason},
        )
        raise ToolBlockedError(reason, cpo_id=cpo_id)

    def read_tickets(self, query: str | None = None) -> list[dict[str, Any]]:
        cfg = self._load_config()
        issues = self._get_client().list_issues(cfg.team_id)
        if query:
            q = query.lower()
            issues = [
                issue
                for issue in issues
                if q in (issue.get("title") or "").lower()
                or q in (issue.get("description") or "").lower()
                or q in (issue.get("identifier") or "").lower()
            ]
        return [
            {
                "id": issue.get("identifier") or issue.get("id"),
                "linear_id": issue.get("id"),
                "title": issue.get("title"),
                "description": issue.get("description"),
                "url": issue.get("url"),
                "status": (issue.get("state") or {}).get("name"),
                "assignee": (issue.get("assignee") or {}).get("name") or "unassigned",
                "team_id": cfg.team_id,
            }
            for issue in issues
        ]

    def create_draft(self, ticket: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "Linear provider does not support local drafts; use create_live with an approved CPO"
        )

    def create_live(self, ticket: dict[str, Any], *, cpo_id: str | None = None) -> dict[str, Any]:
        cfg = self._load_config()
        if not self.guard or not cpo_id:
            self._refuse_gated(
                "create_live",
                _CREATE_LIVE_TOOL,
                "A4",
                cpo_id=cpo_id,
                reason=f"{_CREATE_LIVE_TOOL} requires approved CPO",
            )

        try:
            self.guard.check_allowed(_CREATE_LIVE_TOOL, cpo_id=cpo_id)
        except ToolBlockedError as exc:
            self._refuse_gated(
                "create_live",
                _CREATE_LIVE_TOOL,
                "A4",
                cpo_id=cpo_id,
                reason=str(exc),
            )

        title = ticket.get("title") or ticket.get("id") or "AI-proposed ticket"
        description = ticket.get("description") or ticket.get("rationale") or ""

        def _write() -> dict[str, Any]:
            issue = self._get_client().create_issue(
                cfg.team_id,
                title,
                description,
                project_id=cfg.project_id,
            )
            result = {
                "provider": "linear",
                "path": issue.get("url"),
                "ticket": {
                    "id": issue.get("identifier") or issue.get("id"),
                    "linear_id": issue.get("id"),
                    "title": issue.get("title") or title,
                    "description": description,
                    "status": "created",
                    "assignee": (issue.get("assignee") or {}).get("name") or "unassigned",
                    "team_id": cfg.team_id,
                },
            }
            if cfg.project_id:
                result["ticket"]["project_id"] = cfg.project_id
            self._emit_connector_audit(
                "create_live",
                status="executed",
                tool_name=_CREATE_LIVE_TOOL,
                risk_class="A4",
                cpo_id=cpo_id,
                outputs={
                    "ticket_id": result["ticket"]["id"],
                    "linear_id": result["ticket"]["linear_id"],
                    "team_id": cfg.team_id,
                },
            )
            return result

        return guarded_write(
            self.guard,
            _CREATE_LIVE_TOOL,
            _write,
            cpo_id=cpo_id,
            preview=ticket.get("id", title),
            audit_outputs=lambda result: {
                "provider": result["provider"],
                "path": result["path"],
                "ticket_id": result["ticket"].get("id"),
                "team_id": cfg.team_id,
            },
        )

    def assign(
        self,
        ticket_id: str,
        assignee: str,
        *,
        cpo_id: str | None = None,
    ) -> dict[str, Any]:
        cfg = self._load_config()
        if not self.guard or not cpo_id:
            self._refuse_gated(
                "assign",
                _ASSIGN_TOOL,
                "A3",
                cpo_id=cpo_id,
                reason=f"{_ASSIGN_TOOL} requires approved CPO",
            )

        try:
            self.guard.check_allowed(_ASSIGN_TOOL, cpo_id=cpo_id)
        except ToolBlockedError as exc:
            self._refuse_gated(
                "assign",
                _ASSIGN_TOOL,
                "A3",
                cpo_id=cpo_id,
                reason=str(exc),
            )

        def _write() -> dict[str, Any]:
            issue = self._get_client().assign_issue(ticket_id, assignee)
            result = {
                "provider": "linear",
                "ticket_id": issue.get("identifier") or issue.get("id"),
                "linear_id": issue.get("id"),
                "assignee": (issue.get("assignee") or {}).get("name") or assignee,
                "url": issue.get("url"),
            }
            self._emit_connector_audit(
                "assign",
                status="executed",
                tool_name=_ASSIGN_TOOL,
                risk_class="A3",
                cpo_id=cpo_id,
                outputs={
                    "ticket_id": result["ticket_id"],
                    "linear_id": result["linear_id"],
                    "assignee": result["assignee"],
                },
            )
            return result

        return guarded_write(
            self.guard,
            _ASSIGN_TOOL,
            _write,
            cpo_id=cpo_id,
            preview=f"{ticket_id}->{assignee}",
            audit_outputs=lambda result: {
                "provider": result["provider"],
                "ticket_id": result["ticket_id"],
                "assignee": result["assignee"],
            },
        )


__all__ = ["LinearConfigError", "LinearTicketProvider"]
