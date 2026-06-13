"""Secret scanner behavior tests."""
from __future__ import annotations

from spa.lint.secrets import scan_text_for_secrets


def test_scan_skips_redaction_placeholder_match_only():
    text = (
        "api_key=[REDACTED_SECRET]\n"
        'password = "super_secret_key_1234567890"\n'
    )
    hits = scan_text_for_secrets(text)
    assert len(hits) == 1
    assert hits[0][1] == 2


def test_scan_finds_secret_on_line_with_other_redacted_content():
    text = (
        "note: prior value was [REDACTED_AWS_KEY]\n"
        "AKIAIOSFODNN7EXAMPLE\n"
    )
    hits = scan_text_for_secrets(text)
    assert any(label == "AWS access key" and line_no == 2 for label, line_no in hits)


def test_scan_matches_broad_private_key_headers():
    text = "-----BEGIN OPENSSH PRIVATE KEY-----\nMIIE...\n"
    hits = scan_text_for_secrets(text)
    assert hits == [("Private key block", 1)]

    text = "-----BEGIN PGP PRIVATE KEY BLOCK-----\nVersion: GnuPG v1\n"
    hits = scan_text_for_secrets(text)
    assert hits == [("PGP private key block", 1)]
