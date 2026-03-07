"""Core matching logic: rename plan generation and execution."""
from pathlib import Path

DEFAULT_PATTERN = "{invoice}"
DEFAULT_SEPARATOR = "_"


def generate_rename_plan(
    matches: dict[str, list[str]],
    pattern: str = DEFAULT_PATTERN,
    separator: str = DEFAULT_SEPARATOR,
) -> dict[str, str]:
    """Generate a mapping of old_filename -> new_filename.

    Pattern placeholders:
      {invoice}  — matched invoice number(s), joined by separator if multiple
      {original} — original filename without extension

    The original file extension is always preserved automatically.
    Uses the master list version of invoice numbers (from fuzzy matching).
    """
    plan = {}
    for filename, invoices in matches.items():
        if not invoices:
            continue
        invoice_str = separator.join(invoices)
        original_path = Path(filename)
        original_stem = original_path.stem
        extension = original_path.suffix  # preserves case: .pdf, .PDF
        new_stem = pattern.format(invoice=invoice_str, original=original_stem)
        plan[filename] = new_stem + extension
    return plan


def execute_renames(
    directory: Path, plan: dict[str, str]
) -> dict[str, list[dict]]:
    """Rename files according to plan. Returns results with renamed/skipped lists."""
    results: dict[str, list[dict]] = {"renamed": [], "skipped": []}
    for old_name, new_name in plan.items():
        old_path = directory / old_name
        new_path = directory / new_name
        if new_path.exists():
            results["skipped"].append({
                "old": old_name, "new": new_name, "reason": "target already exists"
            })
            continue
        if not old_path.exists():
            results["skipped"].append({
                "old": old_name, "new": new_name, "reason": "source not found"
            })
            continue
        old_path.rename(new_path)
        results["renamed"].append({"old": old_name, "new": new_name})
    return results
