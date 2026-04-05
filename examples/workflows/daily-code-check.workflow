# Daily Code Quality Check

## Trigger
schedule: daily 09:00

## Steps
1. Pull latest changes from main branch
2. Run ruff linting on all Python files
3. Check for TODO/FIXME comments added in last 24h
4. Summarize findings

## On Failure
retry_once

## Security
level: medium
allowed_tools: Read, Grep, Glob, Bash(git, ruff)
