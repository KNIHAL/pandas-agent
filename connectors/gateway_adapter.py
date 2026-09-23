"""Wraps DatasetRegistry + quality.py as tool_gateway ToolContracts.

Data-access tools (query_data/fetch_dataset/materialize_dataset/
release_dataset) operate on a DatasetRegistry. Data-quality tools take a
dataset_id and look the DataFrame up via registry.get_dataset(dataset_id) --
they never take raw data as input, keeping the "LLM never sees raw datasets
directly" rule intact end-to-end.
"""

from __future__ import annotations

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from . import quality
from .contracts import (
    AssessDataQualityOutput,
    CheckDateCoverageInput,
    CheckDateCoverageOutput,
    CheckDuplicatesInput,
    CheckDuplicatesOutput,
    CheckFormatConsistencyInput,
    CheckFormatConsistencyOutput,
    CheckInvalidValuesInput,
    CheckInvalidValuesOutput,
    CheckMissingInput,
    CheckMissingOutput,
    CheckSchemaInput,
    CheckSchemaOutput,
    DatasetIdInput,
    FetchDatasetInput,
    FetchDatasetOutput,
    MaterializeDatasetInput,
    MaterializeDatasetOutput,
    ProfileDatasetOutput,
    QueryDataInput,
    QueryDataOutput,
    ReleaseDatasetInput,
    ReleaseDatasetOutput,
)
from .registry import DatasetRegistry


def make_connector_contracts(registry: DatasetRegistry, timeout_seconds: float = 30.0) -> list[ToolContract]:
    """Build all 12 connector ToolContracts (4 data-access + 8 data-quality)
    bound to a given registry."""

    # -- data access --------------------------------------------------------

    def query_data(inp: QueryDataInput) -> QueryDataOutput:
        df = registry.query(inp.source, inp.entity, columns=inp.columns, filters=inp.filters, limit=inp.limit)
        return QueryDataOutput(rows=df.to_dict(orient="records"), row_count=len(df))

    def fetch_dataset(inp: FetchDatasetInput) -> FetchDatasetOutput:
        handle = registry.fetch_dataset(inp.source, inp.entity, columns=inp.columns, filters=inp.filters)
        return FetchDatasetOutput(**handle.summary())

    def materialize_dataset(inp: MaterializeDatasetInput) -> MaterializeDatasetOutput:
        path = registry.materialize_dataset(inp.dataset_id, inp.path, fmt=inp.format)
        return MaterializeDatasetOutput(path=path)

    def release_dataset(inp: ReleaseDatasetInput) -> ReleaseDatasetOutput:
        return ReleaseDatasetOutput(released=registry.release_dataset(inp.dataset_id))

    # -- data quality -------------------------------------------------------

    def profile_dataset(inp: DatasetIdInput) -> ProfileDatasetOutput:
        return ProfileDatasetOutput(**quality.profile_dataset(registry.get_dataset(inp.dataset_id).df))

    def check_missing(inp: CheckMissingInput) -> CheckMissingOutput:
        return CheckMissingOutput(**quality.check_missing(registry.get_dataset(inp.dataset_id).df, inp.column))

    def check_duplicates(inp: CheckDuplicatesInput) -> CheckDuplicatesOutput:
        return CheckDuplicatesOutput(
            **quality.check_duplicates(registry.get_dataset(inp.dataset_id).df, inp.subset)
        )

    def check_invalid_values(inp: CheckInvalidValuesInput) -> CheckInvalidValuesOutput:
        return CheckInvalidValuesOutput(
            **quality.check_invalid_values(
                registry.get_dataset(inp.dataset_id).df,
                inp.column,
                min_value=inp.min_value,
                max_value=inp.max_value,
                allowed_values=inp.allowed_values,
            )
        )

    def check_format_consistency(inp: CheckFormatConsistencyInput) -> CheckFormatConsistencyOutput:
        return CheckFormatConsistencyOutput(
            **quality.check_format_consistency(registry.get_dataset(inp.dataset_id).df, inp.column)
        )

    def check_date_coverage(inp: CheckDateCoverageInput) -> CheckDateCoverageOutput:
        return CheckDateCoverageOutput(
            **quality.check_date_coverage(registry.get_dataset(inp.dataset_id).df, inp.column)
        )

    def check_schema(inp: CheckSchemaInput) -> CheckSchemaOutput:
        return CheckSchemaOutput(
            **quality.check_schema(registry.get_dataset(inp.dataset_id).df, inp.expected_schema)
        )

    def assess_data_quality(inp: DatasetIdInput) -> AssessDataQualityOutput:
        return AssessDataQualityOutput(**quality.assess_data_quality(registry.get_dataset(inp.dataset_id).df))

    def contract(name, purpose, input_schema, output_schema, handler, permission=Permission.READ_DATA):
        return ToolContract(
            name=name,
            purpose=purpose,
            input_schema=input_schema,
            output_schema=output_schema,
            permission=permission,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=handler,
        )

    return [
        contract("query_data", "Run a bounded, ad-hoc query/preview against a connector source.",
                  QueryDataInput, QueryDataOutput, query_data),
        contract("fetch_dataset", "Load a full result set from a connector into memory as a dataset_id handle.",
                  FetchDatasetInput, FetchDatasetOutput, fetch_dataset),
        contract("materialize_dataset", "Persist an already-fetched dataset to disk (parquet/csv).",
                  MaterializeDatasetInput, MaterializeDatasetOutput, materialize_dataset,
                  permission=Permission.ARTIFACT_WRITE),
        contract("release_dataset", "Free the in-memory dataset held under a dataset_id.",
                  ReleaseDatasetInput, ReleaseDatasetOutput, release_dataset),
        contract("profile_dataset", "Per-column profile (dtype/nulls/uniques/examples/numeric stats) of a dataset.",
                  DatasetIdInput, ProfileDatasetOutput, profile_dataset),
        contract("check_missing", "Null count/percentage per column (or one column) of a dataset.",
                  CheckMissingInput, CheckMissingOutput, check_missing),
        contract("check_duplicates", "Duplicate row count/percentage in a dataset, optionally scoped to columns.",
                  CheckDuplicatesInput, CheckDuplicatesOutput, check_duplicates),
        contract("check_invalid_values", "Count values in a column outside a range or allowed-value set.",
                  CheckInvalidValuesInput, CheckInvalidValuesOutput, check_invalid_values),
        contract("check_format_consistency", "Detect the dominant string pattern in a column and its consistency %.",
                  CheckFormatConsistencyInput, CheckFormatConsistencyOutput, check_format_consistency),
        contract("check_date_coverage", "Date range and missing-day gaps for a date-like column.",
                  CheckDateCoverageInput, CheckDateCoverageOutput, check_date_coverage),
        contract("check_schema", "Compare a dataset's actual columns/types against an expected schema.",
                  CheckSchemaInput, CheckSchemaOutput, check_schema),
        contract("assess_data_quality", "Aggregate 0-100 trustworthiness score from missingness + duplication.",
                  DatasetIdInput, AssessDataQualityOutput, assess_data_quality),
    ]
