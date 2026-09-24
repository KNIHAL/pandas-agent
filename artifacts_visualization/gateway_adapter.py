"""Wraps artifacts_visualization's generation/export logic as tool_gateway
ToolContracts.

generate_chart/export_dataset/generate_report produce "working" files.
finalize_artifact/list_artifacts/regenerate_artifact are the persistence
layer on top (spec.md's Finalized Dataset/Artifact stage): finalize_artifact
records a working output's generator_config so regenerate_artifact can
rebuild the file later from the same analysis result, with no re-analysis.
"""
from __future__ import annotations

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from artifacts_visualization.contracts import (
    ExportDatasetInput,
    ExportDatasetOutput,
    FinalizeArtifactInput,
    FinalizeArtifactOutput,
    GenerateChartInput,
    GenerateChartOutput,
    GenerateReportInput,
    GenerateReportOutput,
    ListArtifactsInput,
    ListArtifactsOutput,
    RegenerateArtifactInput,
    RegenerateArtifactOutput,
    ReportSection,
)
from artifacts_visualization.bar import BarChartGenerator
from artifacts_visualization.line import LineChartGenerator
from artifacts_visualization.pie import PieChartGenerator
from artifacts_visualization.exporters import (
    export_csv,
    export_excel,
    export_pdf_table,
    export_report,
)
from artifacts_visualization.repository import ArtifactRepository

_GENERATORS = {
    "bar": BarChartGenerator,
    "line": LineChartGenerator,
    "pie": PieChartGenerator,
}

_EXPORTERS = {
    "csv": lambda data, title, prefix: export_csv(data, prefix),
    "excel": lambda data, title, prefix: export_excel(data, prefix),
    "pdf": lambda data, title, prefix: export_pdf_table(data, title, prefix),
}


def make_artifacts_visualization_contracts(
    repo: ArtifactRepository, timeout_seconds: float = 15.0
) -> list[ToolContract]:
    """Build all artifacts-visualization ToolContracts for a given repository."""

    def generate_chart(inp: GenerateChartInput) -> GenerateChartOutput:
        generator_cls = _GENERATORS[inp.chart_type]
        generator = generator_cls()
        data = {"columns": [col.model_dump() for col in inp.columns]}
        result = generator.generate(data, title=inp.title)
        return GenerateChartOutput(
            status=result["status"], html_path=result["html_path"], chart_type=result["type"]
        )

    def export_dataset(inp: ExportDatasetInput) -> ExportDatasetOutput:
        exporter = _EXPORTERS[inp.format]
        path = exporter(inp.data, inp.title, inp.filename_prefix)
        return ExportDatasetOutput(status="SUCCESS", format=inp.format, file_path=path)

    def generate_report(inp: GenerateReportInput) -> GenerateReportOutput:
        sections = [s.model_dump() for s in inp.sections]
        path = export_report(inp.title, sections, inp.filename_prefix)
        return GenerateReportOutput(status="SUCCESS", file_path=path)

    def finalize_artifact(inp: FinalizeArtifactInput) -> FinalizeArtifactOutput:
        record = repo.finalize(
            artifact_type=inp.artifact_type,
            title=inp.title,
            file_path=inp.file_path,
            generator_config=inp.generator_config,
        )
        return FinalizeArtifactOutput(
            id=record["id"],
            artifact_type=record["artifact_type"],
            title=record["title"],
            file_path=record["file_path"],
            created_at=record["created_at"],
        )

    def list_artifacts(inp: ListArtifactsInput) -> ListArtifactsOutput:
        return ListArtifactsOutput(artifacts=repo.list(inp.artifact_type))

    def regenerate_artifact(inp: RegenerateArtifactInput) -> RegenerateArtifactOutput:
        record = repo.get(inp.artifact_id)
        artifact_type = record["artifact_type"]
        config = record["generator_config"]

        if artifact_type == "chart":
            chart_inp = GenerateChartInput(**config)
            path = generate_chart(chart_inp).html_path
        elif artifact_type in ("csv", "excel", "pdf"):
            export_inp = ExportDatasetInput(**config)
            path = export_dataset(export_inp).file_path
        else:  # report
            report_inp = GenerateReportInput(
                title=config["title"],
                sections=[ReportSection(**s) for s in config["sections"]],
                filename_prefix=config.get("filename_prefix", "report"),
            )
            path = generate_report(report_inp).file_path

        return RegenerateArtifactOutput(status="SUCCESS", artifact_type=artifact_type, file_path=path)

    return [
        ToolContract(
            name="generate_chart",
            purpose="Generate an interactive Chart.js HTML chart (bar/line/pie) from column data.",
            input_schema=GenerateChartInput,
            output_schema=GenerateChartOutput,
            permission=Permission.ARTIFACT_WRITE,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=generate_chart,
        ),
        ToolContract(
            name="export_dataset",
            purpose="Export tabular data (rows) to CSV, Excel, or a PDF table.",
            input_schema=ExportDatasetInput,
            output_schema=ExportDatasetOutput,
            permission=Permission.ARTIFACT_WRITE,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=export_dataset,
        ),
        ToolContract(
            name="generate_report",
            purpose="Generate a PDF analysis report from a title and ordered heading/body sections.",
            input_schema=GenerateReportInput,
            output_schema=GenerateReportOutput,
            permission=Permission.ARTIFACT_WRITE,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=generate_report,
        ),
        ToolContract(
            name="finalize_artifact",
            purpose="Persist a working chart/export/report as a finalized artifact, storing how to "
            "reproduce it later.",
            input_schema=FinalizeArtifactInput,
            output_schema=FinalizeArtifactOutput,
            permission=Permission.ARTIFACT_WRITE,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=finalize_artifact,
        ),
        ToolContract(
            name="list_artifacts",
            purpose="List finalized artifacts, optionally filtered by type.",
            input_schema=ListArtifactsInput,
            output_schema=ListArtifactsOutput,
            permission=Permission.READ_DATA,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=list_artifacts,
        ),
        ToolContract(
            name="regenerate_artifact",
            purpose="Rebuild a finalized artifact's file from its stored generator_config -- no "
            "re-analysis needed.",
            input_schema=RegenerateArtifactInput,
            output_schema=RegenerateArtifactOutput,
            permission=Permission.ARTIFACT_WRITE,
            timeout_seconds=timeout_seconds,
            failure_behavior=FailureBehavior.RETURN_ERROR,
            handler=regenerate_artifact,
        ),
    ]
