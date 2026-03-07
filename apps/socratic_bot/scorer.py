"""Score argument quality from debate history."""
import json

SCORING_PROMPT = """\
Evaluate the USER's argumentation quality in this debate. Score 1-5 for each:

Debate transcript:
{transcript}

Return ONLY JSON:
{{"logic": <1-5>, "evidence": <1-5>, "counterarguments": <1-5>, "clarity": <1-5>, "overall": <1.0-5.0>, "feedback": "<2 sentences>"}}
"""


def build_scoring_prompt(history: list[dict]) -> str:
    transcript = "\n".join(
        f"{'User' if h['role'] == 'user' else 'Bot'}: {h['content']}"
        for h in history
    )
    return SCORING_PROMPT.format(transcript=transcript)


def parse_score(raw: str) -> dict:
    try:
        try:
            data = json.loads(raw)
            if "result" in data:
                return json.loads(data["result"])
            return data
        except (json.JSONDecodeError, TypeError):
            pass
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"logic": 0, "evidence": 0, "counterarguments": 0,
                "clarity": 0, "overall": 0, "feedback": "Could not parse score."}
