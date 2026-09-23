"""Tests for artifacts_visualization.gateway_adapter -- generate_chart wired
into a real ToolGateway."""
import os
import pytest

from artifacts_visualization.gateway_adapter import make_artifacts_visualization_contracts
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


@pytest.fixture
def gateway():
    gw = ToolGateway(granted_permissions={Permission.ARTIFACT_WRITE})
    for contract in make_artifacts_visualization_contracts():
        gw.register(contract)
    return gw


@pytest.fixture
def columns():
    return [
        {"name": "product", "type": "string", "examples": ["A", "B", "C"]},
        {"name": "revenue", "type": "number", "examples": [100, 200, 20]},
    ]


def test_generate_bar_chart_via_gateway(gateway, columns):
    result = gateway.invoke("generate_chart", {
        "chart_type": "bar", "columns": columns, "title": "Revenue by Product",
    })
    assert result.success
    assert result.data.status == "SUCCESS"
    assert result.data.chart_type == "bar"
    assert os.path.exists(result.data.html_path)
    os.remove(result.data.html_path)


def test_generate_line_chart_via_gateway(gateway, columns):
    result = gateway.invoke("generate_chart", {
        "chart_type": "line", "columns": columns,
    })
    assert result.success
    assert result.data.chart_type == "line"
    os.remove(result.data.html_path)


def test_generate_pie_chart_via_gateway(gateway, columns):
    result = gateway.invoke("generate_chart", {
        "chart_type": "pie", "columns": columns,
    })
    assert result.success
    assert result.data.chart_type == "pie"
    os.remove(result.data.html_path)


def test_generate_chart_invalid_type_fails(gateway, columns):
    result = gateway.invoke("generate_chart", {
        "chart_type": "scatter", "columns": columns,
    })
    assert not result.success
    assert result.error.type == "INVALID_INPUT"


def test_generate_chart_denied_without_permission(columns):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_artifacts_visualization_contracts():
        gw.register(contract)
    result = gw.invoke("generate_chart", {"chart_type": "bar", "columns": columns})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"


@pytest.fixture
def rows():
    return [
        {"product": "A", "revenue": 100},
        {"product": "B", "revenue": 200},
        {"product": "C", "revenue": 20},
    ]


def test_export_dataset_csv_via_gateway(gateway, rows):
    result = gateway.invoke("export_dataset", {"format": "csv", "data": rows})
    assert result.success
    assert result.data.format == "csv"
    assert os.path.exists(result.data.file_path)
    os.remove(result.data.file_path)


def test_export_dataset_excel_via_gateway(gateway, rows):
    result = gateway.invoke("export_dataset", {"format": "excel", "data": rows})
    assert result.success
    assert os.path.exists(result.data.file_path)
    os.remove(result.data.file_path)


def test_export_dataset_pdf_via_gateway(gateway, rows):
    result = gateway.invoke("export_dataset", {"format": "pdf", "data": rows, "title": "Revenue"})
    assert result.success
    assert os.path.exists(result.data.file_path)
    os.remove(result.data.file_path)


def test_export_dataset_invalid_format_fails(gateway, rows):
    result = gateway.invoke("export_dataset", {"format": "json", "data": rows})
    assert not result.success
    assert result.error.type == "INVALID_INPUT"


def test_generate_report_via_gateway(gateway):
    result = gateway.invoke("generate_report", {
        "title": "Q3 Revenue Analysis",
        "sections": [
            {"heading": "Summary", "body": "Revenue grew 12% quarter over quarter."},
            {"heading": "Drivers", "body": "Product B was the largest contributor."},
        ],
    })
    assert result.success
    assert os.path.exists(result.data.file_path)
    os.remove(result.data.file_path)


def test_export_dataset_denied_without_permission(rows):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_artifacts_visualization_contracts():
        gw.register(contract)
    result = gw.invoke("export_dataset", {"format": "csv", "data": rows})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
