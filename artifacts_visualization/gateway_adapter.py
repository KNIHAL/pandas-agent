"""Wraps artifacts_visualization's chart generation as a tool_gateway ToolContract.

Same split/style as investigation_engine's adapter: the chart-generator
classes (bar/line/pie) are internal implementation, only the single
`generate_chart` tool is agent-facing.
"""
from __future__ import annotations

from tool_gateway.contracts import FailureBehavior, Permission, ToolContract

from artifacts_visualization.contracts import GenerateChartInput, GenerateChartOutput
from artifacts_visualization.bar import BarChartGenerator
from artifacts_visualization.line import LineChartGenerator
from artifacts_visualization.pie import PieChartGenerator

_GENERATORS = {
    "bar": BarChartGenerator,
    "line": LineChartGenerator,
    "pie": PieChartGenerator,
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
    ]
