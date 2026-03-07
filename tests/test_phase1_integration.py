"""Phase 1 integration tests -- workflow + gateway working together."""

from pathlib import Path

from claude_scheduler.gateway.middleware import GatewayMiddleware
from claude_scheduler.gateway.policy import load_policies
from claude_scheduler.workflow.models import Workflow
from claude_scheduler.workflow.parser import parse_workflow

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_parse_example_workflow():
    wf = parse_workflow(EXAMPLES / "workflows" / "daily-code-check.workflow")
    assert wf.name == "Daily Code Quality Check"
    assert len(wf.steps) == 4


def test_load_example_policies():
    policies = load_policies(EXAMPLES / "policies" / "default.toml")
    assert len(policies) == 3
    assert policies["high"].network_isolation is True


def test_workflow_with_gateway(tmp_path):
    wf = parse_workflow(EXAMPLES / "workflows" / "daily-code-check.workflow")
    policies = load_policies(EXAMPLES / "policies" / "default.toml")
    mw = GatewayMiddleware(policy=policies[wf.security_level], audit_dir=tmp_path)

    # Step tools should be allowed
    assert mw.check("test", "Read", "src/main.py").allowed is True
    assert mw.check("test", "Grep", "TODO").allowed is True

    # Secrets should be denied
    assert mw.check("test", "Read", ".env").allowed is False

    # Dangerous bash should be denied
    assert mw.check("test", "Bash", "rm -rf /").allowed is False
