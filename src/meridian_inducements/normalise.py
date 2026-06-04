"""Cross-system identifier and value normalisation."""

from __future__ import annotations

import re

# Registry uses ADV-NNN; Concur uses A-NNNNN (zero-padded). Both reduce to an int.
_ADV_RE = re.compile(r"^ADV-(\d+)$", re.IGNORECASE)
_CONCUR_RE = re.compile(r"^A-(\d+)$", re.IGNORECASE)


def to_canonical_adviser_id(value: object) -> str | None:
    """Return the canonical ``ADV-NNN`` form for either input shape, else None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    m = _ADV_RE.match(text)
    if m is None:
        m = _CONCUR_RE.match(text)
    if m is None:
        return None
    try:
        n = int(m.group(1))
    except ValueError:
        return None
    if n <= 0:
        return None
    return f"ADV-{n:03d}"


def to_concur_adviser_ref(canonical_id: str) -> str:
    """Return the Concur ``A-NNNNN`` form for a canonical id (round-trip helper)."""
    m = _ADV_RE.match(canonical_id)
    if m is None:
        raise ValueError(f"Not a canonical adviser id: {canonical_id!r}")
    return f"A-{int(m.group(1)):05d}"
