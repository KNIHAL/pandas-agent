last updated: 2026-09-21

# How to Work on This Project (read this first, every new chat)

## Read order -- STRICT, no exceptions
1. HOW_TO_WORK.md
2. STATUS.md -- find current active module.
3. docs/modules/<active-module>/spec.md
4. docs/modules/<active-module>/tasks.md
5. docs/modules/<active-module>/progress.md

That's it for docs. Do NOT read: OVERVIEW.md, raw.txt, DECISIONS.md, or any
other module's spec/tasks/progress -- even if it feels "helpful" or related.
If something is genuinely unclear after these 5, ASK the user. Don't self-justify
reading more files "just in case."

## Code files -- also STRICT
- Only read/edit code inside the active module's own code directory.
- Do NOT open another module's code files (e.g. agent-core, execution-backend)
  "for context" while working on a different module.
- If the active module's code genuinely needs to call into another module
  (a real integration point, not a guess) -- ask the user first, don't go
  explore other modules' code on your own to figure it out.
- A module's own progress.md/spec.md should already say what interface/contract
  another module exposes, if that's needed. If it doesn't say it, ask -- don't read the other module's code to find out.

## Format rules
- Every doc file: bullet points only, no prose paragraphs.
- Every file starts with "last updated: <date>".
- Keep progress.md rolling -- latest state + last 2-3 milestones only, not full history.
- Module folder names = exact code folder/repo naming (kebab-case, matches actual dir).

## When a work session ends
- Update tasks.md (tick done items).
- Update progress.md (short, only what next session needs).
- Update STATUS.md (1-liner for the module + "Current active module" line).
- If any real decision/tradeoff was made -> add entry to DECISIONS.md (what + 1-line why).

## Git workflow
- One branch per module: feature/<module-name>.
- Never `git add .` -- stage only the specific files actually changed for that task.
- Keep unrelated changes out of the commit/diff.

## Module list
agent-core, tool-gateway, execution-backend, data-catalog, connectors,
investigation-engine, artifacts-visualization, desktop-app, landing-page
