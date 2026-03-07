# Design: PM in the AI Era — Daily Study Course

**Date:** 2026-03-07
**Status:** Approved

## Overview

A 20-day course on project management for software engineers adapting to AI-era workflows. Delivered daily at 7:30 AM via claude-scheduler as hybrid content: pre-written lessons + Claude-generated personalized reflections.

**Target:** Intermediate PM (knows sprints/features, wants AI-era adaptation)
**Goals:** Ship personal projects AND drive work initiatives effectively with AI

## Course Structure

4 weekly modules x 5 days. Each day ~20 min (15 min read + 5 min apply).

### Week 1: AI-Augmented Planning
1. The New PM Mindset
2. Idea to Spec in 60 Minutes
3. Scoping with AI Estimation
4. Architecture Decisions at AI Speed
5. Capstone: Spec Your Idea

### Week 2: Execution at AI Speed
6. Sprint Design for AI-Paired Dev
7. Managing AI Agents as Workers
8. The Prompt-Driven Backlog
9. Quality at Speed
10. Capstone: Build Your Sprint Board

### Week 3: Shipping & Stakeholder Play
11. The Art of Getting Buy-In
12. MVP: Maximum AI Leverage
13. Risk Management with AI
14. Launch Checklist Engineering
15. Capstone: Your Launch Plan

### Week 4: Iteration & Growth
16. Feedback Loops at AI Speed
17. From Solo to Team
18. Building in Public
19. Your Personal Shipping Playbook
20. Course Retrospective

## Lesson Format

```
┌─────────────────────────────┐
│  Yesterday's Recall (2 min) │  ← spaced repetition quiz
├─────────────────────────────┤
│  Key Insight (2 min)        │
│  Deep Dive (8 min)          │  ← pre-written content
│  AI in Action (3 min)       │
├─────────────────────────────┤
│  Your Project (5 min)       │  ← Claude-generated, tied to user's idea
│  Tomorrow's Teaser (30 sec) │  ← curiosity hook
└─────────────────────────────┘
```

## File Layout

```
~/.config/claude-scheduler/courses/pm-ai-era/
├── lessons/           # 20 pre-written lesson files
│   ├── 01-the-new-pm-mindset.md
│   └── ...
└── progress.json      # Tracks current day, project context, feedback

~/workspace/study/pm/  # Delivered enriched lessons
├── day-01-the-new-pm-mindset.md
└── ...
```

## Scheduler Task

- File: `~/.config/claude-scheduler/tasks/pm-ai-era-daily.task`
- Schedule: `daily 07:30`
- Model: `claude-sonnet-4-6`
- Tools: `Read,Write,Bash`
- Prompt instructs Claude to:
  1. Read progress.json for current day + project context + past feedback
  2. Read the lesson file
  3. Generate recall quiz (from previous day's content)
  4. Generate personalized "Your Project" reflection
  5. Write combined output to `~/workspace/study/pm/day-XX-title.md`
  6. Update progress.json
  7. Output summary for scheduler logs

## Engagement Mechanisms

1. **Spaced repetition** — 2-3 recall questions from previous lesson
2. **Project thread** — Every reflection ties to user's real project
3. **Difficulty signal** — `cs feedback pm-ai-era --rating N` adjusts depth
4. **Capstone synthesis** — Days 5/10/15/20 are apply-and-build challenges

## Feedback CLI

```bash
cs feedback pm-ai-era --rating 3 --note "too basic"
```

Writes to progress.json, Claude reads next morning to adjust reflection depth.
