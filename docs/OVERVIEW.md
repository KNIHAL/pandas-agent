last updated: 2026-09-20

# Panda Agent — Overview

## What
Open-source **Desktop AI Data Analyst**. Not a CSV cleaner — it connects to real
data sources, investigates questions like a human analyst, and gives
evidence-based answers with artifacts (charts/reports/datasets).

## Core philosophy
- One brain, many hands — single agent reasons, tools execute.
- LLM never sees raw datasets directly (no huge context dumps).
- Deterministic computation (pandas/numpy/duckdb) outside the LLM.
- Adaptive bounded investigation loop, not rigid waterfall.
- BYOK — user provides own LLM key (Gemini/Claude/Groq). No local LLM.

## Major building blocks
- Agent Core — scratch-built Python agent loop (no CrewAI / no agentic lib)
- Tool Gateway — mediates all tool access (permissions, limits, audit)
- Execution Backend — sandboxed pandas/numpy/duckdb execution
- Data Catalog — semantic map of where company data lives
- Connectors — Postgres/MySQL/Shopify/Slack/Stripe/etc.
- Investigation Engine — hypothesis → test → evidence → finding
- Artifacts & Visualization — charts/CSV/Excel/PDF/reports
- Desktop App — Tauri + Next.js UI, Python runtime bundled

## Explicitly NOT building (V1)
Multi-agent system, autonomous operator, CRM, local LLM, local vector DB,
CLI-first product, unrestricted Python exec, hosted SaaS (yet).

## Full spec
See `raw.txt` in this folder for the complete detailed spec (long — only
read if you need deep detail beyond a module's own spec.md).
