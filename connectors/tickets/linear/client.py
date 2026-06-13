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

_TEAM_LABELS_QUERY = """
query TeamLabels($teamId: String!) {
  team(id: $teamId) {
    labels {
      nodes { id name }
    }
  }
}
"""

_ISSUE_LABEL_CREATE_MUTATION = """
mutation IssueLabelCreate($input: IssueLabelCreateInput!) {
  issueLabelCreate(input: $input) {
    success
    issueLabel { id name }
  }
}
"""

_ISSUE_ADD_LABEL_MUTATION = """
mutation IssueAddLabel($id: String!, $labelId: String!) {
  issueAddLabel(id: $id, labelId: $labelId) {
    success
  }
}
"""

_COMMENT_CREATE_MUTATION = """
mutation CommentCreate($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment { id body }
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

    def list_team_labels(self, team_id: str) -> list[dict[str, Any]]:
        data = self.graphql(_TEAM_LABELS_QUERY, {"teamId": team_id})
        team = data.get("team")
        if not team:
            return []
        return team.get("labels", {}).get("nodes", [])

    def create_label(self, team_id: str, name: str) -> dict[str, Any]:
        data = self.graphql(
            _ISSUE_LABEL_CREATE_MUTATION,
            {"input": {"teamId": team_id, "name": name, "color": "#9b59b6"}},
        )
        result = data.get("issueLabelCreate") or {}
        if not result.get("success"):
            raise LinearAPIError("issueLabelCreate returned success=false")
        label = result.get("issueLabel")
        if not label:
            raise LinearAPIError("issueLabelCreate returned no label")
        return label

    def get_or_create_label(self, team_id: str, name: str) -> dict[str, Any]:
        for label in self.list_team_labels(team_id):
            if (label.get("name") or "").lower() == name.lower():
                return label
        return self.create_label(team_id, name)

    def add_label_to_issue(self, issue_id: str, label_id: str) -> None:
        data = self.graphql(_ISSUE_ADD_LABEL_MUTATION, {"id": issue_id, "labelId": label_id})
        result = data.get("issueAddLabel") or {}
        if not result.get("success"):
            raise LinearAPIError("issueAddLabel returned success=false")

    def create_comment(self, issue_id: str, body: str) -> dict[str, Any]:
        data = self.graphql(_COMMENT_CREATE_MUTATION, {"input": {"issueId": issue_id, "body": body}})
        result = data.get("commentCreate") or {}
        if not result.get("success"):
            raise LinearAPIError("commentCreate returned success=false")
        comment = result.get("comment")
        if not comment:
            raise LinearAPIError("commentCreate returned no comment")
        return comment
