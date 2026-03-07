"""Speaking practice session -- text-based for now, audio in future."""
import json
import subprocess

from .evaluator import build_eval_prompt, parse_evaluation
from .scenarios import get_scenario


class SpeakingSession:
    def __init__(self, scenario: str = "free", model: str = "claude-sonnet-4-6"):
        self.scenario_info = get_scenario(scenario)
        self.scenario = scenario
        self.model = model
        self.turn_count = 0
        self.evaluations: list[dict] = []

    def get_opening(self) -> str:
        return self.scenario_info["opening"]

    def evaluate_response(self, user_text: str) -> dict:
        prompt = build_eval_prompt(user_text, self.scenario_info["name"])
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model",
            self.model,
            "--output-format",
            "json",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        stdout = proc.stdout.decode(errors="replace")
        evaluation = parse_evaluation(stdout)
        self.turn_count += 1
        self.evaluations.append(evaluation)
        return evaluation

    def get_summary(self) -> dict:
        if not self.evaluations:
            return {"turns": 0}
        scores = {
            k: []
            for k in ["grammar_score", "vocabulary_score", "fluency_score", "overall_score"]
        }
        for e in self.evaluations:
            for k in scores:
                if k in e and isinstance(e[k], (int, float)):
                    scores[k].append(e[k])
        return {
            "scenario": self.scenario,
            "turns": self.turn_count,
            "avg_grammar": round(
                sum(scores["grammar_score"]) / len(scores["grammar_score"]), 1
            )
            if scores["grammar_score"]
            else 0,
            "avg_vocabulary": round(
                sum(scores["vocabulary_score"]) / len(scores["vocabulary_score"]), 1
            )
            if scores["vocabulary_score"]
            else 0,
            "avg_fluency": round(
                sum(scores["fluency_score"]) / len(scores["fluency_score"]), 1
            )
            if scores["fluency_score"]
            else 0,
            "avg_overall": round(
                sum(scores["overall_score"]) / len(scores["overall_score"]), 1
            )
            if scores["overall_score"]
            else 0,
        }
