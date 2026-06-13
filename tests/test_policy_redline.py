"""policy-redline skill security and slug tests."""
from __future__ import annotations

from pathlib import Path

from spa.skills.policy_redline import run


def test_policy_redline_sanitizes_traversal_policy_name(tmp_path: Path):
    out_dir = tmp_path / "proposals"
    content = "Policy: ../../etc/passwd\nRequire MFA for all admins."

    output = run(content, context={"output_dir": out_dir})

    slug = output["policy_name"]
    assert ".." not in slug
    assert "/" not in slug
    assert "\\" not in slug
    assert slug == "etc-passwd"

    redline_path = out_dir / "03-policies" / "proposals" / f"{slug}-redline.md"
    pr_path = out_dir / f"draft-pr-body-{slug}.md"
    assert redline_path.exists()
    assert pr_path.exists()
    assert redline_path.resolve().is_relative_to((out_dir / "03-policies" / "proposals").resolve())
    assert pr_path.resolve().is_relative_to(out_dir.resolve())


def test_policy_redline_empty_policy_name_falls_back_to_default(tmp_path: Path):
    out_dir = tmp_path / "proposals"
    content = "Policy: !!!\nEmpty slug should use default."

    output = run(content, context={"output_dir": out_dir})

    assert output["policy_name"] == "access-control-policy"
    redline_path = out_dir / "03-policies" / "proposals" / "access-control-policy-redline.md"
    assert redline_path.exists()
