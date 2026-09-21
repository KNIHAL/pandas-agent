"""Wraps CatalogRepository's read methods as tool_gateway ToolContracts.

Only the 4 agent-facing tools from spec.md are exposed here
(list_sources/inspect_source/inspect_schema/find_data). upsert_entry and
resolve_authority are write/internal operations used by the connectors and
investigation-engine modules directly, not agent tools — same reasoning as
execution_backend/gateway_adapter.py's split between module API and
gateway-exposed surface.
"""

from __future__ import annotations

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from .contracts import (
    FindDataInput,
    FindDataOutput,
    InspectSchemaInput,
    InspectSchemaOutput,
    InspectSourceInput,
    InspectSourceOutput,
    ListSourcesInput,
    ListSourcesOutput,
)
from .errors import EntryNotFoundError
from .repository import CatalogRepository


def make_data_catalog_contracts(repo: CatalogRepository, timeout_seconds: float = 10.0) -> list[ToolContract]:
    """Build all 4 data-catalog ToolContracts for a given repository."""

    def list_sources(_: ListSourcesInput) -> ListSourcesOutput:
        return ListSourcesOutput(sources=repo.list_sources())

    def inspect_source(inp: InspectSourceInput) -> InspectSourceOutput:
        try:
            entries = repo.inspect_source(inp.source)
        except EntryNotFoundError:
            entries = []
        return InspectSourceOutput(source=inp.source, entries=entries)

    def inspect_schema(inp: InspectSchemaInput) -> InspectSchemaOutput:
        try:
            entries = repo.inspect_schema(inp.source, inp.entity)
        except EntryNotFoundError:
            entries = []
        return InspectSchemaOutput(entries=entries)

    def find_data(inp: FindDataInput) -> FindDataOutput:
        return FindDataOutput(matches=repo.find_data(inp.query))

    return [
        ToolContract(
            name="list_sources",
            purpose="List all data source names registered in the catalog.",
            input_schema=ListSourcesInput,
            output_schema=ListSourcesOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=list_sources,
        ),
        ToolContract(
            name="inspect_source",
            purpose="List every entity/table catalogued under a given source.",
            input_schema=InspectSourceInput,
            output_schema=InspectSourceOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=inspect_source,
        ),
        ToolContract(
            name="inspect_schema",
            purpose="Get full schema detail (fields/metrics/dimensions/relationships/lineage) for a source+entity.",
            input_schema=InspectSchemaInput,
            output_schema=InspectSchemaOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=inspect_schema,
        ),
        ToolContract(
            name="find_data",
            purpose="Search the catalog for sources/entities/fields/metrics matching a free-text query.",
            input_schema=FindDataInput,
            output_schema=FindDataOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=find_data,
        ),
    ]
