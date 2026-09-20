last updated: 2026-09-20

# desktop-app — Spec

## What
- The actual OSS product is the Desktop App itself, not CLI-first.
- Stack: Tauri + Next.js + TypeScript UI, Python Panda Runtime bundled (Agent/Tools/Connectors/Analysis/Investigation/Execution).
- UI is chat-centric: streaming responses, tables, charts, findings, evidence, source info, investigation status, artifacts.
- UI/UX details not locked yet — decide during build.

## Packaging targets
- Windows → .exe, macOS → .dmg, Linux → AppImage/.deb

## Boundaries
- Last module to build — depends on all backend modules being stable.
