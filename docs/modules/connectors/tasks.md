last updated: 2026-09-22

# connectors — Tasks

- [x] Define base Connector interface
- [x] CSV/file connector (V1 first target)
- [x] Postgres connector (V1 second target)
- [x] Data access tools: query_data, fetch_dataset, materialize_dataset, release_dataset
- [x] Data quality tools: profile_dataset, check_missing, check_duplicates, check_invalid_values, check_format_consistency, check_date_coverage, check_schema, assess_data_quality
- [x] Register all tools with tool-gateway
- [x] Extended connector library (Kumar's full list, easy→hard): Excel, MySQL, Notion, Slack, Google Drive, Stripe, BigQuery, GA4, Mixpanel, WooCommerce, Salesforce, HubSpot, QuickBooks, Teams, Shopify, Snowflake (17 total incl. CSV/Postgres). Qdrant skipped — doesn't fit the row-fetch Connector interface, no clear use yet.
