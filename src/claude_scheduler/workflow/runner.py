"""Execute workflows as step pipelines."""
from pathlib import Path

from claude_scheduler.core.models import Task
from claude_scheduler.core.executor import execute_task
from .models import Workflow


class WorkflowRunner:
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir

    def _step_to_task(self, workflow: Workflow, step, context: str = "") -> Task:
        prompt = step.to_prompt(context=context)
        return Task(
            name=f"{workflow.slug}--step-{step.order}",
            schedule=workflow.trigger,
            prompt=prompt,
            file_path=Path(f"<workflow:{workflow.slug}>"),
            workdir=workflow.workdir,
            tools=step.tools or workflow.allowed_tools,
            max_turns=step.max_turns,
            model=workflow.model,
            timeout=step.timeout,
            security_level=workflow.security_level,
        )

    def run(self, workflow: Workflow) -> dict:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        step_results = []
        context = ""

        for step in workflow.steps:
            task = self._step_to_task(workflow, step, context=context)
            result = execute_task(task, self.logs_dir)
            step_results.append({
                "step": step.order,
                "description": step.description,
                **result,
            })

            if result["status"] != "success":
                return {
                    "status": "failed",
                    "failed_step": step.order,
                    "step_results": step_results,
                }

            context = result.get("stdout", "")

        return {"status": "success", "step_results": step_results}
