"""Claude-powered transcript refinement."""
import json
import subprocess

REFINE_PROMPT = """\
Clean up this voice transcript. Fix grammar, punctuation, and formatting.
Output format: {format_type}

Transcript: "{text}"

Return ONLY the cleaned text, nothing else.
"""


def refine_transcript(text: str, format_type: str = "general") -> str:
    prompt = REFINE_PROMPT.format(text=text, format_type=format_type)
    cmd = ["claude", "-p", prompt, "--output-format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        stdout = proc.stdout.decode(errors="replace")
        data = json.loads(stdout)
        return data.get("result", text)
    except Exception:
        return text
