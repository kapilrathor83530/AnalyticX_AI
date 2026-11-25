from app.visualization.chart_registry import get_chart, list_charts


def test_chart_registry_has_expected_charts():
    charts = list_charts()
    ids = {c.id for c in charts}
    assert "bar" in ids
    assert "line" in ids
    assert "pie" in ids
    assert "scatter" in ids
    assert "kpi" in ids


def test_get_chart_returns_definition():
    chart = get_chart("bar")
    assert chart is not None
    assert chart.category == "comparison"
    assert any(role.name == "x" for role in chart.data_roles)
    assert any(role.name == "y" for role in chart.data_roles)


def test_unknown_chart_returns_none():
    assert get_chart("does_not_exist") is None
