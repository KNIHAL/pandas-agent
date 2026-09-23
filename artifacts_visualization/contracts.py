"""Pydantic contracts for artifacts-visualization tools.

Mirrors the ChartColumn/data shape already used by the underlying
BarChartGenerator/LineChartGenerator/PieChartGenerator.generate() (a
'columns' list of {name, type, examples}), just given a schema so the
tool-gateway can validate input/output.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChartColumn(BaseModel):
    name: str
    type: Literal["string", "number"]
    examples: list


class GenerateChartInput(BaseModel):
    chart_type: Literal["bar", "line", "pie"] = Field(
        description="Which chart generator to use."
    )
    columns: list[ChartColumn] = Field(
        description="One row of column data: a labels column (type='string') "
        "plus one or more value columns (type='number')."
    )
    title: str = Field(default="Chart", description="Chart title.")


class GenerateChartOutput(BaseModel):
    status: Literal["SUCCESS"]
    html_path: str
    chart_type: str


class ExportDatasetInput(BaseModel):
    format: Literal["csv", "excel", "pdf"] = Field(description="Export file format.")
    data: list[dict] = Field(description="Rows to export, e.g. [{'col': value, ...}, ...].")
    title: str = Field(default="Dataset", description="Used as the PDF title; ignored for csv/excel.")
    filename_prefix: str = Field(default="dataset", description="Prefix for the generated filename.")


class ExportDatasetOutput(BaseModel):
    status: Literal["SUCCESS"]
    format: str
    file_path: str


class ReportSection(BaseModel):
    heading: str
    body: str


class GenerateReportInput(BaseModel):
    title: str
    sections: list[ReportSection] = Field(description="Ordered heading/body sections of the report.")
    filename_prefix: str = Field(default="report")


class GenerateReportOutput(BaseModel):
    status: Literal["SUCCESS"]
    file_path: str
