# Claude Code Skills

Reusable [Claude Code](https://claude.ai/code) skills. Clone this repo and pass it as `--add-dir` to make all skills available:

```bash
claude --add-dir /path/to/claude-skills
```

## Skills

- **[/scout](.claude/skills/scout/SKILL.md)** — Multi-model research for ambiguous problems. Distills the problem interactively, launches parallel ideation agents (Claude + GPT + Gemini), synthesizes and critiques with all three models, then optionally tests shortlisted approaches. Produces a ranked recommendation report.
