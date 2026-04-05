# Product Hunt-Inspired Personal Development & AI Tools — Design

**Date:** 2026-03-07
**Status:** Approved
**Branch:** ducdt/producthunt-ideas

## Summary

8 tools inspired by Product Hunt 2026 trends, built as modules/apps within the existing automation-hub. Focused on three areas: AI workflow improvement, AI agent security, and personal development (English speaking + critical thinking).

## Architecture

All ideas integrate into the existing `automation-hub` structure:

```
automation-hub/
├── src/claude_scheduler/
│   ├── core/                    # Existing orchestrator, executor, etc.
│   ├── timetable/               # Existing family timetable
│   ├── workflow/                 # Idea 1: Claude-native workflow orchestrator
│   │                             # Idea 4: SOP converter (submodule)
│   ├── gateway/                  # Idea 2: MCP zero-trust gateway
│   └── journal/                  # Idea 8: Daily reflection journal
├── apps/
│   ├── scheduler/               # Existing
│   ├── speaking-coach/          # Idea 6: AI English speaking coach
│   ├── socratic-bot/            # Idea 7: Socratic debate bot
│   └── knowledge-base/          # Idea 3: Obsidian AI bridge
└── docs/plans/
```

Ideas 4 (SOP-to-Automation) and 5 (Voice-to-Text) are features integrated into Ideas 1 and 6 respectively, not standalone apps.

---

## Idea 1: Claude-Native Workflow Orchestrator

**Replaces:** n8n (self-hosted, paid for advanced features)
**Inspired by:** n8n, Aident AI, Zapier

### Concept

Workflows defined in natural language markdown `.workflow` files. Claude parses intent, breaks into steps, executes via MCP tools and shell commands. Reuses existing `Orchestrator` + `Task` model.

### Workflow file format

```markdown
# Daily Code Quality Check

## Trigger
schedule: daily 9am

## Steps
1. Pull latest changes from main branch
2. Run linting on all Python files
3. Check for any TODO/FIXME comments added in last 24h
4. Summarize findings and send to Slack

## On Failure
Retry once, then notify via webhook

## Security
level: medium
allowed_tools: Read, Grep, Glob, Bash(git, ruff)
```

### Components

| File | Purpose |
|------|---------|
| `src/claude_scheduler/workflow/__init__.py` | Package init |
| `src/claude_scheduler/workflow/models.py` | `Workflow`, `Step` dataclasses |
| `src/claude_scheduler/workflow/parser.py` | Parse `.workflow` markdown into step list |
| `src/claude_scheduler/workflow/runner.py` | Execute step pipeline with context passing |
| `src/claude_scheduler/workflow/sop_converter.py` | Idea 4: SOP markdown to `.workflow` file |

### How it works

1. `WorkflowParser` reads `.workflow` file, extracts trigger, steps, failure policy, security
2. Each step compiles to a `Task` object with appropriate tool constraints
3. `WorkflowRunner` wraps `Orchestrator.run_single()` in a pipeline
4. Each step's output feeds into next step's context (`context_sharing: artifact`)
5. Leverages existing `depends_on`, `security_level`, `retry`, `budget_usd`

### CLI

```bash
cs workflow run <file>           # Run a workflow
cs workflow list                 # List all workflows
cs workflow history              # Execution history
cs workflow from-sop <sop.md>    # Idea 4: Convert SOP to workflow
```

### SOP Converter (Idea 4)

- Takes plain-English SOP markdown, calls Claude to extract steps/constraints/triggers
- Outputs `.workflow` file for review
- Generated workflows default to `security_level: high` + `require_approval: true`

---

## Idea 2: MCP Zero-Trust Gateway

**Inspired by:** Agentfield, mcp-use, IBM AI Agent Security

### Concept

Middleware between Claude agents and MCP tools. Enforces least-privilege, audit logging, rate limiting. Extends existing `security_level` field into a full policy engine.

### Policy format (`policies/default.toml`)

```toml
[policy.low]
allowed_tools = ["Read", "Grep", "Glob"]
denied_patterns = ["*.env", "*secret*", "*credentials*"]
max_calls_per_minute = 60

[policy.medium]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit"]
bash_allowlist = ["git", "ruff", "pytest", "python"]
denied_patterns = ["*.env", "*secret*"]
require_approval = ["Edit"]
max_calls_per_minute = 30

[policy.high]
allowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
bash_allowlist = ["git", "ruff", "pytest", "python", "pip"]
require_approval = ["Bash", "Edit", "Write"]
network_isolation = true
max_calls_per_minute = 10
audit_level = "verbose"
```

### Components

| File | Purpose |
|------|---------|
| `src/claude_scheduler/gateway/__init__.py` | Package init |
| `src/claude_scheduler/gateway/policy.py` | Load & evaluate policies from TOML |
| `src/claude_scheduler/gateway/middleware.py` | Intercept tool calls, check policy, log |
| `src/claude_scheduler/gateway/audit.py` | Structured audit log |
| `src/claude_scheduler/gateway/sanitizer.py` | Scrub secrets from args and outputs |

### Audit log format

```json
{"ts": "...", "task": "daily-review", "tool": "Bash", "args": "git diff", "policy": "medium", "decision": "allow"}
{"ts": "...", "task": "daily-review", "tool": "Read", "args": ".env", "policy": "medium", "decision": "deny", "reason": "denied_pattern"}
```

### CLI

```bash
cs gateway audit [--task X] [--since 24h]
cs gateway policy list
```

---

## Idea 3: Obsidian AI Second Brain Bridge

**Inspired by:** Obsidian AI, Saner.AI, Tana

### Concept

CLI tool connecting Obsidian vault to Claude for AI search, synthesis, and linking. Local-first, no cloud dependency.

### Components

| File | Purpose |
|------|---------|
| `apps/knowledge-base/indexer.py` | Scan vault, build local embedding index (SQLite + numpy) |
| `apps/knowledge-base/search.py` | Semantic search via embeddings |
| `apps/knowledge-base/linker.py` | Suggest Zettelkasten links between related notes |
| `apps/knowledge-base/synthesizer.py` | Claude synthesizes answers from multiple notes |

### Config

Add to `config.toml`:
```toml
[knowledge_base]
obsidian_vault_path = "~/Documents/Obsidian"
index_db = "~/.config/claude-scheduler/data/kb_index.db"
```

### CLI

```bash
cs kb search "MCP security"
cs kb link                          # Suggest new links
cs kb ask "summarize Go patterns"   # Synthesize from notes
cs kb reindex                       # Rebuild index
```

---

## Idea 5: Voice-to-Text Dev Workflow

**Inspired by:** Wispr Flow

### Concept

Lightweight voice input using macOS speech recognition + Claude for cleanup. Shared infrastructure with Speaking Coach (Idea 6).

### Components

| File | Purpose |
|------|---------|
| `apps/voice-input/recorder.py` | macOS STT via `speech_recognition` library |
| `apps/voice-input/refiner.py` | Claude cleans transcript, formats as code/docs/slack |
| `apps/voice-input/hotkey.py` | Global hotkey via `pynput` to start/stop |

### CLI

```bash
cs voice start
cs voice stop
cs voice refine --format code|slack|doc
```

Uses `speech_recognition` + `pyaudio` — no paid API. Optional Whisper API for higher accuracy.

---

## Idea 6: AI English Speaking Coach

**Inspired by:** Fluently AI, YAP, ChatPal

### Concept

Conversation loop: STT -> Claude evaluates -> TTS speaks back. Feedback on pronunciation, grammar, vocabulary.

### Session flow

```
1. User picks scenario (or free talk)
2. AI speaks prompt via TTS (macOS `say` or edge-tts)
3. User responds via mic (speech_recognition STT)
4. Claude evaluates: grammar, vocabulary, corrections, natural response
5. AI responds + shows feedback panel
6. Repeat until "end session"
7. Session summary: scores, mistakes, new vocabulary
```

### Components

| File | Purpose |
|------|---------|
| `apps/speaking-coach/session.py` | Main conversation loop |
| `apps/speaking-coach/evaluator.py` | Claude prompt for scoring grammar/vocabulary/fluency |
| `apps/speaking-coach/scenarios.py` | Work scenarios: standup, code review, presentation, interview |
| `apps/speaking-coach/progress.py` | SQLite tracker for vocabulary growth, error frequency |

### CLI

```bash
cs speak [--scenario standup]
cs speak history
cs speak progress
```

---

## Idea 7: Socratic Debate Bot

**Inspired by:** SocraticAI, BigRead, Maike

### Concept

Multi-turn Claude agent using Socratic questioning to challenge reasoning.

### Debate modes

| Mode | Behavior |
|------|----------|
| `socratic` | Asks probing "why?" questions to expose assumptions |
| `devil` | Always argues the opposite position |
| `steelman` | Strengthens your argument, then finds remaining weaknesses |

### Components

| File | Purpose |
|------|---------|
| `apps/socratic-bot/debate.py` | Main debate loop with Socratic system prompt |
| `apps/socratic-bot/modes.py` | Mode definitions and system prompts |
| `apps/socratic-bot/scorer.py` | Evaluates argument quality: logic, evidence, counterarguments |
| `apps/socratic-bot/topics.py` | Topic bank for daily practice |

### CLI

```bash
cs debate [--mode socratic] [--topic "microservices vs monolith"]
cs debate history
cs debate score                     # View reasoning scores over time
```

---

## Idea 8: Daily Reflection & Argumentation Journal

**Inspired by:** BigRead, Grammarly, Socratic method research

### Concept

Daily journaling bot combining English writing practice with critical thinking training. Connects to Obsidian vault (Idea 3).

### Daily flow

```
1. cs journal — presents today's prompt (or user picks topic)
2. User writes 200-500 words in $EDITOR
3. Claude reviews: English (grammar, vocabulary, structure) + reasoning (logic, fallacies, evidence)
4. 2-3 Socratic follow-up questions
5. User responds briefly
6. Session summary saved to Obsidian vault (ties into Idea 3)
```

### Components

| File | Purpose |
|------|---------|
| `src/claude_scheduler/journal/daily.py` | Daily prompt generator + writing session |
| `src/claude_scheduler/journal/reviewer.py` | Claude reviews English + critical thinking |
| `src/claude_scheduler/journal/socratic_followup.py` | Socratic follow-up questions |
| `src/claude_scheduler/journal/tracker.py` | SQLite progress: vocab growth, scores, streaks |

### CLI

```bash
cs journal                          # Start today's session
cs journal review <date>            # Review past entry
cs journal stats                    # Progress dashboard
cs journal streak                   # Current streak
```

---

## Implementation Priority

| Phase | Ideas | Rationale |
|-------|-------|-----------|
| Phase 1 | 1 (Workflow) + 2 (Gateway) | Core infrastructure, all other ideas benefit |
| Phase 2 | 7 (Socratic) + 8 (Journal) | Quick wins, text-only, no audio dependencies |
| Phase 3 | 6 (Speaking Coach) + 5 (Voice) | Share audio infrastructure |
| Phase 4 | 3 (Knowledge Base) | Requires embedding setup |
| Phase 5 | 4 (SOP Converter) | Enhancement to Phase 1 |

## Dependencies

### New Python packages
- `speech_recognition` + `pyaudio` — STT for ideas 5, 6
- `edge-tts` — TTS for idea 6 (better quality than macOS `say`)
- `pynput` — global hotkey for idea 5
- `numpy` — embedding similarity for idea 3
- No new heavy dependencies (no vector DB, no paid APIs required)

### Existing packages (already in project)
- `rich` — CLI output
- `sqlite3` — progress tracking
- `tomllib` — policy/config files

## What's Cut (YAGNI)
- No web UI for any new app (CLI-first, web later if needed)
- No paid speech APIs (start with free macOS + edge-tts)
- No vector database (SQLite + numpy is sufficient for personal vault)
- No multi-user support
- No mobile app
