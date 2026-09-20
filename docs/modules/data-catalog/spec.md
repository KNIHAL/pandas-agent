last updated: 2026-09-20

# data-catalog — Spec

## What
- Semantic map of where company data lives, so agent doesn't search every source per question.
- Example shape: Revenue → Shopify/orders, Stripe/payments, Postgres/sales_summary (marked authoritative).

## Fields per entry
- source, entity, table, fields, metrics, dimensions, date fields, authority, freshness, relationships, permissions, lineage.

## Boundaries
- Populated/queried via connectors module. Consumed by agent-core + investigation-engine to pick authoritative source before querying.
