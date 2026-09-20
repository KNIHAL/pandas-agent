last updated: 2026-09-20

# connectors — Spec

## What
- Connector-based architecture so adding a new source later isn't a core rewrite.
- Target sources (over time): Postgres, MySQL, Snowflake, BigQuery, Salesforce, HubSpot, Shopify, WooCommerce, Google Analytics, Mixpanel, Slack, Teams, Notion, Google Drive, Stripe, QuickBooks, CSV, Excel, Qdrant Cloud/pgvector.
- V1 priority: start with 1 file connector (CSV) + 1 DB connector (Postgres) to prove the pattern end-to-end.

## Data Access tools (via tool-gateway)
- query_data, fetch_dataset, materialize_dataset, release_dataset

## Data Quality tools
- profile_dataset, check_missing, check_duplicates, check_invalid_values, check_format_consistency, check_date_coverage, check_schema, assess_data_quality
- Purpose: determine trustworthiness for analysis, NOT auto-cleaning.
