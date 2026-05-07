# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Skills for Context Engineering — an open collection of 14 Agent Skills teaching context engineering principles for production AI agent systems. Skills are platform-agnostic (Claude Code, Cursor, GitHub Copilot, any Open Plugins-conformant tool).

Context engineering is the discipline of curating everything that enters a model's context window (system prompts, tool definitions, retrieved documents, message history, tool outputs) to maximize signal within limited attention budget.

Cited in academic research (Peking University, 2026) as foundational work on static skill architecture for agentic systems.

## Repository Structure

```
/
├── skills/                    # 14 skill directories
│   └── <skill-name>/
│       ├── SKILL.md           # Required: instructions + YAML frontmatter
│       ├── references/        # Optional: additional documentation
│       └── scripts/           # Optional: executable concept demos
├── examples/                  # 5 complete demonstration projects
│   ├── digital-brain-skill/   # Node.js personal operating system
│   ├── llm-as-judge-skills/   # TypeScript, AI SDK, 19 vitest tests
│   ├── interleaved-thinking/  # Python, reasoning trace optimizer
│   ├── book-sft-pipeline/     # LoRA fine-tuning pipeline docs
│   └── x-to-book-system/      # Multi-agent X-to-book PRD
├── docs/                      # Research materials and reference docs
├── researcher/                # Research output examples
├── template/SKILL.md          # Canonical skill template
├── SKILL.md                   # Root collection-level metadata and skill map
├── .claude-plugin/marketplace.json  # Claude Code marketplace manifest (v2.1.0)
└── .plugin/plugin.json        # Open Plugins format manifest (v2.1.0)
```

## The 14 Skills

| Skill directory | Category |
|---|---|
| `context-fundamentals` | Foundational |
| `context-degradation` | Foundational |
| `context-compression` | Foundational |
| `context-optimization` | Operational |
| `latent-briefing` | Operational |
| `evaluation` | Operational |
| `advanced-evaluation` | Operational |
| `multi-agent-patterns` | Architectural |
| `memory-systems` | Architectural |
| `tool-design` | Architectural |
| `filesystem-context` | Architectural |
| `hosted-agents` | Architectural |
| `project-development` | Development Methodology |
| `bdi-mental-states` | Cognitive Architecture |

## Build & Test Commands

No top-level build system. Individual example projects have their own tooling:

### examples/llm-as-judge-skills (TypeScript, Node >= 18)
```bash
cd examples/llm-as-judge-skills
npm install
npm run build        # tsc
npm test             # vitest run (19 tests)
npm run lint         # eslint src tests examples
npm run format       # prettier --write
npm run typecheck    # tsc --noEmit

# Run individual examples
npm run example:basic     # basic-evaluation.ts
npm run example:compare   # pairwise-comparison.ts
npm run example:rubric    # generate-rubric.ts
npm run example:full      # full-evaluation-workflow.ts
```

Dependencies: `ai` (Vercel AI SDK v4), `@ai-sdk/openai`, `@ai-sdk/anthropic`, `zod`, `dotenv`. Copy `env.example` to `.env` before running examples.

### examples/interleaved-thinking (Python >= 3.10)
```bash
cd examples/interleaved-thinking
pip install -e ".[dev]"
pytest               # pytest + pytest-asyncio (asyncio_mode = auto)
ruff check .         # linting (100 char line length)
rto                  # CLI entry point (reasoning_trace_optimizer.cli:main)
```

Dependencies: `anthropic>=0.40.0`, `pydantic>=2.0.0`, `rich>=13.0.0`, `python-dotenv>=1.0.0`.

### examples/digital-brain-skill (Node.js >= 16)
```bash
cd examples/digital-brain-skill
npm run setup           # node scripts/setup.js
npm run weekly-review   # python3 agents/scripts/weekly_review.py
npm run content-ideas   # python3 agents/scripts/content_ideas.py
npm run stale-contacts  # python3 agents/scripts/stale_contacts.py
```

### examples/book-sft-pipeline and examples/x-to-book-system
Documentation/PRD-only projects — no build system.

## Skill Authoring Rules

When creating or editing skills:

1. **SKILL.md must stay under 500 lines** — move detailed content to `references/` directory
2. **YAML frontmatter is required** — must include `name` and `description` fields as first block
3. **Folder naming**: lowercase with hyphens (e.g., `context-fundamentals`)
4. **Write in third person** — descriptions are injected into system prompts; inconsistent POV causes discovery issues
5. **Platform-agnostic** — no vendor-locked examples or platform-specific tool names without abstraction
6. **Token-conscious** — challenge each paragraph: "Does Claude really need this?" Assume advanced audience
7. **Include a Gotchas section** — experience-derived failure modes are the highest-signal content in any skill
8. **Update root README.md** when adding new skills
9. **Update both manifests** when adding skills: `.claude-plugin/marketplace.json` and `.plugin/plugin.json`

### YAML Frontmatter Format

Every `SKILL.md` must open with:
```yaml
---
name: skill-name
description: Third-person description that triggers skill activation when users ask about relevant topics.
---
```

The `description` field drives automatic skill activation — write it with activation keywords explicitly mentioned (e.g., "Use when the user asks to 'compress context'…").

### Skill Trigger Patterns (for description field)

Match existing skills' description style: list quoted phrases users might say plus related technical terms. See existing skill frontmatter for reference.

## Plugin Architecture

All 14 skills are distributed as a single plugin (`context-engineering`) in the marketplace manifest. This avoids cache duplication — Claude Code caches each plugin's `source` directory separately, so multiple plugins pointing to `source: "./"` would each cache a full copy of the repo.

Progressive disclosure pattern: only skill names/descriptions load at startup; full content loads on activation.

- **Marketplace plugin name**: `context-engineering`
- **Marketplace name**: `context-engineering-marketplace`
- **Version**: `2.1.0` (both manifests must stay in sync)
- **Owner**: Muratcan Koylan

### Installing via Claude Code
```
/plugin marketplace add muratcankoylan/Agent-Skills-for-Context-Engineering
/plugin install context-engineering@context-engineering-marketplace
```

### Installing Individual Skills Without the Plugin
```bash
mkdir -p .claude/skills
curl -o .claude/skills/context-fundamentals.md \
  https://raw.githubusercontent.com/muratcankoylan/Agent-Skills-for-Context-Engineering/main/skills/context-fundamentals/SKILL.md
```

### Open Plugins / Cursor
The `.plugin/plugin.json` follows the [Open Plugins](https://open-plugins.com) v2.0.0 standard, compatible with Cursor, GitHub Copilot, and any conformant agent tool.

## Contributing Workflow

1. Fork → create feature branch → make changes following template structure
2. Ensure `SKILL.md` files remain under 500 lines
3. Add `references/` or `scripts/` as appropriate
4. Update `README.md` skill tables
5. Update both manifests if adding a new skill directory
6. Submit pull request with clear description of changes

When adding a new skill to `marketplace.json`, add an entry to the `skills` array under the single `context-engineering` plugin — do not create a second plugin object.

## Key Design Principles

- **Context quality over quantity** — attention scarcity and lost-in-middle phenomenon mean more context is not always better
- **Sub-agents isolate context** — they exist to manage attention budget, not simulate org roles
- **Skills reference each other** — use plain text skill names (not links) in Integration sections to avoid cross-directory reference issues
- **Examples use Python pseudocode** — conceptual demonstrations that work across environments, not production-ready implementations
- **Position-aware content placement** — critical constraints belong at the beginning and end of context (85-95% recall), not the middle (76-82%)
- **Progressive disclosure** — load names/descriptions at startup; load full skill body only on activation

## Docs Directory

`docs/` contains reference and research materials used when authoring skills — not user-facing documentation:

| File | Contents |
|---|---|
| `agentskills.md` | Agent Skills format specification |
| `compression.md` | Context compression research |
| `skills-improvement-analysis.md` | Skill quality analysis |
| `claude_research.md`, `gemini_research.md` | Model-specific research |
| `blogs.md`, `hncapsule.md`, `netflix_context.md`, `vercel_tool.md` | Reference articles |
