---
name: canva-technical-deck
description: Create or revise Korean technical presentation slides in Canva using an existing deck's template, editable execution diagrams, and source-backed metrics. Use for requests such as 발표자료 수정, Agent 구조도, 문제 해결 과정, or 비용 비교 슬라이드.
---

# Canva technical presentations

Start with the slide the user points to and its neighbors. Identify which existing page supplies the template, what the audience should understand, and which part the user wants changed. Treat a rejected or rolled-back design as evidence about the workflow, not as a visual reference to reproduce.

## Keep the template and design the body

- Duplicate the reference page or copy its actual header, section label, guide line, typography, and other shared elements. Keep their positions and styles. Build the body around the specific content.
- Use Canva text, shapes, and connectors for diagrams. Keep real game or product captures as images. Prefer the original editable diagram or full-resolution source when one exists. Rebuilding a diagram as many disconnected image fragments loses its editability and layout.
- Choose the layout from the relationship being explained. Use aligned lanes for different actors, a branch for routing, and a return arrow for a loop. Put labels next to their branches. Give the main path a clear reading direction and room to breathe. Reserve color for meaningful distinctions.
- For a new visual direction across many pages, show one representative page at presentation size before extending that treatment. If the user already selected an example, use it. When asked to compare layouts, duplicate the relevant page and keep both versions available.
- When working on copies, record the source and copy page IDs. Keep originals in order. For a rollback, match the requested copies by ID and verify the original sequence afterward. Page numbers move as slides are inserted.

## Write for the audience

Use short Korean bullets and concrete titles. Put the conclusion or design decision in the title when it helps. Omit tool instructions, filler, and low-level checks such as “턴 종료 버튼이 보이는지 확인” unless that check is itself the topic. Write **테스트 케이스** in audience-facing labels. Preserve exact identifiers in evidence.

For a section overview, use a contents page naming the topics in order. On the detail pages, reuse the same progress guide and highlight the current topic. If the user asks for template pages only, prepare the requested slots and leave the body open.

## Show the actual execution

Use one page per requested Agent or execution mode. Follow the implementation from input through decision, selected handler, operation, and output. Show what repeats, what ends the run, and where human approval is needed when those details matter. Look up the actual route names, conditions, and effects before drawing arrows.

For the ARTEL Agent section, introduce Project Agent, Scenario Agent, QA Agent Workflow Lite, and QA Agent Planner–Executor in the overview. On the Scenario Agent page, label each route with the request that triggers it and show what the handler returns, saves, or asks the user. On the Workflow Lite page, show where the engine schedules judgment and knowledge recording after action. On the Planner–Executor page, distinguish planning, action selection, and evaluation. These are content choices for this deck, not a mandatory outline for other presentations.

## Support results with comparable evidence

- For a problem-solving slide, connect the observed problem to a specific change and an observed result. In the ARTEL game-diversity example, cover both variation in input packages and different control patterns across genres.
- For context optimization, give duplicate-screen removal and ternary search for the compression threshold their own explanations. Distinguish these changes from the Planner–Executor model split. Attribute each result only to the experiment that measured it.
- Prefer the requested aggregate over a handpicked run. Verify the baseline, comparison group, sample sizes, models, unit, and denominator. Compute a cost reduction as (baseline cost − new cost) / baseline cost × 100. Use the same aggregation method on both sides. If comparable aggregates are unavailable, leave the percentage out and state the evidence gap.
- When the user asks for percentages only, keep the percentage and a short comparison label on the slide. Keep the underlying values, sample scope, and source in notes or the handoff. For a claim about recorded knowledge, check the original PR or run report and distinguish entries recorded from runs executed.

## Check the saved slide

View the finished slide at presentation size. Trace each branch to its destination and check for overlaps, clipped Korean labels, and illegible captions. In the saved Canva design, verify that a label, a node, and a connector can be selected independently. Check the order and count when pages changed. Share a direct link to the result and identify any simplified illustration or unverified figure.
