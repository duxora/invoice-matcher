# PM in the AI Era Course — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a 20-day study course on AI-era project management, delivered daily at 7:30 AM via claude-scheduler with pre-written lessons + AI-generated reflections.

**Architecture:** 20 markdown lesson files stored in `~/.config/claude-scheduler/courses/pm-ai-era/lessons/`. A scheduler `.task` file runs daily at 07:30, reads `progress.json` for the current day, reads the lesson, generates personalized recall quiz + reflection via Claude, writes the enriched output to `~/workspace/study/pm/`, and advances the counter.

**Tech Stack:** claude-scheduler (.task file), Claude CLI (for AI enrichment), JSON (progress tracking), Markdown (lesson content)

---

### Task 1: Create directory structure and progress.json

**Files:**
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/` (directory)
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/progress.json`
- Create: `~/workspace/study/pm/` (directory)

**Step 1: Create all directories**

```bash
mkdir -p ~/.config/claude-scheduler/courses/pm-ai-era/lessons
mkdir -p ~/workspace/study/pm
```

**Step 2: Create progress.json**

```json
{
  "current_day": 1,
  "total_days": 20,
  "completed": [],
  "started_at": null,
  "project_name": "",
  "project_description": "",
  "feedback": []
}
```

Write to: `~/.config/claude-scheduler/courses/pm-ai-era/progress.json`

**Step 3: Commit**

```bash
# Nothing to commit to repo — these are user-local files
```

---

### Task 2: Write Week 1 lessons (Days 1-5)

**Files:**
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/01-the-new-pm-mindset.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/02-idea-to-spec.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/03-scoping-with-ai-estimation.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/04-architecture-decisions-at-ai-speed.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/05-capstone-spec-your-idea.md`

Each lesson follows this template:

```markdown
# Day N: Title

> Week 1 — AI-Augmented Planning

## Key Insight

[One powerful idea, 2 min read]

## Deep Dive

[Main content, 8 min read. Concepts, frameworks, real examples.
Cover both solo-project and work-initiative perspectives.]

## AI in Action

[Practical AI workflow for this PM skill, 3 min read.
Include actual prompt examples the reader can try.]

## Quick Win

[One concrete thing to apply today, 2 min read]

---
<!-- RECALL_QUESTIONS
Q1: [question about this lesson for tomorrow's quiz]
Q2: [question about this lesson for tomorrow's quiz]
Q3: [question about this lesson for tomorrow's quiz]
-->

<!-- NEXT_TEASER: [One-sentence hook for tomorrow's lesson] -->
```

Write full lesson content for each of the 5 files. Content guidelines:
- Target audience: intermediate software engineer PM (knows sprints, wants AI adaptation)
- Dual perspective: solo side projects AND work initiatives
- Practical over theoretical — frameworks with examples
- AI tools referenced: Claude Code, Claude CLI, AI-assisted planning
- Day 5 is a capstone: synthesis exercise, not new content

---

### Task 3: Write Week 2 lessons (Days 6-10)

**Files:**
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/06-sprint-design-for-ai-paired-dev.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/07-managing-ai-agents-as-workers.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/08-the-prompt-driven-backlog.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/09-quality-at-speed.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/10-capstone-build-your-sprint-board.md`

Same template as Task 2. Week 2 theme: Execution at AI Speed.

Content focuses on:
- Designing sprints for AI-paired development (shorter cycles, bigger scope)
- Task decomposition for parallel AI agents
- Reviewing AI output like a tech lead
- Writing backlog items as executable prompts
- Testing strategies when AI writes code
- Day 10 capstone: create a real sprint plan for the reader's idea

---

### Task 4: Write Week 3 lessons (Days 11-15)

**Files:**
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/11-the-art-of-getting-buy-in.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/12-mvp-maximum-ai-leverage.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/13-risk-management-with-ai.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/14-launch-checklist-engineering.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/15-capstone-your-launch-plan.md`

Same template. Week 3 theme: Shipping & Stakeholder Play.

Content focuses on:
- Pitching AI-built prototypes, demo-driven development
- MVP definition using AI-native framework (what to build vs what to prompt)
- AI-assisted risk identification, failure modes of AI-built systems
- Launch checklists, rollback plans, monitoring
- Day 15 capstone: build a launch-ready checklist

---

### Task 5: Write Week 4 lessons (Days 16-20)

**Files:**
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/16-feedback-loops-at-ai-speed.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/17-from-solo-to-team.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/18-building-in-public.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/19-your-personal-shipping-playbook.md`
- Create: `~/.config/claude-scheduler/courses/pm-ai-era/lessons/20-course-retrospective.md`

Same template. Week 4 theme: Iteration & Growth.

Content focuses on:
- Feedback pipelines, metrics, AI-assisted user feedback analysis
- When to bring humans in, delegation frameworks, hybrid AI+human teams
- Shipping cadence, changelogs, building community with AI help
- Day 19: synthesize all lessons into a personal reusable framework
- Day 20: retrospective exercise, identify gaps, plan next learning

---

### Task 6: Create the scheduler task file

**Files:**
- Create: `~/.config/claude-scheduler/tasks/pm-ai-era-daily.task`

**Step 1: Write the .task file**

```
# name: PM AI Era Daily Lesson
# schedule: daily 07:30
# workdir: ~/workspace/study/pm
# model: claude-sonnet-4-6
# tools: Read,Write,Bash
# max_turns: 10
# timeout: 120
# retry: 1
# notify: all
# on_failure: notify
# enabled: true
---
You are a study coach delivering a daily lesson from the "Project Management in the AI Era" course.

STEP 1: Read progress file
Read ~/.config/claude-scheduler/courses/pm-ai-era/progress.json to find the current_day, project_name, project_description, and recent feedback.

If current_day > 20, output "Course complete! All 20 lessons delivered." and stop.

If started_at is null, this is the first run. Set started_at to today's date.

STEP 2: Read today's lesson
Read the lesson file from ~/.config/claude-scheduler/courses/pm-ai-era/lessons/ matching the current day number (e.g., day 1 = file starting with "01-").

STEP 3: Read yesterday's lesson for recall questions
If current_day > 1, read the previous day's lesson file. Extract the questions from the RECALL_QUESTIONS comment block.

STEP 4: Generate enriched lesson
Create a markdown file combining:

a) HEADER: "# Day {N}: {Title}" with date and week info

b) YESTERDAY'S RECALL (skip for Day 1): Write 2-3 recall questions from the previous lesson's RECALL_QUESTIONS block. Format as numbered questions with answers hidden in a <details> tag.

c) TODAY'S LESSON: Include the full lesson content (Key Insight, Deep Dive, AI in Action, Quick Win sections).

d) YOUR PROJECT: Generate a personalized 5-minute reflection/exercise tied to the reader's project (from progress.json project_name/project_description). If no project is set yet, ask them to set one by editing progress.json. Adjust depth based on the most recent feedback rating (1-2 = simpler, 4-5 = more advanced, 3 = default).

e) TOMORROW'S TEASER: Extract from the NEXT_TEASER comment in today's lesson.

f) FOOTER: Progress bar showing "Day N/20 | Week W" and a reminder: "Rate this lesson: cs feedback pm-ai-era --rating N"

STEP 5: Write output file
Write the enriched lesson to ~/workspace/study/pm/day-{NN}-{slug}.md where NN is zero-padded day number and slug is the lesson filename slug.

STEP 6: Update progress
Read progress.json again, add current_day to the completed array, increment current_day by 1, and write the updated file back.

STEP 7: Output summary
Print a one-line summary: "Lesson {N}/20 delivered: {Title} -> ~/workspace/study/pm/day-{NN}-{slug}.md"
```

**Step 2: Verify task parses**

```bash
cs run ~/.config/claude-scheduler/tasks/pm-ai-era-daily.task --dry-run
```

Expected: Shows task details without errors.

---

### Task 7: Add `cs feedback` CLI command

**Files:**
- Modify: `src/claude_scheduler/cli.py`

**Step 1: Add cmd_feedback function**

Add after the `cmd_artifacts` function (around line 316):

```python
def cmd_feedback(args):
    """Record feedback for a course lesson."""
    import json
    course_dir = Path.home() / ".config" / "claude-scheduler" / "courses" / args.course
    progress_file = course_dir / "progress.json"
    if not progress_file.exists():
        console.print(f"[red]Course '{args.course}' not found[/red]")
        return
    data = json.loads(progress_file.read_text())
    entry = {
        "day": data["current_day"] - 1,
        "rating": args.rating,
        "note": args.note or "",
    }
    data.setdefault("feedback", []).append(entry)
    progress_file.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Feedback recorded[/green] for day {entry['day']}: rating {args.rating}/5")
```

**Step 2: Add parser entry**

Add in the `main()` function before `argcomplete.autocomplete(parser)`:

```python
    p = sub.add_parser("feedback", help="Rate a course lesson")
    p.add_argument("course", help="Course name (e.g. pm-ai-era)")
    p.add_argument("--rating", "-r", type=int, required=True, choices=[1, 2, 3, 4, 5])
    p.add_argument("--note", "-n", help="Optional feedback note")
    p.set_defaults(func=cmd_feedback)
```

**Step 3: Verify CLI**

```bash
pip install -e .
cs feedback --help
```

Expected: Shows feedback command help.

**Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: All 39 tests pass (no existing tests affected).

**Step 5: Commit**

```bash
git add src/claude_scheduler/cli.py
git commit -m "feat: add cs feedback command for course lesson ratings"
```

---

### Task 8: Verify end-to-end flow

**Step 1: Verify progress.json exists**

```bash
cat ~/.config/claude-scheduler/courses/pm-ai-era/progress.json
```

Expected: Shows `{"current_day": 1, ...}`

**Step 2: Verify lesson files exist**

```bash
ls ~/.config/claude-scheduler/courses/pm-ai-era/lessons/ | wc -l
```

Expected: 20

**Step 3: Verify task parses**

```bash
cs run ~/.config/claude-scheduler/tasks/pm-ai-era-daily.task --dry-run
```

Expected: Task details printed, no errors.

**Step 4: Verify output directory exists**

```bash
ls ~/workspace/study/pm/
```

Expected: Empty directory (no lessons delivered yet).

**Step 5: Test feedback command**

```bash
cs feedback pm-ai-era --rating 3 --note "test"
cat ~/.config/claude-scheduler/courses/pm-ai-era/progress.json
```

Expected: Feedback entry added to progress.json.

**Step 6: Final commit if needed**

```bash
git status
# Commit any remaining changes
```
