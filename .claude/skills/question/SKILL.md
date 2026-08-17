---
name: question
description: "Answer a question without taking any write actions. Use when the user invokes /question or asks a question and explicitly wants only an answer — no implementation, no code changes, no commits. Read-only actions (reading files, searching code, web research, querying APIs/logs/databases) are fine. The key constraint: gather information and explain, but never modify anything."
---

# Question Mode (Read-Only)

The user is asking a question and wants only an answer. They do NOT want you to fix, implement, refactor, or change anything.

## Allowed actions

- Reading files, searching code (Grep, Glob, Read)
- Web searches and fetches
- Git log, git blame, git diff (read-only git commands)
- Querying APIs, logs, databases for information
- Spawning research subagents (Explore agents, etc.)
- Any Bash command that only reads state (e.g., `npm ls`, `wrangler d1 execute ... --command "SELECT ..."`)

## Forbidden actions

- Edit, Write (no modifying files)
- Creating commits, branches, or PRs
- Running builds, deployments, or migrations that change state
- Any Bash command that mutates the filesystem or external state
- Creating tasks/plans for implementation work

## How to respond

Answer the question directly and thoroughly. If your research reveals an issue, explain what you found — but stop there. Do not offer to fix it, do not start fixing it, do not create a plan to fix it. If the user wants action taken, they'll ask in a follow-up message.
