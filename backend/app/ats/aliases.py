"""Keyword alias table for literal ATS-style matching — SPEC 附录 F.5 TASK-C02.

Not exhaustive by design; extend as real mismatches are observed in
practice. Matching stays literal/word-boundary based — this table maps
known abbreviation ↔ full-form pairs, it does NOT introduce semantic
similarity (that would defeat the point of this module, see F.2).
"""

ALIASES: dict[str, list[str]] = {
    "kubernetes": ["k8s"],
    "javascript": ["js"],
    "typescript": ["ts"],
    "machine learning": ["ml"],
    "natural language processing": ["nlp"],
    "artificial intelligence": ["ai"],
    "continuous integration": ["ci"],
    "continuous deployment": ["cd"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "postgresql": ["postgres"],
    "user interface": ["ui"],
    "user experience": ["ux"],
    "large language model": ["llm"],
}


def get_alias_group(keyword: str) -> list[str]:
    """Every literal form (including `keyword` itself) that counts as a
    hit for `keyword` — covers both canonical→alt and alt→canonical."""
    normalized = keyword.strip().lower()
    forms = {normalized}

    if normalized in ALIASES:
        forms.update(ALIASES[normalized])

    for canonical, alts in ALIASES.items():
        if normalized in alts:
            forms.add(canonical)
            forms.update(alts)

    return sorted(forms)
