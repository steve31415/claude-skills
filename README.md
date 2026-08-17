# Claude Code Skills

Reusable [Claude Code](https://claude.ai/code) skills. Clone this repo and pass it as `--add-dir` to make all skills available:

```bash
claude --add-dir /path/to/claude-skills
```

## Skills

- **[/audio-transcription](.claude/skills/audio-transcription/SKILL.md)** — Turn an audio recording into a speaker-labeled, timestamped transcript and a structured written summary using Gemini 2.5 Pro and the bundled transcription script.
- **[/question](.claude/skills/question/SKILL.md)** — Answer a question in read-only mode. No file edits, no commits, no implementation — just research and explain.
- **[/scout](.claude/skills/scout/SKILL.md)** — Multi-model research for ambiguous problems. Distills the problem interactively, launches parallel ideation agents (Claude + GPT + Gemini), synthesizes and critiques with all three models, then optionally tests shortlisted approaches. Produces a ranked recommendation report.
