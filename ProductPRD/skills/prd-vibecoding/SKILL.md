---
name: prd-vibecoding
description: Generate and maintain standardized PRD assets (Markdown + interactive HTML with process diagrams) from rough product input. Use when users ask to draft PRD, refine requirements, convert notes into a PRD package, or continuously update MD/HTML specs with missing-item follow-up questions until required fields are complete.
---

# PRD VibeCoding Skill

## Core Contract

- Produce two synchronized deliverables for every request:
  - `PRD_*.md`: structured requirement spec for archive and handoff.
  - `prd-*.html`: interactive review page focused on flow diagrams (Mermaid).
- Keep requirement IDs consistent across documents (e.g., `REQ-001`).
- Ask follow-up questions when required fields are missing; continue until all required fields are filled.

## Required Fields Checklist

Collect all items below before marking the PRD as complete:

1. Product basics: product name, project code, owner, target date.
2. Necessity: business reason, user value, timing.
3. Scope: in-scope and out-of-scope.
4. Users and scenarios: target users, core journey.
5. Functional requirements: at least one `REQ-*` with acceptance criteria.
6. Non-functional requirements: performance, availability, security.
7. AI boundaries: can do, cannot do, fallback.
8. Milestones and release plan.

If any item is missing, ask targeted short questions and update files incrementally.

## Workflow

### 1. Normalize Input

- Convert rough notes into structured sections.
- Split merged statements into atomic requirements.
- Assign or reuse stable `REQ-*` IDs.

### 2. Generate Markdown PRD

- Follow section order in `references/md-standard.md`.
- Ensure each `REQ-*` includes: objective, rules, exceptions, acceptance, tracking.
- Add unresolved assumptions to a final "Open Questions" section.

### 3. Generate Interactive HTML

- Follow `references/html-standard.md`.
- Build a diagram-first review page (flow, sequence, architecture, state machine, release/deployment).
- Show per-diagram purpose, I/O, acceptance points, risks.

### 4. Quality Gate

Before finishing:

1. Verify all required fields are filled or explicitly marked as open questions.
2. Verify Markdown and HTML describe the same requirement set.
3. Verify every diagram maps to at least one `REQ-*` or milestone.
4. Verify JSON/config/code snippets use valid paths and consistent filenames.

## File and Naming Rules

- Default Markdown filename: `PRD_<topic>.md`.
- Default HTML filename: `prd-<topic>.html`.
- Keep Chinese content concise and implementation-oriented.
- Keep diagrams readable on desktop and mobile.

## Resources

- Markdown structure reference: `references/md-standard.md`
- HTML structure reference: `references/html-standard.md`
- Markdown template asset: `assets/PRD_TEMPLATE.md`
- HTML template asset: `assets/PRD_FLOWBOARD_TEMPLATE.html`
