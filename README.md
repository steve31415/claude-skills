# Claude Code Skills

Reusable skills for [Claude Code](https://claude.ai/code).

## Usage

Clone this repo and add it as an additional directory when launching Claude Code:

```bash
git clone https://github.com/steve31415/claude-skills.git
claude --add-dir /path/to/claude-skills
```

Skills in `.claude/skills/` will be automatically discovered and available via slash commands.

## Skills

| Skill | Description |
|-------|-------------|
| [scout](.claude/skills/scout/SKILL.md) | Multi-model research for evaluating approaches to ambiguous problems. Launches parallel ideation agents, synthesizes with Claude/GPT/Gemini critique, then tests shortlisted approaches. |

## How Skills Work

Each skill is a directory under `.claude/skills/` containing a `SKILL.md` file with frontmatter (name, description, version) and instructions. Claude Code discovers these automatically and makes them available as `/skill-name` commands.

See the [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for more on skills.
