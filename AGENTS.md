# ARTEL Agent Instructions

## Documentation language

Two audiences, two languages. The directory settles which one a file is.

| Path | Read by | Language |
| --- | --- | --- |
| `AGENTS.md`, `CLAUDE.md`, `.agents/**`, `.claude/**` | an agent | English |
| `README.md`, `docs/**` | a person | Korean |

- Instructions an agent is told to read are English. Every repository's `AGENTS.md` points
  only into `.agents/docs/`, and nothing points an agent at `docs/` — that boundary already
  holds, so keep it.
- Documentation a person opens is Korean. `README.md` is the front door, and `docs/` holds
  the architecture, protocol and decision records that a teammate reads.
- Keep code identifiers, design tokens, API names, and technical terminology in their
  canonical English form in both.
- A document already written in the other language is not a defect to sweep. Rewrite it when
  you are rewriting it anyway; leave it alone otherwise. `.plan/**` keeps whatever each plan
  already uses.
- Follow [`.agents/docs/git-language.md`](.agents/docs/git-language.md) when writing commits,
  pull requests, or issues.
- Its `## Titles` section governs every title you write — commit subject, pull request title,
  Jira summary, and the headings inside a document or a deck.
- Its `## Word Choice` section reaches further than Git: it also governs code comments, KDoc and docstrings, SQL comments, test names, and issue bodies.

## UI design system

- Before designing or changing React UI, Replay Studio, QA timeline, evidence, or agent-status interfaces, read `.agents/docs/DESIGN.md` and follow it.
- Unless a task explicitly requires otherwise, use its semantic tokens, layouts, components, states, and accessibility rules as the project defaults.

## Notion workspace

- Before reading from or writing to the ARTEL Notion workspace, read [`.agents/docs/NOTION.md`](.agents/docs/NOTION.md) and follow it.
- Credentials live in the gitignored `.notion.env`. Load them with `set -a && . ./.notion.env && set +a`. Never run `ntn login`, and never print the token.
- Its `## 8. Write policy` section governs what an agent may create on its own, what needs a human's approval first, and what is never written.
