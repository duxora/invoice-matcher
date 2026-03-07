"""Claude-powered speech evaluation."""

EVAL_PROMPT = """\
You are an English speaking coach for a non-native speaker. Evaluate their response.

Scenario: {scenario}
User said: "{user_text}"

Evaluate and return ONLY JSON:
{{
  "grammar_score": <1-5>,
  "grammar_corrections": ["correction1", "correction2"],
  "vocabulary_score": <1-5>,
  "vocabulary_suggestions": ["better word/phrase suggestions"],
  "fluency_score": <1-5>,
  "fluency_feedback": "brief feedback on naturalness",
  "overall_score": <1.0-5.0>,
  "natural_response": "Your conversational response continuing the scenario (2-3 sentences)",
  "tip": "One specific improvement tip"
}}
"""


def build_eval_prompt(user_text: str, scenario: str = "free conversation") -> str:
    return EVAL_PROMPT.format(user_text=user_text, scenario=scenario)


def parse_evaluation(raw: str) -> dict:
    import json

    try:
        data = json.loads(raw)
        if "result" in data:
            return json.loads(data["result"])
        return data
    except (json.JSONDecodeError, TypeError):
        return {
            "grammar_score": 0,
            "grammar_corrections": [],
            "vocabulary_score": 0,
            "vocabulary_suggestions": [],
            "fluency_score": 0,
            "fluency_feedback": "",
            "overall_score": 0,
            "natural_response": "",
            "tip": "Could not parse evaluation.",
        }
