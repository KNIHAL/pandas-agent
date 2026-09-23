"""Wraps artifacts_visualization's chart generation as a tool_gateway ToolContract.

Same split/style as investigation_engine's adapter: the chart-generator
classes (bar/line/pie) are internal implementation, only the single
`generate_chart` tool is agent-facing.
"""
from __future__ import annotations

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from artifacts_visualization.contracts import (
    ExportDatasetInput,
    ExportDatasetOutput,
    GenerateChartInput,
    GenerateChartOutput,
    GenerateReportInput,
    GenerateReportOutput,
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


def make_artifacts_visualization_contracts(timeout_seconds: float = 15.0) -> list[ToolContract]:
    """Build the artifacts-visualization ToolContract(s)."""

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
    ]
