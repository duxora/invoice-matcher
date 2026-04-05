from claude_scheduler.workflow.sop_converter import (
    build_convert_prompt,
    generate_workflow_file,
    parse_workflow_json,
)


def test_build_convert_prompt():
    sop = "Every morning, check server logs and restart failed services."
    prompt = build_convert_prompt(sop)
    assert "server logs" in prompt
    assert "JSON" in prompt


def test_parse_workflow_json_valid():
    raw = (
        '{"name": "Log Check", "trigger": "schedule: daily 08:00", '
        '"steps": ["Check logs", "Restart services"], '
        '"security_level": "medium", "on_failure": "notify"}'
    )
    data = parse_workflow_json(raw)
    assert data["name"] == "Log Check"
    assert len(data["steps"]) == 2


def test_parse_workflow_json_invalid():
    data = parse_workflow_json("not json")
    assert data == {}


def test_generate_workflow_file():
    data = {
        "name": "Log Check",
        "trigger": "schedule: daily 08:00",
        "steps": ["Check logs", "Restart services"],
        "security_level": "medium",
        "on_failure": "notify",
    }
    content = generate_workflow_file(data)
    assert "# Log Check" in content
    assert "1. Check logs" in content
    assert "2. Restart services" in content
    assert "level: medium" in content


def test_generate_workflow_defaults():
    data = {}
    content = generate_workflow_file(data)
    assert "# Untitled Workflow" in content
    assert "level: high" in content  # default to high security
