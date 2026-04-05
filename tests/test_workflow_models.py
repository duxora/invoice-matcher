from claude_scheduler.workflow.models import Workflow, Step


def test_workflow_creation():
    steps = [
        Step(order=1, description="Pull latest changes", tools="Bash(git)"),
        Step(order=2, description="Run linting", tools="Bash(ruff)"),
    ]
    wf = Workflow(
        name="Daily Code Check",
        trigger="daily 09:00",
        steps=steps,
        security_level="medium",
    )
    assert wf.slug == "daily-code-check"
    assert len(wf.steps) == 2
    assert wf.steps[0].tools == "Bash(git)"


def test_step_to_prompt():
    step = Step(order=1, description="Check for TODO comments in Python files", tools="Read,Grep,Glob")
    prompt = step.to_prompt(context="Previous step found 3 modified files.")
    assert "Check for TODO comments" in prompt
    assert "Previous step found 3 modified files" in prompt


def test_workflow_defaults():
    wf = Workflow(name="Test", trigger="daily 09:00", steps=[])
    assert wf.security_level == "medium"
    assert wf.on_failure == "retry_once"
    assert wf.allowed_tools == "Read,Grep,Glob"
