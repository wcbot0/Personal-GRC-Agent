"""questionnaire: CAIQ/SIG-style Q&A grounded in brain/ with citations."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from spa.paths import BRAIN_DIR


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    from spa.llm.skill_engine import maybe_run_llm

    return maybe_run_llm("questionnaire", content, context, _run_heuristic)


def _parse_questions(content: str) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^(?:Q(\d+)|(\d+)[.)])\s*[:\-]?\s*(.+)$", stripped, re.I)
        if match:
            qid = match.group(1) or match.group(2) or str(idx)
            text = match.group(3).strip()
        elif stripped.startswith("- "):
            qid = str(idx)
            text = stripped[2:].strip()
        else:
            continue
        if text:
            questions.append({"question_id": f"Q{qid}", "question": text})
    return questions


def _brain_policy_files() -> list[Path]:
    policies = BRAIN_DIR / "03-policies"
    if not policies.exists():
        return []
    return sorted(policies.glob("*.md"))


def _score_policy_match(question: str, policy_text: str) -> float:
    q_tokens = {t.lower() for t in re.findall(r"[A-Za-z]{4,}", question)}
    if not q_tokens:
        return 0.0
    p_lower = policy_text.lower()
    hits = sum(1 for t in q_tokens if t in p_lower)
    return hits / len(q_tokens)


def _find_citations(question: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for path in _brain_policy_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        score = _score_policy_match(question, text)
        if score >= 0.25:
            rel = str(path.relative_to(BRAIN_DIR.parent))
            hits.append({"path": rel, "score": score, "excerpt": text[:400]})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:3]


def _draft_answer(question: str, citations: list[dict[str, Any]]) -> tuple[str, float]:
    if not citations:
        return "", 0.0
    top = citations[0]
    excerpt = top.get("excerpt", "")
    sentences = [s.strip() for s in re.split(r"[.\n]+", excerpt) if len(s.strip()) > 40]
    if sentences:
        answer = sentences[0][:500]
        if not answer.endswith("."):
            answer += "."
        answer += f" (Source: {top['path']})"
        confidence = min(0.95, 0.55 + top["score"] * 0.4)
        return answer, round(confidence, 2)
    return f"See policy reference: {top['path']}", 0.5


def _run_heuristic(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    q_type = "SIG"
    if re.search(r"(?i)caiq|consensus assessments", content):
        q_type = "CAIQ"

    parsed = _parse_questions(content)
    if not parsed:
        parsed = [{"question_id": "Q1", "question": content.strip()[:500]}]

    answers: list[dict[str, Any]] = []
    control_tags: set[str] = set()

    keyword_tags = {
        "mfa": ["SOC2:CC6.1", "CSF:PR.AC", "800-53:IA-2"],
        "encrypt": ["SOC2:CC6.7", "CSF:PR.DS", "800-53:SC-28"],
        "access": ["SOC2:CC6.1", "CSF:PR.AC", "800-53:AC-2"],
        "log": ["SOC2:CC7.2", "CSF:DE.AE", "800-53:AU-2"],
        "incident": ["SOC2:CC7.3", "CSF:RS.RP", "800-53:IR-4"],
    }

    for item in parsed:
        question = item["question"]
        citations_raw = _find_citations(question)
        citation_paths = [c["path"] for c in citations_raw]
        answer_text, confidence = _draft_answer(question, citations_raw)
        needs_human = not citation_paths or confidence < 0.6

        if needs_human:
            answer_text = answer_text or "Insufficient brain coverage — human review required."
            citation_paths = []

        for key, tags in keyword_tags.items():
            if key in question.lower():
                control_tags.update(tags)

        answers.append(
            {
                "question_id": item["question_id"],
                "question": question,
                "answer": answer_text,
                "citations": citation_paths,
                "confidence": confidence,
                "needs_human": needs_human,
            }
        )

    if not control_tags:
        control_tags.update(["CSF:GV.PO", "SOC2:CC1.1", "800-53:PL-2"])

    return {
        "skill": "questionnaire",
        "questionnaire_type": q_type,
        "answers": answers,
        "summary": {
            "total": len(answers),
            "needs_human": sum(1 for a in answers if a["needs_human"]),
            "cited": sum(1 for a in answers if a["citations"]),
        },
        "control_tags": sorted(control_tags),
    }
