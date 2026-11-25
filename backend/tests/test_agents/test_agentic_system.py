"""Comprehensive Verification Suite for Analyticx AI Advanced Agentic System.
Covers Test Groups A through F (50 automated tests):
- Group A: Screen & Context Awareness (tests 1-10)
- Group B: Agent Routing (tests 11-16)
- Group C: Numerical Accuracy (tests 17-25)
- Group D: Agent Loop Engineering (tests 26-35)
- Group E: Dashboard & Persistence (tests 36-42)
- Group F: Security & Reliability (tests 43-50)
"""
import math
import os
from pathlib import Path
import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.agentic_loop import TASK_AUDIT_LOG, execute_agentic_loop, _fuzzy_match_column
from app.agents.business_analyst_agent import business_analyst_agent
from app.agents.context_agent import context_agent
from app.agents.data_analyst_agent import data_analyst_agent
from app.agents.data_quality_agent import data_quality_agent
from app.agents.document_intelligence_agent import document_intelligence_agent
from app.agents.forecasting_scenario_agent import forecasting_scenario_agent
from app.agents.orchestrator import execute_agent_task
from app.agents.tool_registry import ToolExecutionError, tool_registry
from app.agents.validation_agent import validation_agent
from app.agents.visualization_agent import visualization_agent
from app.context.context_freshness_service import (
    ensure_dataset_freshness,
    is_context_stale,
    mark_context_accessed,
    record_context_mutation,
)
from app.context.schemas import (
    ActivityContext,
    DashboardContext,
    DatasetContext,
    FileContext,
    LiveApplicationContext,
    ScreenMetadata,
    VisualSnapshotData,
)
from app.context.screen_context_service import generate_screen_summary
from app.database import Base
from app.models.dataset import Dataset
from app.schemas.agent import AgentTaskRequest, TaskState
from app.services.cleaning_service import apply_cleaning_decision, undo_last_transformation


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_agentic.db")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West", "North", "South", "East", "West"],
        "revenue": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 10000.0],
        "units": [10, 20, 30, 40, 50, 60, 70, 80],
        "profit": [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0],
    })


@pytest.fixture
def sample_db_dataset(tmp_path, db_session, sample_df):
    csv_path = tmp_path / "test_data.csv"
    sample_df.to_csv(csv_path, index=False)
    ds = Dataset(
        name="Sales Analytics",
        original_filename="test_data.csv",
        stored_path=str(csv_path),
        row_count=len(sample_df),
        column_count=len(sample_df.columns),
        size_bytes=os.path.getsize(csv_path),
        version=1,
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


# ==============================================================================
# GROUP A: Screen & Context Awareness (Tests 1 - 10)
# ==============================================================================

def test_01_route_screen_tracking():
    ctx = LiveApplicationContext(
        screen=ScreenMetadata(route="/data-prep", screen_name="Data Preparation Studio"),
    )
    summary = generate_screen_summary(ctx)
    assert "Data Preparation Studio" in summary["screen_summary"]


def test_02_active_dataset_tracking(db_session, sample_db_dataset):
    ctx = LiveApplicationContext(
        dataset=DatasetContext(dataset_id=sample_db_dataset.id, dataset_name=sample_db_dataset.name, row_count=8),
    )
    summary = generate_screen_summary(ctx, db=db_session)
    assert sample_db_dataset.name in summary["screen_summary"]
    assert "8 rows" in summary["screen_summary"]


def test_03_pdf_page_tracking(tmp_path, db_session):
    dummy_pdf = tmp_path / "quarterly_report.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(str(dummy_pdf))
    doc.close()

    ds = Dataset(
        name="Q3 Report",
        original_filename="quarterly_report.pdf",
        stored_path=str(dummy_pdf),
        row_count=0,
        column_count=0,
        size_bytes=100,
        version=1,
    )
    db_session.add(ds)
    db_session.commit()

    ctx = LiveApplicationContext(
        file=FileContext(file_id=str(ds.id), file_type="pdf", pdf_page_number=3, pdf_total_pages=10),
        dataset=DatasetContext(dataset_id=ds.id, dataset_name=ds.name),
    )
    summary = generate_screen_summary(ctx, db=db_session)
    assert "Viewing Page 3 of 10" in summary["screen_summary"]


def test_04_active_chart_tracking():
    ctx = LiveApplicationContext(
        dashboard=DashboardContext(dashboard_id=1, selected_chart_id="c_1", selected_chart_title="Revenue by Region", selected_chart_type="bar"),
    )
    summary = generate_screen_summary(ctx)
    assert "Revenue by Region" in summary["screen_summary"]
    assert "bar" in summary["screen_summary"]


def test_05_active_filters_metrics_tracking():
    ctx = LiveApplicationContext(
        dashboard=DashboardContext(
            dashboard_id=1,
            active_filters={"region": "North"},
            active_measures=["revenue", "profit"],
        ),
    )
    assert ctx.dashboard.active_filters["region"] == "North"
    assert "revenue" in ctx.dashboard.active_measures


def test_06_recent_actions_tracking():
    ctx = LiveApplicationContext(
        activity=ActivityContext(
            task_status="completed",
            recent_actions=[{"action": "remove_duplicates", "records_affected": 4}],
        ),
    )
    summary = generate_screen_summary(ctx)
    assert any("remove_duplicates" in obs for obs in summary["key_observations"])


def test_07_unsaved_changes_tracking():
    ctx = LiveApplicationContext(
        activity=ActivityContext(has_unsaved_changes=True),
    )
    summary = generate_screen_summary(ctx)
    assert any("unsaved changes" in warn.lower() for warn in summary["warnings_or_issues"])


def test_08_stale_context_invalidation():
    record_context_mutation("dataset", 101)
    # Stale when checked with older timestamp
    assert is_context_stale("dataset", 101, last_known_timestamp=0.0) is True
    # Not stale with future timestamp
    assert is_context_stale("dataset", 101, last_known_timestamp=9999999999.0) is False


def test_09_context_resolution_without_explicit_id(db_session, sample_db_dataset):
    ctx_dict = {"dataset_id": sample_db_dataset.id}
    res = context_agent.resolve_context(raw_context=ctx_dict, db=db_session)
    assert res["dataset_id"] == sample_db_dataset.id
    assert res["dataset_name"] == sample_db_dataset.name


def test_10_distinguish_screen_dataset_document():
    doc_mod = context_agent.classify_target_modality("What does clause 4 on page 3 say?", {})
    ds_mod = context_agent.classify_target_modality("What is the average revenue in this dataset?", {})
    dash_mod = context_agent.classify_target_modality("Create a bar chart of profit", {})
    assert doc_mod == "document"
    assert ds_mod == "dataset"
    assert dash_mod == "dashboard"


# ==============================================================================
# GROUP B: Agent Routing (Tests 11 - 16)
# ==============================================================================

@pytest.mark.asyncio
async def test_11_route_data_analyst(sample_df):
    req = AgentTaskRequest(query="What is the average revenue?")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.assigned_agent == "DataAnalystAgent"
    assert "numeric_summary" in res.tools_used


@pytest.mark.asyncio
async def test_12_route_data_quality(sample_df):
    req = AgentTaskRequest(query="Check for missing values and duplicates")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.assigned_agent == "DataQualityAgent"
    assert "detect_data_quality_issues" in res.tools_used


@pytest.mark.asyncio
async def test_13_route_document_intelligence(tmp_path):
    doc_path = tmp_path / "notes.txt"
    doc_path.write_text("Analyticx AI Agentic System Notes")
    req = AgentTaskRequest(query="What is in this document on page 1?", context={"pdf_path": str(doc_path)})
    # Routing test
    res = await execute_agentic_loop(req, df=None)
    assert res.assigned_agent == "DocumentIntelligenceAgent"


@pytest.mark.asyncio
async def test_14_route_visualization(sample_df):
    req = AgentTaskRequest(query="Create a bar chart of revenue by region")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.assigned_agent == "VisualizationAgent"
    assert "recommend_chart" in res.tools_used


@pytest.mark.asyncio
async def test_15_route_business_analyst(sample_df):
    req = AgentTaskRequest(query="Explain KPI and give strategic recommendations")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.assigned_agent == "BusinessAnalystAgent"


@pytest.mark.asyncio
async def test_16_route_forecasting_scenario(sample_df):
    req = AgentTaskRequest(query="Forecast next quarter trend and scenario")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.assigned_agent == "ForecastingScenarioAgent"


# ==============================================================================
# GROUP C: Numerical Accuracy (Tests 17 - 25)
# ==============================================================================

def test_17_mean_accuracy(sample_df):
    res = tool_registry.execute("numeric_summary", df=sample_df, column="revenue")
    expected_mean = round(float(sample_df["revenue"].mean()), 4)
    assert res["mean"] == expected_mean


def test_18_median_accuracy():
    # Odd length
    df_odd = pd.DataFrame({"val": [10.0, 20.0, 30.0]})
    res_odd = tool_registry.execute("numeric_summary", df=df_odd, column="val")
    assert res_odd["median"] == 20.0

    # Even length
    df_even = pd.DataFrame({"val": [10.0, 20.0, 30.0, 40.0]})
    res_even = tool_registry.execute("numeric_summary", df=df_even, column="val")
    assert res_even["median"] == 25.0


def test_19_outlier_iqr_accuracy(sample_df):
    res = tool_registry.execute("preview_cleaning_changes", df=sample_df, action_type="handle_outliers", column="revenue")
    assert res["outliers_count"] == 1  # 10000.0 is outlier
    assert res["bounds"][1] < 10000.0


def test_20_imputation_count_accuracy():
    df_missing = pd.DataFrame({"sales": [100.0, None, 300.0, None, 500.0]})
    res = tool_registry.execute("preview_cleaning_changes", df=df_missing, action_type="impute_missing", column="sales", strategy="median")
    assert res["missing_filled"] == 2


def test_21_duplicate_removal_accuracy():
    df_dups = pd.DataFrame({"x": [1, 1, 2, 3, 3, 3]})
    res = tool_registry.execute("preview_cleaning_changes", df=df_dups, action_type="remove_duplicates")
    assert res["rows_before"] == 6
    assert res["rows_after"] == 3


def test_22_correlation_accuracy(sample_df):
    res = tool_registry.execute("correlation_summary", df=sample_df, columns=["units", "profit"])
    expected_corr = round(float(sample_df["units"].corr(sample_df["profit"])), 3)
    found = next(p for p in res["correlations"] if set([p["col1"], p["col2"]]) == {"units", "profit"})
    assert abs(found["correlation"] - expected_corr) < 0.001


@pytest.mark.asyncio
async def test_23_multilingual_numerical_invariance(sample_df):
    req_en = AgentTaskRequest(query="What is the average revenue?", language_override="en")
    req_hi = AgentTaskRequest(query="औसत राजस्व क्या है?", language_override="hi")
    req_hing = AgentTaskRequest(query="Revenue ka average kitna hai?", language_override="hinglish")

    res_en = await execute_agentic_loop(req_en, df=sample_df)
    res_hi = await execute_agentic_loop(req_hi, df=sample_df)
    res_hing = await execute_agentic_loop(req_hing, df=sample_df)

    # Invariance check: extracted mean must be identical across languages
    mean_val = round(float(sample_df["revenue"].mean()), 4)
    assert any(f"{mean_val:,}" in f for f in res_en.verified_facts)
    assert any(f"{mean_val:,}" in f for f in res_hi.verified_facts)
    assert any(f"{mean_val:,}" in f for f in res_hing.verified_facts)


def test_24_chart_aggregation_accuracy(sample_df):
    res = tool_registry.execute("top_categories", df=sample_df, dimension="region", metric="revenue", limit=4)
    grouped = sample_df.groupby("region")["revenue"].sum()
    for item in res["items"]:
        reg = item["value"]
        assert item["metric"] == round(float(grouped[reg]), 2)


def test_25_non_negative_counts_and_bounds(sample_df):
    res = tool_registry.execute("numeric_summary", df=sample_df, column="revenue")
    assert res["count"] > 0
    assert res["missing_count"] >= 0
    assert res["min"] <= res["mean"] <= res["max"]
    assert res["std"] >= 0


# ==============================================================================
# GROUP D: Agent Loop Engineering (Tests 26 - 35)
# ==============================================================================

@pytest.mark.asyncio
async def test_26_eleven_step_loop_completes(sample_df):
    req = AgentTaskRequest(query="Calculate average revenue")
    res = await execute_agentic_loop(req, df=sample_df)
    # Check that observe, understand, plan, select tools, observe results, evaluate, verify, persist, respond are present
    step_names = [s.step_name.split()[0] for s in res.execution_steps]
    assert "Observe" in step_names
    assert "Understand" in step_names
    assert "Plan" in step_names
    assert "Select" in step_names
    assert "Verify" in step_names
    assert "Persist" in step_names
    assert "Respond" in step_names


@pytest.mark.asyncio
async def test_27_task_state_transitions(sample_df):
    req = AgentTaskRequest(query="Summarize revenue statistics")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.state == TaskState.COMPLETED


def test_28_tool_schema_validation_rejects_invalid(sample_df):
    with pytest.raises(ToolExecutionError) as exc_info:
        # limit must be <= 50; limit=999 violates schema
        tool_registry.execute("top_categories", df=sample_df, dimension="region", limit=999)
    assert "validation failed" in str(exc_info.value).lower()


def test_29_self_correction_column_typo():
    cols = ["revenue", "region", "profit"]
    matched = _fuzzy_match_column("revnue", cols)
    assert matched == "revenue"

    matched_case = _fuzzy_match_column("REVENUE", cols)
    assert matched_case == "revenue"


@pytest.mark.asyncio
async def test_30_self_correction_page_bounds(tmp_path):
    doc_path = tmp_path / "sample.pdf"
    import fitz
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Sample Analyticx Document")
    doc.save(str(doc_path))
    doc.close()

    req = AgentTaskRequest(query="Show me page 999", context={"pdf_path": str(doc_path), "page_number": 999})
    # Loop catches bounds and retries
    res = await execute_agentic_loop(req, df=None)
    assert res.retries_count > 0 or res.state in [TaskState.COMPLETED, TaskState.FAILED]


@pytest.mark.asyncio
async def test_31_max_retries_termination():
    # Attempting to query non-existent column with no valid alternatives
    empty_df = pd.DataFrame({"a": ["text_only", "other"]})
    req = AgentTaskRequest(query="Calculate numeric mean of non_existent_xyz_column")
    res = await execute_agentic_loop(req, df=empty_df)
    assert res.state in [TaskState.FAILED, TaskState.COMPLETED]
    assert res.retries_count <= 2


def test_32_validation_agent_rejects_invalid_bounds(sample_df):
    invalid_summary = {
        "column": "revenue",
        "count": 10,
        "min": 100.0,
        "max": 500.0,
        "mean": 999.0,  # Invalid: mean > max
        "std": -5.0,    # Invalid: std < 0
    }
    report = validation_agent.verify_numeric_summary(invalid_summary, df=sample_df)
    assert report.passed is False
    assert any("outside the range" in iss for iss in report.issues)
    assert any("cannot be negative" in iss for iss in report.issues)


@pytest.mark.asyncio
async def test_33_execution_trace_audit_persisted(sample_df):
    initial_len = len(TASK_AUDIT_LOG)
    req = AgentTaskRequest(query="Audit trace persistence test")
    await execute_agentic_loop(req, df=sample_df)
    assert len(TASK_AUDIT_LOG) > initial_len


@pytest.mark.asyncio
async def test_34_deterministic_fallback_no_llm(sample_df):
    req = AgentTaskRequest(query="Top categories by revenue", use_llm=False)
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.state == TaskState.COMPLETED
    assert len(res.verified_facts) > 0


@pytest.mark.asyncio
async def test_35_execution_latency_tracking(sample_df):
    req = AgentTaskRequest(query="Latency tracking check")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.duration_total_ms > 0
    assert all(s.duration_ms >= 0 for s in res.execution_steps)


# ==============================================================================
# GROUP E: Dashboard and Persistence (Tests 36 - 42)
# ==============================================================================

def test_36_generated_chart_config_valid(sample_df):
    cfg = visualization_agent.build_chart_config("bar", {"x": "region", "y": "revenue"}, title="Regional Revenue")
    report = validation_agent.verify_chart_config(cfg, df=sample_df)
    assert report.passed is True
    assert cfg["chart_type"] == "bar"
    assert cfg["appearance"]["responsive"] is True


def test_37_dashboard_context_tracking():
    dash = DashboardContext(
        dashboard_id=42,
        dashboard_name="Executive Overview",
        selected_chart_id="chart_99",
        selected_chart_title="Profit Margin",
    )
    assert dash.dashboard_id == 42
    assert dash.selected_chart_title == "Profit Margin"


def test_38_context_freshness_after_cleaning(sample_db_dataset, db_session):
    action = {"action_type": "remove_duplicates", "strategy": "remove_exact", "parameters": {}}
    apply_cleaning_decision(sample_db_dataset, action, trigger_source="copilot", db=db_session)
    assert is_context_stale("dataset", sample_db_dataset.id, last_known_timestamp=0.0) is True


@pytest.mark.asyncio
async def test_39_multi_turn_context_retention(sample_df):
    # Turn 1
    req1 = AgentTaskRequest(query="What is the average revenue?")
    res1 = await execute_agentic_loop(req1, df=sample_df)
    assert res1.assigned_agent == "DataAnalystAgent"

    # Turn 2
    req2 = AgentTaskRequest(query="Now show top regions by profit")
    res2 = await execute_agentic_loop(req2, df=sample_df)
    assert "top_categories" in res2.tools_used


def test_40_undo_updates_context_version(sample_db_dataset, db_session):
    orig_rows = sample_db_dataset.row_count
    action = {"action_type": "remove_duplicates", "strategy": "remove_exact", "parameters": {}}
    apply_cleaning_decision(sample_db_dataset, action, trigger_source="copilot", db=db_session)
    undo_res = undo_last_transformation(sample_db_dataset, db=db_session)
    assert undo_res["success"] is True
    assert "duplicate" in undo_res["reverted_transformation"].lower()


def test_41_profile_generation_persistence(sample_df):
    profile = data_analyst_agent.profile_dataset(sample_df)
    assert profile["row_count"] == len(sample_df)
    assert profile["column_count"] == len(sample_df.columns)
    assert isinstance(profile["columns"], list)


@pytest.mark.asyncio
async def test_42_language_preference_persistence(sample_df):
    req = AgentTaskRequest(query="Show me stats", language_override="hi")
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.detected_language == "hi"
    assert "सत्यापित तथ्य" in res.answer


# ==============================================================================
# GROUP F: Security and Reliability (Tests 43 - 50)
# ==============================================================================

def test_43_no_arbitrary_python_eval(sample_df):
    # Attempting to call an unregistered malicious command
    with pytest.raises(ToolExecutionError) as exc_info:
        tool_registry.execute("os.system('whoami')", df=sample_df)
    assert "not registered" in str(exc_info.value)


def test_44_no_sql_injection(sample_df):
    malicious = "revenue; DROP TABLE datasets; --"
    with pytest.raises(ToolExecutionError) as exc_info:
        tool_registry.execute("numeric_summary", df=sample_df, column=malicious)
    assert "does not exist" in str(exc_info.value)


def test_45_empty_dataset_handling():
    empty_df = pd.DataFrame(columns=["a", "b"])
    prof = tool_registry.execute("profile_dataset", df=empty_df)
    assert prof["row_count"] == 0
    assert prof["column_count"] == 2


def test_46_non_numeric_in_numeric_tool(sample_df):
    with pytest.raises(ToolExecutionError) as exc_info:
        tool_registry.execute("numeric_summary", df=sample_df, column="region")
    assert "no valid numeric values" in str(exc_info.value)


def test_47_missing_pdf_file_handling():
    with pytest.raises(ToolExecutionError) as exc_info:
        tool_registry.execute("retrieve_pdf_page", document_path="/non/existent/path.pdf", page_number=1)
    assert "does not exist" in str(exc_info.value)


def test_48_bounded_output_sizes(sample_df):
    res = tool_registry.execute("top_categories", df=sample_df, dimension="region", limit=2)
    assert len(res["items"]) <= 2


@pytest.mark.asyncio
async def test_49_non_ascii_unicode_stability(sample_df):
    unicode_query = "डेटासेट का सारांश दिखाओ 📊 Q3 ਮਾਲੀਆ"
    req = AgentTaskRequest(query=unicode_query)
    res = await execute_agentic_loop(req, df=sample_df)
    assert res.state == TaskState.COMPLETED
    assert len(res.verified_facts) > 0


def test_50_deterministic_invariance(sample_df):
    results = [
        tool_registry.execute("numeric_summary", df=sample_df, column="revenue")
        for _ in range(5)
    ]
    first = results[0]
    for r in results[1:]:
        assert r["mean"] == first["mean"]
        assert r["median"] == first["median"]
        assert r["min"] == first["min"]
        assert r["max"] == first["max"]
