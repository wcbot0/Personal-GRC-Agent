"""Linear GraphQL API client (fixed team scope)."""
from __future__ import annotations

from typing import Any

import httpx

LINEAR_API_URL = "https://api.linear.app/graphql"

_ISSUES_QUERY = """
query TeamIssues($teamId: String!, $first: Int!) {
  team(id: $teamId) {
    issues(first: $first) {
      nodes {
        id
        identifier
        title
        description
        url
        state { name }
        assignee { id name email }
      }
    }
  }
}
"""

_ISSUE_CREATE_MUTATION = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      url
      title
      assignee { id name }
    }
  }
}
"""

_ISSUE_UPDATE_MUTATION = """
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      identifier
      url
      assignee { id name }
    }
  }
}
"""


class LinearAPIError(RuntimeError):
    pass


class LinearGraphQLClient:
    def __init__(self, api_key: str, *, http_client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self._http = http_client or httpx.Client(timeout=30.0)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self._http.post(
            LINEAR_API_URL,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        payload = resp.json()
        if errors := payload.get("errors"):
            raise LinearAPIError(str(errors))
        return payload.get("data") or {}

    def list_issues(self, team_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        data = self.graphql(_ISSUES_QUERY, {"teamId": team_id, "first": limit})
        team = data.get("team")
        if not team:
            return []
        return team.get("issues", {}).get("nodes", [])

    def create_issue(
        self,
        team_id: str,
        title: str,
        description: str,
        *,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        issue_input: dict[str, Any] = {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
        if project_id:
            issue_input["projectId"] = project_id
        data = self.graphql(_ISSUE_CREATE_MUTATION, {"input": issue_input})
        result = data.get("issueCreate") or {}
        if not result.get("success"):
            raise LinearAPIError("issueCreate returned success=false")
        issue = result.get("issue")
        if not issue:
            raise LinearAPIError("issueCreate returned no issue")
        return issue

    def assign_issue(self, issue_id: str, assignee_id: str) -> dict[str, Any]:
        data = self.graphql(
            _ISSUE_UPDATE_MUTATION,
            {"id": issue_id, "input": {"assigneeId": assignee_id}},
        )
        result = data.get("issueUpdate") or {}
        if not result.get("success"):
            raise LinearAPIError("issueUpdate returned success=false")
        issue = result.get("issue")
        if not issue:
            raise LinearAPIError("issueUpdate returned no issue")
        return issue
