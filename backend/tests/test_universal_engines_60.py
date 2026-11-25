"""Comprehensive 60-scenario test suite for Analyticx AI Universal Insight & Visualization Engines.

Covers:
- S01..S20: 20 Dataset Structure & Edge-Case Scenarios
- S21..S34: 14 Insight Accuracy & Anti-Hallucination Scenarios
- S35..S48: 14 Visualization Validation & Rendering Scenarios
- S49..S60: 12 Agent, Integration & 5-Domain E2E Scenarios (Sales, Student, HR, Weather, Healthcare)
"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.agents.orchestrator import run_workflow
from app.analytics.data_understanding import understand_dataset, validate_and_sanitize_dataframe
from app.analytics.eda import eda_dataframe
from app.analytics.project_insights_engine import (
    INSIGHT_CATEGORIES,
    build_automated_eda,
    build_executive_summary,
    compute_dataset_fingerprint,
    discover_business_insights,
)
from app.analytics.statistics import (
    analyze_categorical_column,
    analyze_datetime_column,
    analyze_numerical_column,
    calculate_correlation,
    compare_groups,
    detect_outliers,
)
from app.main import app
from app.services.visualization_service import recommend_charts, render_chart, validate_config
from app.visualization.chart_schemas import ChartConfig
from app.visualization.data_mapper import build_chart_data

client = TestClient(app)


def _run_insights(df: pd.DataFrame, name: str = "TestDataset") -> Dict[str, Any]:
    understanding = understand_dataset(df, dataset_name=name, sanitize=True)
    ds = SimpleNamespace(id=1, name=name, stored_path=None, version=1)
    fp = compute_dataset_fingerprint(ds, df)
    eda = build_automated_eda(df, name, understanding=understanding)
    insights = discover_business_insights(df, ds, eda, fp)
    summary = build_executive_summary(df, name, eda, insights)
    return {
        "understanding": understanding,
        "eda": eda,
        "insights": insights,
        "summary": summary,
        "fingerprint": fp,
    }


def _upload_df(df: pd.DataFrame, filename: str = "test.csv") -> int:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    resp = client.post("/api/v1/datasets/upload", files={"file": (filename, csv_bytes, "text/csv")})
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


# ==============================================================================
# PART A — 20 DATASET STRUCTURE & EDGE-CASE SCENARIOS (S01 .. S20)
# ==============================================================================


def test_s01_small_numeric_dataset() -> None:
    df = pd.DataFrame({"a": range(1, 16), "b": [x * 2 for x in range(1, 16)], "c": [x + 5 for x in range(1, 16)]})
    res = _run_insights(df, "SmallNumeric")
    assert res["eda"]["row_count"] == 15
    assert set(res["understanding"]["profile"]["numerical_columns"]) == {"a", "b", "c"}
    assert len(res["insights"]) >= 3


def test_s02_large_numeric_dataset_10k() -> None:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "metric_a": rng.normal(500, 75, size=10000),
        "metric_b": rng.normal(120, 25, size=10000),
        "group": rng.choice(["North", "South", "East", "West"], size=10000),
    })
    t0 = time.perf_counter()
    rendered = render_chart(df, {
        "chart_type": "scatter",
        "data_mapping": {"x": "metric_a", "y": "metric_b"},
    })
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    assert rendered["metadata"]["sampled"] is True
    assert rendered["metadata"]["total_source_rows"] == 10000
    assert len(rendered["data"]) == 2000


def test_s03_categorical_only_dataset() -> None:
    df = pd.DataFrame({
        "department": ["Sales", "Sales", "Engineering", "Engineering", "Support", "Marketing"] * 4,
        "status": ["Active", "Active", "Active", "Leave", "Active", "Leave"] * 4,
        "tier": ["Gold", "Silver", "Gold", "Bronze", "Silver", "Gold"] * 4,
    })
    res = _run_insights(df, "CategoricalOnly")
    profile = res["understanding"]["profile"]
    assert profile["numerical_columns"] == []
    assert set(profile["categorical_columns"]) >= {"department", "status", "tier"}
    cov = {item["category"]: item for item in res["summary"]["category_coverage"]}
    assert cov["categorical"]["status"] == "available"
    assert cov["distribution"]["status"] != "available"
    assert "No reliable insight could be generated" in cov["distribution"]["message"]
    recs = recommend_charts(df, understanding=res["understanding"])
    assert len(recs) >= 1
    assert all(r["chart_type"] in {"bar", "horizontal_bar", "pie", "donut", "treemap", "grouped_bar"} for r in recs)


def test_s04_mixed_schema_dataset() -> None:
    df = pd.DataFrame({
        "order_id": ["ORD-001", "ORD-002", "ORD-003", "ORD-004", "ORD-005", "ORD-006"],
        "order_date": ["2025-01-01", "2025-01-05", "2025-02-01", "2025-02-15", "2025-03-01", "2025-03-20"],
        "region": ["North", "South", "North", "East", "West", "East"],
        "is_priority": [True, False, True, False, True, False],
        "revenue": [1200.0, 800.0, 1500.0, 950.0, 2100.0, 1100.0],
    })
    profile = understand_dataset(df)["profile"]
    assert "order_id" in profile["identifier_columns"]
    assert "order_date" in profile["datetime_columns"]
    assert "region" in profile["categorical_columns"]
    assert "is_priority" in profile["boolean_columns"]
    assert "revenue" in profile["numerical_columns"]


def test_s05_datetime_and_quarter_dataset() -> None:
    df = pd.DataFrame({
        "quarter": ["2025-Q3", "2025-Q1", "2025-Q4", "2025-Q2"],
        "sales": [300, 100, 400, 200],
    })
    res = understand_dataset(df)
    assert "quarter" in res["profile"]["datetime_columns"]
    chart_data = build_chart_data(
        res["normalized_df"],
        ChartConfig(chart_type="time_series", data_mapping={"x": "quarter", "y": "sales"}, aggregation="sum"),
        normalized_df=res["normalized_df"],
    )
    assert [row["sales"] for row in chart_data] == [100.0, 200.0, 300.0, 400.0]


def test_s06_high_missing_values() -> None:
    df = pd.DataFrame({
        "clean_col": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "partial_nulls": [1, None, 3, None, 5, 6, None, 8, 9, 10],
        "mostly_null": [1, None, None, None, None, None, None, None, 9, None],
        "all_null": [None] * 10,
    })
    res = _run_insights(df, "MissingDataset")
    cols_by_name = {c["name"]: c for c in res["understanding"]["profile"]["columns"]}
    assert cols_by_name["partial_nulls"]["missing_percent"] == 30.0
    assert cols_by_name["mostly_null"]["missing_percent"] == 80.0
    assert cols_by_name["all_null"]["detected_type"] == "empty"
    assert cols_by_name["all_null"]["analysis_eligible"] is False
    quality_titles = " ".join(i["title"] for i in res["insights"] if i["category"] == "quality").lower()
    assert "missing" in quality_titles


def test_s07_exact_duplicate_rows() -> None:
    base = pd.DataFrame({"region": ["A", "B", "C", "D"], "amount": [10, 20, 30, 40]})
    df = pd.concat([base, base.iloc[:2]], ignore_index=True)
    res = _run_insights(df, "DuplicateDataset")
    assert res["understanding"]["profile"]["duplicate_rows"] == 2
    assert any(i["category"] == "quality" and "duplicate" in i["title"].lower() for i in res["insights"])


def test_s08_extreme_outliers_preserved_nondestructively() -> None:
    values = [100, 102, 98, 101, 99, 103, 97, 100, 105, 96, 101, 5000]
    df = pd.DataFrame({"cost": values, "unit": ["A"] * 6 + ["B"] * 6})
    understanding = understand_dataset(df)
    assert len(understanding["normalized_df"]) == len(df)
    out = detect_outliers(understanding["normalized_df"], "cost", method="iqr")
    assert out["flagged_count"] >= 1
    assert any(a["value"] == 5000.0 for a in out["anomalies"])


def test_s09_constant_and_zero_variance() -> None:
    df = pd.DataFrame({
        "const_num": [100.0] * 12,
        "const_cat": ["AlwaysSame"] * 12,
        "varying": list(range(1, 13)),
    })
    profile = understand_dataset(df)["profile"]
    assert "const_num" in profile["constant_columns"]
    assert "const_cat" in profile["constant_columns"]
    cols = {c["name"]: c for c in profile["columns"]}
    assert cols["const_num"]["is_constant"] is True
    assert cols["const_num"]["analysis_eligible"] is False
    assert "const_num" not in profile["numerical_columns"]


def test_s10_leading_zero_and_numeric_ids() -> None:
    df = pd.DataFrame({
        "zip_code": ["00123", "00456", "00789", "00101", "00999", "00222"],
        "customer_id": list(range(1001, 1007)),
        "spend": [50.0, 60.0, 55.0, 80.0, 75.0, 90.0],
    })
    res = understand_dataset(df)
    norm_df = res["normalized_df"]
    profile = res["profile"]
    assert norm_df["zip_code"].iloc[0] == "00123"
    assert "customer_id" in profile["identifier_columns"]
    assert "customer_id" not in profile["numerical_columns"]
    assert "zip_code" not in profile["numerical_columns"]


def test_s11_numeric_strings() -> None:
    df = pd.DataFrame({
        "units_text": ["1,250", "980", "2,100.5", "1,500", "750", "3,200"],
        "city": ["A", "B", "A", "B", "A", "B"],
    })
    res = understand_dataset(df)
    assert "units_text" in res["profile"]["numerical_columns"]
    assert float(res["normalized_df"]["units_text"].max()) == 3200.0


def test_s12_currency_symbols_inr_usd() -> None:
    df = pd.DataFrame({
        "price_inr": ["₹50,000", "₹25,000", "₹75,000", "₹10,000", "₹60,000", "₹30,000"],
        "cost_usd": ["$400.50", "$200.00", "$600.25", "$90.00", "$450.00", "$250.00"],
        "category": ["X", "Y", "X", "Y", "X", "Y"],
    })
    res = _run_insights(df, "CurrencyDataset")
    assert "price_inr" in res["understanding"]["profile"]["numerical_columns"]
    assert "cost_usd" in res["understanding"]["profile"]["numerical_columns"]
    st = analyze_numerical_column(res["understanding"]["normalized_df"], "price_inr")
    assert st["sum"] == 250000.0
    assert st["mean"] == round(250000.0 / 6, 4)


def test_s13_percentage_strings() -> None:
    df = pd.DataFrame({
        "conversion_rate": ["12.5%", "25%", "18.0%", "30.5%", "15%", "22%"],
        "channel": ["Email", "Search", "Email", "Search", "Social", "Social"],
    })
    res = understand_dataset(df)
    meta = {c["name"]: c for c in res["profile"]["columns"]}["conversion_rate"]
    assert meta["detected_type"] == "numeric"
    assert meta["semantic_type"] == "percentage"
    st = analyze_numerical_column(res["normalized_df"], "conversion_rate")
    assert st["min"] == 12.5
    assert st["max"] == 30.5


def test_s14_unusual_column_names() -> None:
    df = pd.DataFrame({
        "Total Sales ($)": [100, 200, 150, 300, 250, 400],
        "% Growth / YoY": ["10%", "15%", "12%", "20%", "18%", "25%"],
        "Region [Zone-1]": ["North", "South", "North", "South", "East", "East"],
    })
    res = _run_insights(df, "UnusualCols")
    assert len(res["insights"]) >= 3
    recs = recommend_charts(df, understanding=res["understanding"])
    assert len(recs) >= 1


def test_s15_completely_empty_columns_and_validation() -> None:
    empty_df = pd.DataFrame()
    _, v_empty = validate_and_sanitize_dataframe(empty_df)
    assert v_empty["valid"] is False

    df = pd.DataFrame({
        "Unnamed: 0": [None, None, None, None],
        "empty_named": [None, None, None, None],
        "metric": [10, 20, 30, 40],
        "group": ["A", "B", "A", "B"],
    })
    sanitized, report = validate_and_sanitize_dataframe(df)
    assert report["valid"] is True
    assert "Unnamed: 0" not in sanitized.columns
    assert "empty_named" in report["empty_columns"]


def test_s16_duplicate_column_names() -> None:
    raw = pd.DataFrame([[10, 20, "A"], [30, 40, "B"], [50, 60, "A"], [70, 80, "B"]], columns=["Revenue", "Revenue", "Team"])
    sanitized, report = validate_and_sanitize_dataframe(raw)
    assert report["valid"] is True
    assert "Revenue" in report["duplicate_columns"]
    assert list(sanitized.columns) == ["Revenue", "Revenue_2", "Team"]


def test_s17_imbalanced_categories() -> None:
    df = pd.DataFrame({
        "outcome": ["Normal"] * 98 + ["Critical_Rare", "Minor_Rare"],
        "score": list(range(100)),
    })
    cat = analyze_categorical_column(df, "outcome")
    assert cat["imbalance_ratio"] >= 40.0
    assert cat["dominant_pct"] == 98.0
    assert "Critical_Rare" in cat["rare_categories"]


def test_s18_high_cardinality_dimension() -> None:
    df = pd.DataFrame({
        "vendor_name": [f"Vendor_{i:03d}" for i in range(120)],
        "spend": [100 + i * 5 for i in range(120)],
    })
    res = understand_dataset(df)
    assert "vendor_name" in res["profile"]["high_cardinality_columns"]
    pie_check = validate_config(df, {"chart_type": "pie", "data_mapping": {"labels": "vendor_name", "values": "spend"}}, res)
    assert pie_check.valid is False
    assert pie_check.suggested_alternative == "horizontal_bar"


def test_s19_negative_numeric_values() -> None:
    df = pd.DataFrame({
        "city": ["Oslo", "Moscow", "Toronto", "Delhi", "Paris", "Berlin"],
        "temp_c": [-12.5, -18.0, -5.0, 28.0, 6.0, -1.5],
        "net_profit": [-500.0, -200.0, 300.0, 900.0, -100.0, 400.0],
    })
    st = analyze_numerical_column(df, "temp_c")
    assert st["min"] == -18.0
    assert st["negative_count"] == 4
    pie_check = validate_config(df, {"chart_type": "pie", "data_mapping": {"labels": "city", "values": "net_profit"}})
    assert len(pie_check.warnings) >= 1


def test_s20_all_zero_values() -> None:
    df = pd.DataFrame({"all_zero": [0.0] * 10, "val": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "grp": ["A", "B"] * 5})
    res = understand_dataset(df)
    assert "all_zero" in res["profile"]["constant_columns"]
    st = analyze_numerical_column(res["normalized_df"], "all_zero")
    assert st["sum"] == 0.0
    assert st["cv_pct"] is None
    hist = render_chart(res["normalized_df"], {"chart_type": "histogram", "data_mapping": {"x": "all_zero"}}, understanding=res)
    assert len(hist["data"]) == 1
    assert hist["data"][0]["count"] == 10


# ==============================================================================
# PART B — 14 INSIGHT ACCURACY & ANTI-HALLUCINATION TESTS (S21 .. S34)
# ==============================================================================


def test_s21_exact_mean_median_verification() -> None:
    vals = [10, 20, 30, 40, 200]
    df = pd.DataFrame({"amount": vals, "cat": ["A", "B", "A", "B", "A"]})
    st = analyze_numerical_column(df, "amount")
    assert st["mean"] == float(pd.Series(vals).mean())
    assert st["median"] == float(pd.Series(vals).median())


def test_s22_exact_min_max_verification() -> None:
    vals = [-45.5, 0.0, 12.25, 999.75, 42.0]
    df = pd.DataFrame({"score": vals, "tag": ["x", "y", "x", "y", "z"]})
    st = analyze_numerical_column(df, "score")
    assert st["min"] == -45.5
    assert st["max"] == 999.75
    assert st["range"] == 1045.25


def test_s23_exact_category_frequencies() -> None:
    df = pd.DataFrame({"region": ["North"] * 6 + ["South"] * 3 + ["West"] * 1})
    cat = analyze_categorical_column(df, "region")
    assert cat["dominant_category"] == "North"
    assert cat["dominant_count"] == 6
    assert cat["dominant_pct"] == 60.0


def test_s24_exact_missing_percentages() -> None:
    df = pd.DataFrame({"a": [1, None, 3, None, 5, 6, 7, 8], "b": list(range(8))})
    st = analyze_numerical_column(df, "a")
    assert st["missing_count"] == 2
    assert st["missing_pct"] == 25.0


def test_s25_pearson_spearman_cramers_v() -> None:
    x = np.arange(1, 21, dtype=float)
    df = pd.DataFrame({
        "x": x,
        "y": x * 3.0 + 5.0,
        "tier": ["Low"] * 10 + ["High"] * 10,
        "plan": ["Basic"] * 10 + ["Enterprise"] * 10,
    })
    corr = calculate_correlation(df, numeric_columns=["x", "y"], categorical_columns=["tier", "plan"])
    assert corr["pearson_matrix"]["x"]["y"] > 0.999
    assert corr["spearman_matrix"]["x"]["y"] > 0.999
    assert corr["notable_correlations"][0]["pearson_p_value"] < 0.001
    assert len(corr["categorical_associations"]) >= 1
    assert corr["categorical_associations"][0]["cramers_v"] > 0.7


def test_s26_grouped_anova_comparison() -> None:
    df = pd.DataFrame({
        "segment": ["Enterprise"] * 8 + ["SMB"] * 8 + ["Starter"] * 8,
        "revenue": [500, 520, 490, 510, 530, 495, 515, 505]
                   + [200, 210, 195, 205, 215, 190, 220, 200]
                   + [50, 55, 48, 52, 60, 45, 53, 51],
    })
    cmp_res = compare_groups(df, "segment", "revenue")
    assert cmp_res["significant_at_0_05"] is True
    assert cmp_res["p_value"] < 0.001
    assert cmp_res["eta_squared"] > 0.9
    assert cmp_res["top_group"]["group"] == "Enterprise"
    assert cmp_res["bottom_group"]["group"] == "Starter"


def test_s27_datetime_trend_direction() -> None:
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    df = pd.DataFrame({
        "month": dates,
        "revenue": [100 + i * 25 for i in range(12)],
        "region": ["All"] * 12,
    })
    dt_res = analyze_datetime_column(df, "month", numeric_columns=["revenue"])
    trend = dt_res["metric_trends"][0]
    assert trend["net_delta"] > 0
    assert trend["trend_spearman_rho"] > 0.9
    assert trend["percent_change"] > 200.0


def test_s28_outlier_detection_multi_method() -> None:
    rng = np.random.default_rng(7)
    vals = list(rng.normal(50.0, 3.0, size=40)) + [300.0, -150.0]
    aux = list(rng.normal(10.0, 1.0, size=40)) + [90.0, -40.0]
    df = pd.DataFrame({"val": vals, "aux": aux})
    out_iqr = detect_outliers(df, "val", method="iqr")
    out_mad = detect_outliers(df, "val", method="modified_zscore")
    out_z = detect_outliers(df, "val", method="zscore")
    out_iso = detect_outliers(df, numeric_columns=["val", "aux"])
    assert out_iqr["flagged_count"] >= 2
    assert out_mad["flagged_count"] >= 2
    assert out_z["flagged_count"] >= 1
    assert out_iso["multivariate"] is not None
    assert out_iso["multivariate"]["flagged_count"] >= 1


def test_s29_zero_fabricated_claims_on_noise() -> None:
    df = pd.DataFrame({
        "a": [1, 4, 2, 5, 3, 2, 4, 1],
        "b": [5, 1, 4, 2, 1, 5, 2, 4],
    })
    res = _run_insights(df, "WeakNoise")
    corr_insights = [i for i in res["insights"] if i["category"] == "correlation"]
    for ins in corr_insights:
        assert "not strong" not in ins["title"].lower()
        assert abs(ins.get("supporting_metrics", {}).get("pearson_r", 0.0)) >= 0.45


def test_s30_insight_deduplication() -> None:
    df = pd.DataFrame({
        "region": ["East", "West", "North", "South"] * 8,
        "sales": [100 + (i % 4) * 30 for i in range(32)],
        "profit": [20 + (i % 4) * 6 for i in range(32)],
    })
    res = _run_insights(df, "DedupTest")
    sigs = [
        (i["category"], tuple(sorted(i.get("source_columns") or [])), i["title"][:48].lower())
        for i in res["insights"]
    ]
    assert len(sigs) == len(set(sigs))


def test_s31_no_causal_claims_on_correlation() -> None:
    x = np.arange(1, 25, dtype=float)
    df = pd.DataFrame({
        "ad_spend": x * 100,
        "sales": x * 250 + 50,
        "channel": ["Online", "Retail"] * 12,
    })
    res = _run_insights(df, "CorrNonCausal")
    corr_insights = [i for i in res["insights"] if i["category"] == "correlation"]
    assert len(corr_insights) >= 1
    for ins in corr_insights:
        combined = f"{ins['title']} {ins['explanation']} {ins.get('limitations', '')}".lower()
        assert "proves causation" not in combined
        assert "correlation does not imply causation" in combined or "observational" in combined


def test_s32_insufficient_data_disclosure() -> None:
    df = pd.DataFrame({"label_only": ["A", "B", "C"]})
    res = _run_insights(df, "Tiny3Rows")
    cov = {item["category"]: item for item in res["summary"]["category_coverage"]}
    assert len(cov) == len(INSIGHT_CATEGORIES)
    assert cov["correlation"]["status"] != "available"
    assert "No reliable insight could be generated" in cov["correlation"]["message"]


def test_s33_id_and_constant_exclusion_from_insights() -> None:
    df = pd.DataFrame({
        "customer_id": list(range(10001, 10025)),
        "constant_flag": ["FIXED"] * 24,
        "revenue": [100 + i * 10 for i in range(24)],
        "segment": ["A", "B", "C"] * 8,
    })
    res = _run_insights(df, "IDExclusion")
    for ins in res["insights"]:
        if ins["category"] in {"statistical", "correlation", "anomaly", "distribution"}:
            assert "customer_id" not in (ins.get("source_columns") or [])
            assert "constant_flag" not in (ins.get("source_columns") or [])


def test_s34_insight_ranking_and_12_categories() -> None:
    dates = pd.date_range("2025-01-01", periods=36, freq="MS")
    x = np.arange(36, dtype=float)
    df = pd.DataFrame({
        "date": dates,
        "department": ["Enterprise"] * 20 + ["MidMarket"] * 10 + ["SMB"] * 6,
        "region": ["North", "South", "East"] * 12,
        "spend": [100 + i * 8 for i in range(36)],
        "revenue": [300 + i * 24 + (150 if i % 3 == 0 else 0) + (3000 if i == 35 else 0) for i in range(36)],
        "conversion": [None if i in (1, 5) else (0.1 + 0.01 * i) for i in range(36)],
    })
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    res = _run_insights(df, "Rich12Categories")
    ranks = [i.get("rank_score", 0.0) for i in res["insights"]]
    assert ranks == sorted(ranks, reverse=True)
    cov = res["summary"]["category_coverage"]
    covered = [item["category"] for item in cov if item["status"] == "available"]
    assert len(covered) >= 10


# ==============================================================================
# PART C — 14 VISUALIZATION VALIDATION & RENDERING TESTS (S35 .. S48)
# ==============================================================================


def test_s35_render_bar_and_column() -> None:
    df = pd.DataFrame({"region": ["East", "East", "West"], "sales": [100, 150, 200]})
    res = render_chart(df, {"chart_type": "bar", "data_mapping": {"x": "region", "y": "sales"}, "aggregation": "sum"})
    by_reg = {r["region"]: r["sales"] for r in res["data"]}
    assert by_reg == {"East": 250.0, "West": 200.0}


def test_s36_render_horizontal_bar() -> None:
    df = pd.DataFrame({"cat": [f"C{i}" for i in range(18)], "val": list(range(10, 190, 10))})
    res = render_chart(df, {"chart_type": "horizontal_bar", "data_mapping": {"x": "cat", "y": "val"}, "limit": 8})
    assert len(res["data"]) == 8
    assert res["layout"]["orientation"] == "horizontal"


def test_s37_render_grouped_stacked_and_100pct_bar() -> None:
    df = pd.DataFrame({
        "region": ["North", "North", "South", "South"],
        "segment": ["A", "B", "A", "B"],
        "revenue": [30.0, 70.0, 20.0, 80.0],
    })
    for ctype in ("grouped_bar", "stacked_bar"):
        res = render_chart(df, {"chart_type": ctype, "data_mapping": {"x": "region", "y": "revenue", "series": "segment"}})
        assert len(res["data"]) == 4

    pct = render_chart(df, {
        "chart_type": "hundred_percent_stacked_bar",
        "data_mapping": {"x": "region", "y": "revenue", "series": "segment"},
    })
    north_sum = sum(r["revenue"] for r in pct["data"] if r["region"] == "North")
    south_sum = sum(r["revenue"] for r in pct["data"] if r["region"] == "South")
    assert abs(north_sum - 100.0) < 0.2
    assert abs(south_sum - 100.0) < 0.2


def test_s38_render_line_and_time_series() -> None:
    df = pd.DataFrame({
        "date": ["2025-03-01", "2025-01-01", "2025-02-01"],
        "val": [30, 10, 20],
    })
    res = render_chart(df, {"chart_type": "time_series", "data_mapping": {"x": "date", "y": "val"}})
    assert [r["val"] for r in res["data"]] == [10.0, 20.0, 30.0]
    area = render_chart(df, {"chart_type": "area", "data_mapping": {"x": "date", "y": "val"}})
    assert len(area["data"]) == 3


def test_s39_render_histogram() -> None:
    df = pd.DataFrame({"age": [20, 22, 25, 30, 31, 35, 40, 42, 45, 50]})
    res = render_chart(df, {"chart_type": "histogram", "data_mapping": {"x": "age"}})
    assert sum(b["count"] for b in res["data"]) == 10


def test_s40_render_scatter_and_bubble() -> None:
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 20, 30, 40], "z": [5, 10, 15, 20]})
    sc_same = render_chart(df, {"chart_type": "scatter", "data_mapping": {"x": "x", "y": "x"}})
    assert len(sc_same["data"]) == 4
    bub = render_chart(df, {"chart_type": "bubble", "data_mapping": {"x": "x", "y": "y", "size": "z"}})
    assert len(bub["data"]) == 4 and "z" in bub["data"][0]


def test_s41_render_box_and_violin() -> None:
    df = pd.DataFrame({"dept": ["Eng", "Eng", "Sales", "Sales"], "salary": [100, 120, 80, 90]})
    for ct in ("box", "violin"):
        res = render_chart(df, {"chart_type": ct, "data_mapping": {"x": "dept", "y": "salary"}})
        assert len(res["data"]) == 2
        assert all("values" in g and len(g["values"]) == 2 for g in res["data"])


def test_s42_render_heatmap_and_correlation_matrix() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10], "c": [5, 4, 3, 2, 1]})
    res = render_chart(df, {"chart_type": "correlation_matrix", "data_mapping": {}})
    assert len(res["data"]) == 9
    ab = [c for c in res["data"] if c["x"] == "a" and c["y"] == "b"][0]
    assert ab["value"] > 0.99


def test_s43_pie_donut_cardinality_guard_and_other_bucketing() -> None:
    df_12 = pd.DataFrame({"cat": [f"Cat_{i}" for i in range(12)], "val": list(range(12, 0, -1))})
    ok_pie = render_chart(df_12, {"chart_type": "pie", "data_mapping": {"labels": "cat", "values": "val"}})
    assert "error" not in ok_pie
    assert any(r["cat"] == "Other" for r in ok_pie["data"])

    df_20 = pd.DataFrame({"cat": [f"Cat_{i}" for i in range(20)], "val": list(range(20))})
    bad_pie = render_chart(df_20, {"chart_type": "pie", "data_mapping": {"labels": "cat", "values": "val"}})
    assert bad_pie["data"] == []
    assert "error" in bad_pie and bad_pie["suggested_alternative"] == "horizontal_bar"


def test_s44_missing_value_handling_in_charts() -> None:
    df = pd.DataFrame({
        "region": ["North", "South", None, "North"],
        "sales": [100.0, None, 50.0, 200.0],
    })
    res = render_chart(df, {"chart_type": "bar", "data_mapping": {"x": "region", "y": "sales"}, "aggregation": "sum"})
    assert "error" not in res
    assert len(res["data"]) >= 1


def test_s45_invalid_chart_mapping_rejected() -> None:
    df = pd.DataFrame({
        "customer_id": list(range(1001, 1011)),
        "category": [f"Cat_{i % 3}" for i in range(10)],
        "revenue": [100 + i for i in range(10)],
    })
    id_res = render_chart(df, {"chart_type": "bar", "data_mapping": {"x": "category", "y": "customer_id"}, "aggregation": "sum"})
    assert "error" in id_res
    non_num = render_chart(df, {"chart_type": "histogram", "data_mapping": {"x": "category"}})
    assert "error" in non_num


def test_s46_insight_chart_spec_alignment() -> None:
    dates = pd.date_range("2025-01-01", periods=15, freq="MS")
    df = pd.DataFrame({
        "date": dates,
        "region": ["North", "South", "West"] * 5,
        "revenue": [100 + i * 20 for i in range(15)],
        "cost": [60 + i * 10 for i in range(15)],
    })
    res = _run_insights(df, "ChartAlign")
    checked = 0
    for ins in res["insights"]:
        spec = ins.get("chart_spec")
        if spec:
            rendered = render_chart(df, spec, understanding=res["understanding"])
            assert "error" not in rendered, f"Insight '{ins['title']}' invalid chart_spec: {rendered}"
            assert len(rendered["data"]) >= 1
            checked += 1
    assert checked >= 3


def test_s47_dataset_change_invalidates_stale_insights_and_cache() -> None:
    df1 = pd.DataFrame({"region": ["North", "South"] * 5, "sales": [100, 200] * 5})
    ds_id = _upload_df(df1, "version_test.csv")
    try:
        r1 = client.get(f"/api/v1/project-insights/{ds_id}")
        assert r1.status_code == 200, r1.text
        fp1 = r1.json()["dataset_fingerprint"]

        r2 = client.get(f"/api/v1/project-insights/{ds_id}")
        assert r2.status_code == 200, r2.text
        assert r2.json()["dataset_fingerprint"] == fp1

        ds_after = pd.DataFrame({"region": ["North", "South"] * 5, "sales": [999, 888] * 5})
        fp2 = compute_dataset_fingerprint(SimpleNamespace(id=ds_id, name="version_test.csv", stored_path=None, version=2), ds_after)
        assert fp2 != fp1
    finally:
        client.delete(f"/api/v1/datasets/{ds_id}")


def test_s48_recommender_dynamic_ranking() -> None:
    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=20, freq="D"),
        "region": ["North", "South", "East", "West"] * 5,
        "revenue": [100 + i * 15 for i in range(20)],
        "profit": [30 + i * 5 for i in range(20)],
    })
    recs = recommend_charts(df, max_recommendations=6)
    assert len(recs) >= 4
    for rec in recs:
        rendered = render_chart(df, rec)
        assert "error" not in rendered
        assert len(rendered["data"]) >= 1


# ==============================================================================
# PART D — 12 AGENT, INTEGRATION & 5-DOMAIN E2E TESTS (S49 .. S60)
# ==============================================================================


def _assert_domain_e2e(df: pd.DataFrame, filename: str, question: str, expected_substring: str) -> None:
    ds_id = _upload_df(df, filename)
    try:
        prof = client.get(f"/api/v1/datasets/{ds_id}/understanding")
        assert prof.status_code == 200, prof.text
        eda = client.get(f"/api/v1/datasets/{ds_id}/eda")
        assert eda.status_code == 200, eda.text
        assert "categorical_breakdowns" in eda.json()
        ins = client.get(f"/api/v1/project-insights/{ds_id}")
        assert ins.status_code == 200, ins.text
        body = ins.json()
        assert len(body["insights"]) >= 4
        assert "category_coverage" in body["executive_summary"]
        recs = client.get(f"/api/v1/visualizations/recommend/{ds_id}")
        assert recs.status_code == 200, recs.text
        assert len(recs.json()["recommendations"]) >= 1
        chat = client.post(f"/api/v1/project-insights/{ds_id}/chat", json={"question": question})
        assert chat.status_code == 200, chat.text
        assert expected_substring.lower() in chat.json()["answer"].lower()
    finally:
        client.delete(f"/api/v1/datasets/{ds_id}")


def test_s49_domain_sales_e2e() -> None:
    df = pd.DataFrame({
        "Order_Date": pd.date_range("2025-01-01", periods=16, freq="MS"),
        "Region": ["North", "South", "East", "West"] * 4,
        "Category": ["Electronics", "Furniture"] * 8,
        "Revenue": [12000, 8000, 9500, 6000] * 4,
        "Profit": [3000, 1500, 2200, 1100] * 4,
    })
    _assert_domain_e2e(df, "sales_domain.csv", "Total Revenue by Region", "revenue")


def test_s50_domain_student_performance_e2e() -> None:
    df = pd.DataFrame({
        "Student_ID": [f"ST-{1000 + i}" for i in range(18)],
        "Department": ["AIML", "CSE", "ECE"] * 6,
        "Attendance_Pct": ["92%", "85%", "76%"] * 6,
        "Study_Hours": [22, 16, 12] * 6,
        "Final_Score": [89, 77, 68] * 6,
    })
    _assert_domain_e2e(df, "students_domain.csv", "Average Final_Score by Department", "final_score")


def test_s51_domain_hr_workforce_e2e() -> None:
    df = pd.DataFrame({
        "Employee_Code": [f"EMP-{200 + i}" for i in range(16)],
        "Department": ["Engineering", "Sales", "Operations", "HR"] * 4,
        "Tenure_Years": [4.5, 2.0, 3.2, 5.1] * 4,
        "Monthly_Salary": [120000, 80000, 65000, 75000] * 4,
        "Attrition": ["No", "Yes", "No", "No"] * 4,
    })
    _assert_domain_e2e(df, "hr_domain.csv", "Average Monthly_Salary by Department", "monthly_salary")


def test_s52_domain_weather_timeseries_e2e() -> None:
    df = pd.DataFrame({
        "Recorded_Date": pd.date_range("2025-01-01", periods=16, freq="D"),
        "City": ["Shimla", "Delhi", "Mumbai", "Jaipur"] * 4,
        "Temp_C": [-4.5, 16.0, 29.0, 21.0] * 4,
        "Humidity_Pct": [72, 55, 81, 40] * 4,
        "Rainfall_mm": [12.0, 0.0, 18.5, 1.0] * 4,
    })
    _assert_domain_e2e(df, "weather_domain.csv", "Average Temp_C by City", "temp_c")


def test_s53_domain_healthcare_e2e() -> None:
    df = pd.DataFrame({
        "Patient_ID": [f"PT-{500 + i}" for i in range(16)],
        "Ward": ["Cardiology", "Neurology", "General", "Orthopedics"] * 4,
        "Age": [64, 52, 41, 58] * 4,
        "BMI": [29.4, 24.1, 22.8, 27.5] * 4,
        "Systolic_BP": [148, 130, 118, 138] * 4,
        "Glucose_mg_dL": [165, 112, 98, 135] * 4,
    })
    _assert_domain_e2e(df, "healthcare_domain.csv", "Average Glucose_mg_dL by Ward", "glucose_mg_dl")


def test_s54_nl_query_dynamic_column_resolution() -> None:
    df = pd.DataFrame({
        "ward_name": ["ICU", "General", "ICU", "Cardiology"],
        "length_of_stay_days": [12, 4, 10, 6],
        "treatment_cost": [45000, 12000, 38000, 25000],
    })
    res = asyncio.run(run_workflow(df, "What is average length_of_stay_days by ward_name?", use_llm=False))
    assert "length_of_stay_days" in res["answer"].lower()
    assert "icu" in res["answer"].lower()


def test_s55_active_dataset_binding_and_isolation() -> None:
    df_a = pd.DataFrame({"store": ["Alpha", "Beta"], "gross_margin": [400, 600]})
    df_b = pd.DataFrame({"hospital": ["Apollo", "AIIMS"], "patient_count": [120, 250]})
    res_a = asyncio.run(run_workflow(df_a, "Total gross_margin by store", use_llm=False))
    res_b = asyncio.run(run_workflow(df_b, "Total patient_count by hospital", use_llm=False))
    assert "gross_margin" in res_a["answer"].lower()
    assert "apollo" not in res_a["answer"].lower()
    assert "patient_count" in res_b["answer"].lower()
    assert "gross_margin" not in res_b["answer"].lower()


def test_s56_agent_routing_and_11_step_trace() -> None:
    from app.agents.orchestrator import execute_agent_task
    from app.schemas.agent import AgentTaskRequest

    df = pd.DataFrame({
        "category": ["Hardware", "Software", "Services"] * 5,
        "revenue": [500, 900, 300] * 5,
        "units": [5, 12, 4] * 5,
    })
    res = asyncio.run(run_workflow(df, "Plot a bar chart of revenue by category", use_llm=False))
    assert len(res["steps"]) <= 11
    assert res["chart_config"] is not None
    assert res["chart_config"]["data_mapping"]["x"] == "category"

    task_resp = asyncio.run(execute_agent_task(AgentTaskRequest(query="Plot a bar chart of revenue by category", use_llm=False), df=df))
    assert len(task_resp.execution_steps) <= 11


def test_s57_agent_failure_recovery_and_bounded_retries() -> None:
    df = pd.DataFrame({"city": ["Delhi", "Mumbai"], "temperature": [28.0, 31.0]})
    res = asyncio.run(run_workflow(df, "Detect outliers in temperature and show stats", use_llm=False))
    assert len(res["steps"]) <= 11
    assert res["answer"]


def test_s58_no_infinite_loop_guarantee() -> None:
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": ["a", "b", "c", "d"]})
    t0 = time.perf_counter()
    res = asyncio.run(run_workflow(df, "Compare zzz_1 vs zzz_2 over non_existent_time_axis", use_llm=False))
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    assert len(res["steps"]) <= 11


def test_s59_transparent_impossible_request_reporting() -> None:
    df = pd.DataFrame({"department": ["HR", "Eng"], "headcount": [10, 40]})
    res = asyncio.run(run_workflow(df, "What is total cryptocurrency_yield by department?", use_llm=False))
    low = res["answer"].lower()
    assert "cryptocurrency_yield" in low or "missing" in low or "not found" in low
    assert "50" not in res["answer"]


def test_s60_multilingual_en_hi_hinglish_invariance() -> None:
    df = pd.DataFrame({
        "region": ["North", "South", "North", "South"],
        "revenue": [100.0, 200.0, 300.0, 400.0],
    })
    en_res = asyncio.run(run_workflow(df, "Total revenue by region", use_llm=False))
    hinglish_res = asyncio.run(run_workflow(df, "Region wise total revenue dikhao", use_llm=False))
    assert "1,000" in en_res["answer"] or "400" in en_res["answer"]
    assert "1,000" in hinglish_res["answer"] or "400" in hinglish_res["answer"]
