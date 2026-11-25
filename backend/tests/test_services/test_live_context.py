"""Tests for Analyticx AI's Shared Live Application Context Engine and Screen Intelligence."""
import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.context.schemas import (
    ActivityContext,
    DashboardContext,
    DatasetContext,
    FileContext,
    LiveApplicationContext,
    ScreenExplanationRequest,
    ScreenMetadata,
    VisualAnalysisRequest,
    VisualSnapshotData,
)
from app.context.screen_context_service import (
    analyze_visual_screen,
    explain_active_screen,
    generate_screen_summary,
)
from app.context.context_freshness_service import (
    ensure_dataset_freshness,
    is_context_stale,
    record_context_mutation,
)
from app.database import Base
from app.models.dataset import Dataset


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test_context.db")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_dataset(tmp_path, db_session):
    csv_file = tmp_path / "sales_screen.csv"
    data = {
        "region": ["North", "South", "East", "West"],
        "revenue": [50000.0, 32000.0, 41000.0, None],  # 1 missing
        "margin": [0.22, 0.18, 0.25, 0.15],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)

    ds = Dataset(
        name="Sales Screen Test",
        original_filename="sales_screen.csv",
        stored_path=str(csv_file),
        size_bytes=csv_file.stat().st_size,
        row_count=len(df),
        column_count=len(df.columns),
        status="Needs Attention",
        version=1,
        quality_score=68.0,
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


def test_screen_summary_for_dataset(sample_dataset, db_session):
    ctx = LiveApplicationContext(
        screen=ScreenMetadata(
            route=f"/data-prep/{sample_dataset.id}",
            screen_name="Data Preparation & Automated EDA Studio",
        ),
        file=FileContext(
            file_id=str(sample_dataset.id),
            file_name=sample_dataset.name,
            file_type="csv",
        ),
        dataset=DatasetContext(
            dataset_id=sample_dataset.id,
            dataset_name=sample_dataset.name,
            version=sample_dataset.version,
            row_count=sample_dataset.row_count,
            column_count=sample_dataset.column_count,
            quality_score=sample_dataset.quality_score,
            focused_column="revenue",
            pending_decisions_count=2,
        ),
        activity=ActivityContext(
            recent_actions=[{"action": "Loaded dataset", "timestamp": "2026-10-20T12:00:00"}],
            task_status="idle",
        ),
    )

    summary = generate_screen_summary(ctx, db=db_session)
    assert "Sales Screen Test" in summary["screen_summary"]
    assert "4 rows" in summary["screen_summary"]
    assert any("revenue" in obs for obs in summary["key_observations"])
    assert any("missing value" in w for w in summary["warnings_or_issues"])
    assert len(summary["recommended_next_steps"]) > 0


def test_explain_active_screen_english(sample_dataset, db_session):
    ctx = LiveApplicationContext(
        screen=ScreenMetadata(
            route=f"/data-prep/{sample_dataset.id}",
            screen_name="Data Preparation Studio",
        ),
        dataset=DatasetContext(
            dataset_id=sample_dataset.id,
            dataset_name=sample_dataset.name,
            quality_score=68.0,
        ),
    )
    req = ScreenExplanationRequest(
        question="What does the current page show and what should I do next?",
        context=ctx,
        language="en",
    )

    res = explain_active_screen(req, db=db_session)
    assert res.detected_language == "en"
    assert "Data Preparation Studio" in res.screen_summary
    assert len(res.recommended_next_steps) > 0


def test_explain_active_screen_hinglish(sample_dataset, db_session):
    ctx = LiveApplicationContext(
        screen=ScreenMetadata(
            route=f"/data-prep/{sample_dataset.id}",
            screen_name="Data Preparation Studio",
        ),
        dataset=DatasetContext(
            dataset_id=sample_dataset.id,
            dataset_name=sample_dataset.name,
            quality_score=68.0,
        ),
    )
    req = ScreenExplanationRequest(
        question="Is screen pe kya chal raha hai aur next step kya hona chahiye?",
        context=ctx,
        language="auto",
    )

    res = explain_active_screen(req, db=db_session)
    assert res.detected_language == "hinglish"
    assert "screen par hain" in res.screen_summary


def test_visual_analysis_workspace():
    ctx = LiveApplicationContext(
        screen=ScreenMetadata(
            route="/dashboards/1",
            screen_name="Interactive Dashboard Studio",
        ),
        dashboard=DashboardContext(
            dashboard_id=1,
            dashboard_name="Executive Overview",
            selected_widget_id=10,
            selected_chart_type="bar",
            selected_chart_title="Sales by Region",
            active_measures=["revenue"],
        ),
        visual=VisualSnapshotData(
            has_snapshot=True,
            dom_summary="Screen 'Dashboard Studio'. Visual Chart 'Sales by Region' (bar).",
        ),
    )
    req = VisualAnalysisRequest(
        context=ctx,
        query="Analyze what is visible on this screen",
    )

    res = analyze_visual_screen(req)
    assert "Sales by Region" in res.explanation
    assert res.layout_health == "Optimal & Responsive"
    assert "Exact values grounded in verified database analytics" in res.numerical_grounding_note
    assert any("Sales by Region" in el for el in res.visual_elements_detected)


def test_context_freshness_invalidation(sample_dataset, db_session):
    # Check freshness
    freshness = ensure_dataset_freshness(sample_dataset.id, client_version=1, db=db_session)
    assert freshness["is_fresh"] is True
    assert freshness["current_db_version"] == 1

    # Simulate mutation (version bump)
    sample_dataset.version = 2
    db_session.commit()
    record_context_mutation("dataset", sample_dataset.id)

    # Check stale version
    freshness2 = ensure_dataset_freshness(sample_dataset.id, client_version=1, db=db_session)
    assert freshness2["is_fresh"] is False
    assert freshness2["current_db_version"] == 2
