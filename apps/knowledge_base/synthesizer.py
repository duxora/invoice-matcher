"""Claude-powered synthesis from multiple notes."""

import json
import subprocess

SYNTH_PROMPT = """\
Based on these notes from my knowledge base, answer the question.

Question: {question}

Notes:
{notes_text}

Provide a comprehensive answer citing which notes support each point.
"""


def build_synthesis_prompt(question: str, notes: list[dict]) -> str:
    notes_text = "\n\n---\n\n".join(
        f"**{n['title']}** ({n['path']})\n{n.get('content', n.get('snippet', ''))[:1000]}"
        for n in notes
    )
    return SYNTH_PROMPT.format(question=question, notes_text=notes_text)


def synthesize(
    question: str, notes: list[dict], model: str = "claude-sonnet-4-6"
) -> str:
    prompt = build_synthesis_prompt(question, notes)
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        data = json.loads(proc.stdout.decode(errors="replace"))
        return data.get("result", "No result")
    except Exception as e:
        return f"Synthesis failed: {e}"
