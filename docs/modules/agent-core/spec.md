last updated: 2026-09-20

# agent-core — Spec

## What
- Single-brain reasoning agent, built from scratch in Python (no CrewAI/LangChain/etc).
- Understands user question, plans investigation, selects tools, interprets results, creates hypotheses, explains findings.
- Does NOT do raw data processing itself — that's tools' job.

## LLM
- BYOK, provider-abstracted: Gemini / Claude / Groq adapters via a common `LLMProvider` interface.
- No local LLM.

## Boundaries
- Talks to tools only via Tool Gateway (not directly).
- Maintains Investigation State + Conversation Context (see investigation-engine for state shape).
