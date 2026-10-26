"""One read-only view of the shipped Markdown that the tests execute against.

`SKILL.md` is the entry point; the runnable code lives in `references/*.md` (progressive
disclosure). Tests need a single concatenated text so that `<!-- marker:start -->` blocks and
`## Layer N:` splits resolve exactly as they did when everything sat in one file.

Order matters: SKILL.md first, then `references/` sorted by path (so `layers/01-quote.md`
directly precedes `layers/02-research.md`).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"


def source_files():
    return [SKILL_PATH] + sorted(REFERENCES.rglob("*.md"))


SKILL = "\n\n".join(path.read_text(encoding="utf-8") for path in source_files())
