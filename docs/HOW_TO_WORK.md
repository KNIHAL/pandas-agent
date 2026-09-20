last updated: 2026-09-20

# How to Work on This Project (read this first, every new chat)

## Read order
1. This file.
2. `STATUS.md` — find current active module.
3. `docs/modules/<active-module>/spec.md`
4. `docs/modules/<active-module>/tasks.md`
5. `docs/modules/<active-module>/progress.md`
- Only read `OVERVIEW.md` or `raw.txt` if deeper product context is needed.
- Do NOT read other modules' folders unless the active module depends on them.

## Format rules
- Every doc file: bullet points only, no prose paragraphs.
- Every file starts with `last updated: <date>`.
- Keep `progress.md` rolling — latest state + last 2-3 milestones only, not full history.
- Module folder names = exact code folder/repo naming (kebab-case, matches actual dir).

## When a work session ends
- Update `tasks.md` (tick done items).
- Update `progress.md` (short, only what next session needs).
- Update `STATUS.md` (1-liner for the module + "Current active module" line).
- If any real decision/tradeoff was made → add entry to `DECISIONS.md` (what + 1-line why).

## Git workflow
- One branch per module: `feature/<module-name>`.
- Never `git add .` — stage only the specific files actually changed for that task.
- Keep unrelated changes out of the commit/diff.

## Module list
agent-core, tool-gateway, execution-backend, data-catalog, connectors,
investigation-engine, artifacts-visualization, desktop-app
