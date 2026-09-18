# ARTEL Agent Instructions

## Documentation language

- Write and maintain all project documentation in English.
- Keep code identifiers, design tokens, API names, and technical terminology in their canonical English form.
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
