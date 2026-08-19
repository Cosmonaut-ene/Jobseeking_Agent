"""Tests for TailorAgent._validate_bullets (source_raw fabrication check).

Merged in from feat/tailor/source-raw-validation (PR #12) as a
prerequisite for TASK-C04, which builds an iteration loop around this
function's output and needs it under test coverage first.
"""
from backend.app.agents.tailor import _validate_bullets


def test_no_warning_when_numbers_match_source():
    tailored = {
        "tailored_projects": [
            {
                "name": "API Platform",
                "bullets": [
                    {"rewritten": "Served 10k requests/day", "source_raw": "Served 10k requests/day"},
                ],
            }
        ]
    }
    assert _validate_bullets(tailored) == []


def test_no_warning_when_rewritten_has_no_new_numbers():
    tailored = {
        "tailored_projects": [
            {
                "name": "API Platform",
                "bullets": [
                    {"rewritten": "Led development of the API platform", "source_raw": "Built the API"},
                ],
            }
        ]
    }
    assert _validate_bullets(tailored) == []


def test_warning_when_rewritten_adds_fabricated_number():
    tailored = {
        "tailored_projects": [
            {
                "name": "API Platform",
                "bullets": [
                    {"rewritten": "Served 10k requests/day", "source_raw": "Served many requests"},
                ],
            }
        ]
    }
    warnings = _validate_bullets(tailored)
    assert len(warnings) == 1
    assert "API Platform" in warnings[0]
    assert "10k" in warnings[0]


def test_multiple_projects_and_bullets_all_checked():
    tailored = {
        "tailored_projects": [
            {
                "name": "Project A",
                "bullets": [{"rewritten": "Improved performance by 50%", "source_raw": "Improved performance"}],
            },
            {
                "name": "Project B",
                "bullets": [{"rewritten": "Managed a team of 5", "source_raw": "Managed a team of 5"}],
            },
        ]
    }
    warnings = _validate_bullets(tailored)
    assert len(warnings) == 1
    assert "Project A" in warnings[0]
    # _NUMBER_RE's trailing \b only holds after a word-char suffix (k/x),
    # not after a symbol like '%' — the digits are still caught (that's
    # what matters for fabrication detection), the '%' itself just isn't
    # part of the captured token. Documenting actual behavior, not the
    # ideal — fixing the regex is out of scope here.
    assert "50" in warnings[0]


def test_empty_input_returns_no_warnings():
    assert _validate_bullets({}) == []
    assert _validate_bullets({"tailored_projects": []}) == []
