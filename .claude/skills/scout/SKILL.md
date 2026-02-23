---
name: scout
description: Multi-model research skill for finding and evaluating approaches to ambiguous problems — integrations, workarounds, unconventional solutions. Launches parallel ideation agents, synthesizes with Claude/GPT/Gemini critique, then tests shortlisted approaches. Use when the user says "/scout" or wants to research integration approaches.
version: 0.1.0
---

# /scout

Research and evaluate approaches to ambiguous problems — integrating with systems not designed for it, finding workarounds with tradeoffs, choosing between approaches that require careful consideration of specific circumstances.

This skill finds approaches, evaluates them with multiple AI models, and optionally tests shortlisted options. It does NOT implement the final solution — it produces a recommendation.

Do NOT enter plan mode. Execute all phases in a single session.

**Plan mode check:** If a system reminder indicates that plan mode is active, STOP. Do not execute any phases. Instead, tell the user: "This skill needs to run interactively, but plan mode is active. Please exit plan mode first (`/plan` to toggle), then re-invoke the skill." Then stop.

---

## Scratch Directory

All intermediate files live in `/tmp/claude/scout/`. At the start of every run:

```
rm -rf /tmp/claude/scout && mkdir -p /tmp/claude/scout/ideas /tmp/claude/scout/critique /tmp/claude/scout/test-results
```

**Context management rule:** The main agent MUST NEVER read individual subagent output files directly. All synthesis is performed by dedicated combiner subagents. The main agent reads ONLY combiner output files and `problem.md`. This keeps the main agent's context lean across all 11 phases.

---

## Phase 1: Problem Distillation (Interactive)

Read the user's problem description. Then ask clarifying questions using `AskUserQuestion` — ask the most important question first, and continue asking (one at a time) until the problem is well-defined. Focus on:

- **Goal:** What specific outcome are you trying to achieve? What does success look like?
- **Constraints:** Technical stack, budget, legal/compliance, timeline, platform limitations
- **Scale:** Volume, frequency, number of users/accounts
- **Prior art:** What have you already tried or ruled out? Why?
- **Tradeoff preferences:** Reliability vs cost? Ease of setup vs flexibility? Official vs unofficial approaches?
- **Must-haves vs nice-to-haves:** Which requirements are non-negotiable?
- **Reference projects:** Any specific projects or tools to investigate? (e.g., OpenClaw, a known library, a competitor's approach)

Stop asking when you have enough to write a clear problem statement. Don't over-ask — 2-4 questions is typical.

Then launch a subagent to write `/tmp/claude/scout/problem.md` with this structure:

```markdown
# Problem Statement

## Goal
[One paragraph: what we're trying to achieve]

## Constraints
- [Bulleted list of hard constraints]

## Environment
- [Technical stack, platforms, existing systems]

## Scale
- [Volume, frequency, growth expectations]

## Tradeoff Preferences
- [What the user is willing to sacrifice for what]

## Must-Haves
- [Non-negotiable requirements]

## Nice-to-Haves
- [Desired but flexible requirements]

## Prior Art
- [What's been tried, what's been ruled out, and why]

## Reference Projects to Investigate
- [Specific projects/tools the user wants checked, or "None"]
```

Read `/tmp/claude/scout/problem.md`. Present a brief summary (2-3 sentences) followed by the full file contents verbatim. The user must see exactly what the subagents will work from.

**GATE:** User confirms or corrects the problem statement. If corrections are needed, update the file and re-present (summary + full contents). Do not proceed until the user approves.

---

## Phase 2: API Key Check (Interactive)

Check the environment for `OPENAI_API_KEY` and `GEMINI_API_KEY` (use Bash: `echo ${OPENAI_API_KEY:+set}` and `echo ${GEMINI_API_KEY:+set}`).

For each missing key, ask the user via `AskUserQuestion`:

> `OPENAI_API_KEY` is not set. GPT's perspective will be unavailable without it.

Options:
- **Set it now** — user provides the key, export it in the shell
- **Skip GPT** — continue without GPT's perspective

Repeat for `GEMINI_API_KEY`.

Record which models are available. At minimum, Claude is always available.

If both external models are skipped, warn: "Running with Claude only. The skill works but benefits significantly from diverse model perspectives."

---

## Phase 3: Ideation (Parallel Subagents)

Launch all applicable agents in a **single message** (parallel Task calls). Every agent uses `subagent_type: "general-purpose"`.

Each agent receives the problem statement: instruct it to read `/tmp/claude/scout/problem.md`.

Each agent writes its output to `/tmp/claude/scout/ideas/<name>.md` using this format:

```markdown
# <Source Name> Ideas

## Idea 1: <short name>
**Description:** [A short paragraph (4-6 sentences): what this approach is, how the mechanism works, what components/services are involved, and what the user experience looks like]
**Key insight:** [Why this might work when the obvious approach doesn't]
**Source:** [URL, project name, or "built-in knowledge"]

## Idea 2: ...
```

### Agent A: Brainstorm (always)

> You are brainstorming approaches to a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> Using your built-in knowledge, generate 5-10 distinct approaches. Include:
> - Well-known approaches (even if imperfect)
> - Creative workarounds
> - Approaches from adjacent domains that might transfer
> - Both official/supported and unofficial/hack approaches
>
> For each idea, explain the core mechanism — how does it actually work?
>
> Write your output to `/tmp/claude/scout/ideas/brainstorm.md`.

### Agent B: Web Search (always)

> You are researching existing approaches to a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> Use the `WebSearch` tool extensively. Search for:
> - "[problem domain] integration approaches"
> - "[problem domain] workaround"
> - "[problem domain] API alternative"
> - "[problem domain] automation"
> - Search developer forums: Stack Overflow, Reddit, Hacker News
> - Search for blog posts and tutorials
>
> Run at least 5 different searches with varied terminology. For each approach found, record the source URL and summarize the approach.
>
> Write your output to `/tmp/claude/scout/ideas/web-search.md`.

### Agent C: OSS Projects (always)

> You are searching for open-source projects that solve or partially solve a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> Use `WebSearch` to search GitHub specifically:
> - "site:github.com [problem domain]"
> - "[problem domain] library"
> - "[problem domain] SDK"
> - "[problem domain] bot framework"
>
> For promising projects, use `WebFetch` to read their README for details. Record:
> - Project name and URL
> - Stars/activity level (if visible)
> - What it does and how
> - Last update date (is it maintained?)
> - License
>
> Write your output to `/tmp/claude/scout/ideas/oss-projects.md`.

### Agent D: Reference Projects (only if user specified projects in Phase 1)

> You are investigating specific projects to see if they solve or address a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> For each reference project listed in the problem statement:
> 1. Search for it on the web and GitHub
> 2. Read its README and documentation
> 3. Determine: does it solve our problem? Partially? What approach does it use?
> 4. Note: maturity, maintenance status, license, limitations
>
> Write your output to `/tmp/claude/scout/ideas/reference-projects.md`.

### Agent E: GPT Ideation (only if OPENAI_API_KEY available)

> You are getting GPT's perspective on a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> Call the OpenAI API to ask GPT for approaches. Use this pattern:
>
> ```bash
> PROBLEM=$(cat /tmp/claude/scout/problem.md)
> RESPONSE=$(curl -s https://api.openai.com/v1/chat/completions \
>   -H "Content-Type: application/json" \
>   -H "Authorization: Bearer $OPENAI_API_KEY" \
>   -d "$(jq -n --arg problem "$PROBLEM" '{
>     model: "gpt-4o",
>     max_tokens: 4000,
>     messages: [
>       {role: "system", content: "You are a senior engineer brainstorming approaches to a technical problem. Generate 5-10 distinct approaches, including creative workarounds and unconventional solutions. For each, explain the mechanism, key tradeoffs, and any prerequisites. Be specific and practical."},
>       {role: "user", content: $problem}
>     ]
>   }')")
> echo "$RESPONSE" | jq -r '.choices[0].message.content' > /tmp/claude/scout/ideas/gpt-raw.md
> ```
>
> If the API call fails, write an error report noting the failure and continue.
>
> Read the GPT response from `gpt-raw.md`, reformat it into the standard idea format, and write to `/tmp/claude/scout/ideas/gpt-ideas.md`.

### Agent F: Gemini Ideation (only if GEMINI_API_KEY available)

> You are getting Gemini's perspective on a problem. Read the problem statement from `/tmp/claude/scout/problem.md`.
>
> Call the Gemini API. Use this pattern:
>
> ```bash
> PROBLEM=$(cat /tmp/claude/scout/problem.md)
> RESPONSE=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" \
>   -H "Content-Type: application/json" \
>   -H "x-goog-api-key: $GEMINI_API_KEY" \
>   -X POST \
>   -d "$(jq -n --arg problem "$PROBLEM" '{
>     generationConfig: {maxOutputTokens: 8000},
>     contents: [{role: "user", parts: [{text: ("You are a senior engineer brainstorming approaches to a technical problem. Generate 5-10 distinct approaches, including creative workarounds and unconventional solutions. For each, explain the mechanism, key tradeoffs, and any prerequisites. Be specific and practical.\n\n" + $problem)}]}]
>   }')")
> echo "$RESPONSE" | jq -r '.candidates[0].content.parts[0].text' > /tmp/claude/scout/ideas/gemini-raw.md
> ```
>
> If the API call fails, write an error report noting the failure and continue.
>
> Read the Gemini response from `gemini-raw.md`, reformat it into the standard idea format, and write to `/tmp/claude/scout/ideas/gemini-ideas.md`.

---

## Phase 4: Idea Synthesis (Combiner Subagent)

Launch one `subagent_type: "general-purpose"` agent:

> You are synthesizing ideas from multiple sources. Read ALL files in `/tmp/claude/scout/ideas/`.
>
> Produce a consolidated, deduplicated list of approaches:
> 1. Merge near-identical ideas (note all sources)
> 2. Keep genuinely distinct variants as separate entries
> 3. Organize by approach category (e.g., "Official API", "Reverse-engineered", "Third-party service", "Browser automation", etc.)
> 4. Number all ideas sequentially
>
> For each idea, include:
> - **Name**: Short descriptive name
> - **Category**: Approach category
> - **Description**: A short paragraph (4-6 sentences) explaining the mechanism, components involved, and user experience. Preserve important details from the source agents — don't over-compress.
> - **Sources**: Which agents proposed this (brainstorm, web, OSS, GPT, Gemini, etc.)
> - **Key insight**: Why this might work
>
> Write to `/tmp/claude/scout/combined-ideas.md`.

Do NOT read `combined-ideas.md` yet — it will be consumed by Phase 5 subagents.

---

## Phase 5: Critique + Ranking (Parallel Subagents)

Launch up to 3 subagents in a **single message**. Each reads `/tmp/claude/scout/combined-ideas.md` and writes to `/tmp/claude/scout/critique/<model>.md`.

### Claude Critique (always)

> You are a critical evaluator of technical approaches. Read `/tmp/claude/scout/problem.md` for context and `/tmp/claude/scout/combined-ideas.md` for the list of approaches.
>
> For each approach:
> 1. **Strengths**: What's good about this approach? When would it shine?
> 2. **Weaknesses**: What could go wrong? What are the failure modes?
> 3. **Risks**: Legal, maintenance, reliability, scalability concerns
> 4. **Prerequisites**: What's needed to implement this?
> 5. **Devil's advocate**: Why might this approach fail completely?
>
> Then generate:
> - **Evaluation criteria**: A list of 5-10 criteria for comparing approaches. Include criteria that can be tested experimentally (e.g., "message delivery latency under 5 seconds", "handles 100 concurrent connections"). Mark each criterion as [testable] or [judgment].
> - **Ranking**: Order all approaches from best to worst for this specific problem. Justify your top 3 and bottom 3.
> - **Improvements**: Any refinements, combinations, or new variants suggested by the analysis.
>
> Write to `/tmp/claude/scout/critique/claude.md`.

### GPT Critique (only if OPENAI_API_KEY available)

> You are getting GPT's critical evaluation. Read `/tmp/claude/scout/problem.md` and `/tmp/claude/scout/combined-ideas.md`.
>
> Format both into a prompt and call the OpenAI API:
>
> ```bash
> PROBLEM=$(cat /tmp/claude/scout/problem.md)
> IDEAS=$(cat /tmp/claude/scout/combined-ideas.md)
> PROMPT="PROBLEM:\n$PROBLEM\n\nAPPROACHES:\n$IDEAS"
> RESPONSE=$(curl -s https://api.openai.com/v1/chat/completions \
>   -H "Content-Type: application/json" \
>   -H "Authorization: Bearer $OPENAI_API_KEY" \
>   -d "$(jq -n --arg prompt "$PROMPT" '{
>     model: "gpt-4o",
>     max_tokens: 4000,
>     messages: [
>       {role: "system", content: "You are a critical evaluator of technical approaches. For each approach: list strengths, weaknesses, risks, prerequisites, and a devil'\''s advocate argument for why it might fail. Then: (1) propose 5-10 evaluation criteria (mark each as [testable] or [judgment]), (2) rank all approaches best-to-worst with justification for top 3 and bottom 3, (3) suggest improvements or new variants."},
>       {role: "user", content: $prompt}
>     ]
>   }')")
> echo "$RESPONSE" | jq -r '.choices[0].message.content' > /tmp/claude/scout/critique/gpt.md
> ```
>
> If the API call fails, write an error report to `/tmp/claude/scout/critique/gpt.md`.

### Gemini Critique (only if GEMINI_API_KEY available)

> You are getting Gemini's critical evaluation. Read `/tmp/claude/scout/problem.md` and `/tmp/claude/scout/combined-ideas.md`.
>
> Format both into a prompt and call the Gemini API:
>
> ```bash
> PROBLEM=$(cat /tmp/claude/scout/problem.md)
> IDEAS=$(cat /tmp/claude/scout/combined-ideas.md)
> PROMPT="You are a critical evaluator of technical approaches. For each approach: list strengths, weaknesses, risks, prerequisites, and a devil's advocate argument for why it might fail. Then: (1) propose 5-10 evaluation criteria (mark each as [testable] or [judgment]), (2) rank all approaches best-to-worst with justification for top 3 and bottom 3, (3) suggest improvements or new variants.\n\nPROBLEM:\n$PROBLEM\n\nAPPROACHES:\n$IDEAS"
> RESPONSE=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" \
>   -H "Content-Type: application/json" \
>   -H "x-goog-api-key: $GEMINI_API_KEY" \
>   -X POST \
>   -d "$(jq -n --arg prompt "$PROMPT" '{
>     generationConfig: {maxOutputTokens: 8000},
>     contents: [{role: "user", parts: [{text: $prompt}]}]
>   }')")
> echo "$RESPONSE" | jq -r '.candidates[0].content.parts[0].text' > /tmp/claude/scout/critique/gemini.md
> ```
>
> If the API call fails, write an error report to `/tmp/claude/scout/critique/gemini.md`.

---

## Phase 6: Report Synthesis (Combiner Subagent)

Launch one `subagent_type: "general-purpose"` agent:

> You are producing a final research report. Read `/tmp/claude/scout/problem.md`, `/tmp/claude/scout/combined-ideas.md`, and ALL files in `/tmp/claude/scout/critique/`.
>
> Produce a report with:
>
> ### 1. Options (3-8)
> Drop clearly inferior approaches. Merge near-duplicates. For each surviving option, include ALL of the following fields — do not omit any:
> - **Name**
> - **How it works**: A substantial paragraph (5-8 sentences) explaining the mechanism, what components are involved, and how a user would interact with it. The reader should be able to understand the approach without referring to other sources.
> - **Pros** (bulleted list, 3+ items): Concrete advantages — performance, reliability, cost, ease of implementation, maintenance burden, ecosystem support, etc.
> - **Cons** (bulleted list, 3+ items): Concrete disadvantages and risks — limitations, failure modes, dependencies, maintenance concerns, etc.
> - **Combined ranking score** (average rank across models, note agreement/disagreement)
> - **Devil's advocate** (strongest argument against this option)
>
> ### 2. Evaluation Criteria
> Merge criteria from all models. Deduplicate. For each criterion:
> - Description
> - [testable] or [judgment]
> - How to test (for testable criteria)
>
> ### 3. Key Disagreements
> Where did models disagree significantly? What does each perspective reveal?
>
> ### 4. Recommendation
> Which 2-3 options are most worth testing? Brief justification.
>
> Write to `/tmp/claude/scout/report.md`.

Read `/tmp/claude/scout/report.md` and present the full report to the user.

**GATE:** User reviews the report. They may:
- Accept and proceed to shortlisting
- Ask to add/remove/modify options
- Ask to adjust evaluation criteria
- Request deeper investigation of a specific option
- Refine the problem statement (loop back to Phase 1)

If modifications are needed, update `report.md` accordingly (launch a subagent if needed for deeper investigation).

---

## Phase 7: Shortlisting (Interactive)

Based on user feedback, select 2-4 options for implementation testing.

For each shortlisted option, identify what resources are needed to test it. Be specific and creative. Examples:
- API credentials (which service? what permissions?)
- Test accounts (on which platform? what verification needed?)
- Device access (e.g., ADB access to a phone with WhatsApp, a Raspberry Pi for IoT)
- Sample data (what format? how much?)
- External services (paid? free tier available?)
- Network access (specific domains/ports for the sandbox firewall)

Also identify **serialization constraints**: which resources can only be used by one agent at a time? (e.g., a single phone can only run one automation test at a time)

Present the shortlist and resource requirements to the user.

Save to `/tmp/claude/scout/shortlist.md`:

```markdown
# Shortlisted Approaches

## Approach 1: <name>
**Summary:** [1-2 sentences]
**Resources needed:**
- [resource 1]: [details]
- [resource 2]: [details]
**Serialization constraints:** [any exclusive resources, or "None"]

## Approach 2: ...

## Evaluation Criteria
[Copy from report.md — the criteria these tests should evaluate against]

## Test Schedule
- Parallel: [approaches that can run simultaneously]
- Sequential: [approaches that share exclusive resources, in order]
```

**GATE:** User supplies resources or adjusts the shortlist. For each resource:
- User provides the resource (credential, access, etc.)
- Or user removes that approach from the shortlist

Do not proceed until user has supplied all resources for at least one approach.

---

## Phase 8: Implementation Testing (Parallel Subagents)

Launch one `subagent_type: "general-purpose"` agent per shortlisted approach. Respect serialization constraints — if approaches share exclusive resources, run them sequentially.

Each agent prompt:

> You are implementing and testing a specific approach to a problem. Read:
> - `/tmp/claude/scout/problem.md` — the problem
> - `/tmp/claude/scout/shortlist.md` — your assigned approach and evaluation criteria
>
> Your assigned approach: **[approach name]**
>
> Steps:
> 1. Implement a minimal proof-of-concept — just enough to test the evaluation criteria
> 2. For each [testable] criterion, run a concrete test and record the result (pass/fail/measurement)
> 3. For each [judgment] criterion, provide your assessment with evidence
> 4. Note any surprises: things that were easier or harder than expected, undocumented limitations, unexpected capabilities
> 5. Record the total implementation effort (rough line count, dependencies, complexity)
>
> **Resources available:** [list resources the user provided for this approach]
>
> Write your results to `/tmp/claude/scout/test-results/<approach-name>.md` using this format:
>
> ```markdown
> # Test Results: <approach name>
>
> ## Implementation Summary
> - **Effort:** [low/medium/high + brief explanation]
> - **Dependencies:** [what was needed]
> - **Code location:** [where the PoC code lives, if applicable]
>
> ## Criterion Results
>
> ### [Criterion 1 name]
> - **Type:** testable | judgment
> - **Result:** PASS | FAIL | PARTIAL | [measurement]
> - **Evidence:** [what was tested, what happened]
> - **Notes:** [surprises, caveats]
>
> ### [Criterion 2 name] ...
>
> ## Surprises
> - [Things not anticipated by the research phase]
>
> ## Overall Assessment
> [2-3 sentences: would you recommend this approach based on testing?]
> ```

As each subagent completes, read its result file and give the user a brief status update: "[Approach name]: completed — [one-sentence summary of outcome]".

---

## Phase 9: Final Report (Combiner Subagent)

Launch one `subagent_type: "general-purpose"` agent:

> You are writing the final comparative report. Read:
> - `/tmp/claude/scout/problem.md` — the original problem
> - `/tmp/claude/scout/report.md` — the pre-testing analysis (criteria, pros/cons)
> - ALL files in `/tmp/claude/scout/test-results/` — experimental results
>
> Produce a final report:
>
> ### 1. Comparative Table
> A table with approaches as rows and evaluation criteria as columns. Each cell: PASS/FAIL/PARTIAL or a measurement.
>
> ### 2. Per-Approach Summary
> For each tested approach:
> - What worked well
> - What didn't work
> - Surprises from testing
> - Updated pros/cons (incorporating test results)
>
> ### 3. Recommendation
> Recommend 1-2 approaches. For each:
> - Why this is the best choice for this specific problem
> - Remaining risks
> - Suggested next steps for full implementation
> - What would change if constraints shift (e.g., "if budget increases, approach X becomes viable")
>
> ### 4. Runner-Up
> If the recommendation doesn't work out, what's plan B and why?
>
> Write to `/tmp/claude/scout/final-report.md`.

Read `/tmp/claude/scout/final-report.md` and present it to the user.

---

## Edge Cases

- **No reference projects specified:** Skip Agent D in Phase 3
- **API call fails (GPT/Gemini):** Agent writes error report, skill continues with available models
- **Only Claude available:** Skill works but note reduced perspective diversity
- **User wants to skip testing phases:** After Phase 6 gate, user can say "skip testing" — present the report as the final deliverable
- **Subagent crashes:** Note the failure, continue with remaining agents, report the gap
- **Problem too vague after distillation:** Push back — ask more questions until the problem statement is actionable
- **No good approaches found:** Report this honestly. Suggest the problem may need reframing and offer to restart with adjusted constraints.
- **All approaches fail testing:** Report this. Recommend the least-bad option with clear caveats, or suggest the problem needs a fundamentally different framing.
