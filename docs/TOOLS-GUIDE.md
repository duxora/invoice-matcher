# Automation Hub — Tools Guide

All tools are accessed via the `cs` CLI command. Install: `pip install -e .`

---

## 1. Workflow Orchestrator

Define workflows in natural language markdown. Claude parses and executes step-by-step.

### Create a workflow

```markdown
# My Workflow Name

## Trigger
schedule: daily 09:00

## Steps
1. Check git status and pull latest
2. Run tests on changed files
3. Summarize results

## On Failure
retry_once

## Security
level: medium
allowed_tools: Read, Grep, Glob, Bash(git, pytest)
```

Save as `~/.config/claude-scheduler/tasks/my-workflow.workflow`

### Commands

```bash
cs workflow run my-workflow.workflow              # Execute workflow
cs workflow run my-workflow.workflow --dry-run    # Preview without executing
cs workflow list                                  # List all workflows
cs workflow from-sop my-sop.md                   # Convert SOP to workflow
```

---

## 2. Security Gateway

Enforce least-privilege tool access for AI agents with audit logging.

### Setup policy

Create `~/.config/claude-scheduler/policies/default.toml`:

```toml
[policy.low]
allowed_tools = ["Read", "Grep", "Glob"]
denied_patterns = ["*.env", "*secret*"]
max_calls_per_minute = 60

[policy.medium]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit"]
bash_allowlist = ["git", "ruff", "pytest"]
require_approval = ["Edit"]
max_calls_per_minute = 30
```

### Commands

```bash
cs gateway policy          # View all policies
cs gateway audit           # View audit log (all tasks)
cs gateway audit -t my-task  # Filter by task
```

---

## 3. Socratic Debate Bot

Practice critical thinking with AI-powered Socratic questioning.

### Modes

| Mode | What it does |
|------|-------------|
| `socratic` | Asks probing "why?" questions to expose assumptions |
| `devil` | Always argues the opposite position |
| `steelman` | Strengthens your argument, then finds weaknesses |

### Commands

```bash
cs debate                                              # Start (default: socratic)
cs debate --mode devil                                 # Devil's advocate mode
cs debate --mode steelman --topic "AI replaces devs"   # With initial topic
```

### During debate

- Type your argument and press Enter
- Type `score` to get your argument scored (1-5 on logic, evidence, clarity)
- Type `quit` to end

---

## 4. Daily Journal

Combine English writing practice with critical thinking training.

### Daily routine

```bash
cs journal                    # Get today's prompt, write in $EDITOR
cs journal stats              # View progress (grammar, vocab, reasoning scores)
cs journal streak             # Check your writing streak
```

### How it works

1. You get a daily prompt (e.g., "Should AI development be regulated?")
2. Your editor opens — write 200-500 words
3. Claude reviews: grammar, vocabulary, reasoning quality
4. You get scores (1-5) and specific improvement suggestions
5. Progress is tracked over time

---

## 5. English Speaking Coach

Practice English speaking with scenario-based conversations.

### Scenarios

| Scenario | Practice for |
|----------|-------------|
| `standup` | Daily standup meetings |
| `code_review` | Explaining code changes |
| `presentation` | Technical presentations |
| `interview` | Job interviews |
| `free` | Open conversation |

### Commands

```bash
cs speak                           # Start free conversation
cs speak --scenario standup        # Practice standup
cs speak --scenario interview      # Practice interview
cs speak progress                  # View improvement over time
```

### During session

- Type your response (voice input coming soon)
- Get real-time feedback on grammar, vocabulary, fluency
- Type `quit` to end and see session summary

---

## 6. Knowledge Base (Obsidian Bridge)

Connect your Obsidian vault to Claude for AI-powered search and synthesis.

### Setup

1. Have an Obsidian vault (or any folder of markdown files)
2. Index it: `cs kb reindex --vault ~/Documents/Obsidian`

### Commands

```bash
cs kb reindex --vault ~/path/to/vault   # Index/re-index your vault
cs kb search "python patterns"          # Full-text search
cs kb ask "What patterns should I use for API design?"  # AI-synthesized answer
```

### How it works

- Uses SQLite FTS5 for fast full-text search
- Incremental indexing (only re-indexes changed files)
- Claude synthesizes answers from multiple relevant notes

---

## 7. Voice Input (Coming Soon)

Voice-to-text for dev workflows. Requires `pip install SpeechRecognition pyaudio`.

```bash
cs voice start                    # Start recording
cs voice refine --format code     # Clean transcript for code
cs voice refine --format slack    # Clean for Slack message
```

---

## 8. SOP-to-Workflow Converter

Convert plain-English SOPs into executable workflows.

### Usage

```bash
cs workflow from-sop my-procedures.md
```

Write your SOP in plain English:

```markdown
# Morning Server Check

Every morning at 8am:
1. SSH into production server
2. Check disk usage and alert if > 80%
3. Review error logs from last 24 hours
4. Restart any failed services
5. Send summary to Slack #ops channel
```

Claude converts this into a `.workflow` file with proper security levels.

---

## Quick Start

```bash
# 1. Install
pip install -e .
cs init

# 2. Try the debate bot (no setup needed)
cs debate --topic "Is TDD worth the effort?"

# 3. Start journaling
cs journal

# 4. Practice speaking
cs speak --scenario standup

# 5. Create your first workflow
cs workflow run examples/workflows/daily-code-check.workflow --dry-run

# 6. Set up knowledge base
cs kb reindex --vault ~/Documents/Obsidian
cs kb search "your topic"
```

## Data Storage

All data is stored locally at `~/.config/claude-scheduler/`:

```
~/.config/claude-scheduler/
├── config.toml           # Main config
├── tasks/                # .task and .workflow files
├── policies/             # Security policies
├── logs/                 # Execution logs
└── data/
    ├── scheduler.db      # Task execution history
    ├── journal.db        # Journal entries and scores
    ├── speaking.db       # Speaking practice progress
    ├── kb_index.db       # Knowledge base index
    └── audit.jsonl       # Security audit log
```
