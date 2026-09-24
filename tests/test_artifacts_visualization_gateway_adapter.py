"""Tests for artifacts_visualization.gateway_adapter -- all tools wired into
a real ToolGateway."""
import os
import pytest

from artifacts_visualization.db import make_engine, make_session_factory
from artifacts_visualization.gateway_adapter import make_artifacts_visualization_contracts
from artifacts_visualization.repository import ArtifactRepository
from tool_gateway.contracts import Permission
from tool_gateway.gateway import ToolGateway


@pytest.fixture
def repo():
    engine = make_engine(":memory:")
    return ArtifactRepository(make_session_factory(engine))


@pytest.fixture
def gateway(repo):
    gw = ToolGateway(granted_permissions={Permission.ARTIFACT_WRITE, Permission.READ_DATA})
    for contract in make_artifacts_visualization_contracts(repo):
        gw.register(contract)
    return gw


@pytest.fixture
def columns():
    return [
        {"name": "product", "type": "string", "examples": ["A", "B", "C"]},
        {"name": "revenue", "type": "number", "examples": [100, 200, 20]},
    ]


@pytest.fixture
def rows():
    return [
        {"product": "A", "revenue": 100},
        {"product": "B", "revenue": 200},
        {"product": "C", "revenue": 20},
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


def test_generate_chart_denied_without_permission(columns, repo):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_artifacts_visualization_contracts(repo):
        gw.register(contract)
    result = gw.invoke("generate_chart", {"chart_type": "bar", "columns": columns})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"


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


def test_export_dataset_denied_without_permission(rows, repo):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_artifacts_visualization_contracts(repo):
        gw.register(contract)
    result = gw.invoke("export_dataset", {"format": "csv", "data": rows})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"


def test_finalize_and_list_artifacts_via_gateway(gateway, rows):
    export_result = gateway.invoke("export_dataset", {"format": "csv", "data": rows, "title": "Revenue"})
    finalize_result = gateway.invoke("finalize_artifact", {
        "artifact_type": "csv",
        "title": "Q3 Revenue Export",
        "file_path": export_result.data.file_path,
        "generator_config": {"format": "csv", "data": rows, "title": "Revenue"},
    })
    assert finalize_result.success
    assert finalize_result.data.id > 0

    list_result = gateway.invoke("list_artifacts", {})
    assert list_result.success
    assert len(list_result.data.artifacts) == 1
    assert list_result.data.artifacts[0]["title"] == "Q3 Revenue Export"

    filtered = gateway.invoke("list_artifacts", {"artifact_type": "chart"})
    assert filtered.data.artifacts == []

    os.remove(export_result.data.file_path)


def test_regenerate_chart_artifact_via_gateway(gateway, columns):
    chart_result = gateway.invoke("generate_chart", {
        "chart_type": "bar", "columns": columns, "title": "Revenue by Product",
    })
    finalize_result = gateway.invoke("finalize_artifact", {
        "artifact_type": "chart",
        "title": "Revenue by Product",
        "file_path": chart_result.data.html_path,
        "generator_config": {"chart_type": "bar", "columns": columns, "title": "Revenue by Product"},
    })
    os.remove(chart_result.data.html_path)

    regen_result = gateway.invoke("regenerate_artifact", {"artifact_id": finalize_result.data.id})
    assert regen_result.success
    assert regen_result.data.artifact_type == "chart"
    assert os.path.exists(regen_result.data.file_path)
    # regenerated file is a new file, distinct from the original
    assert regen_result.data.file_path != chart_result.data.html_path
    os.remove(regen_result.data.file_path)


def test_regenerate_unknown_artifact_fails(gateway):
    result = gateway.invoke("regenerate_artifact", {"artifact_id": 9999})
    assert not result.success


def test_list_artifacts_denied_without_permission(repo):
    gw = ToolGateway(granted_permissions=set())
    for contract in make_artifacts_visualization_contracts(repo):
        gw.register(contract)
    result = gw.invoke("list_artifacts", {})
    assert not result.success
    assert result.error.type == "PERMISSION_DENIED"
