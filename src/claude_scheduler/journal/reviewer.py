"""Claude-powered writing and reasoning review."""

REVIEW_PROMPT = """\
Review this journal entry for BOTH English quality and critical thinking.

Entry:
---
{text}
---

Return ONLY JSON:
{{
  "grammar_score": <1-5>,
  "grammar_issues": ["issue1", "issue2"],
  "vocabulary_score": <1-5>,
  "vocabulary_suggestions": ["word1 -> better_word1"],
  "reasoning_score": <1-5>,
  "reasoning_feedback": "brief feedback on argument quality",
  "logical_fallacies": ["fallacy if any"],
  "socratic_questions": ["follow-up question 1", "follow-up question 2"],
  "overall_feedback": "2-3 sentence summary"
}}
"""


def build_review_prompt(text: str) -> str:
    """Build a review prompt for the given journal entry text."""
    return REVIEW_PROMPT.format(text=text)
