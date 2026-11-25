"""Forecasting & Scenario Agent for Analyticx AI.
Runs baseline time-series projections, what-if sensitivity analyses, and goal-seek scenarios with explicit assumptions.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from app.agents.base_agent import BaseSpecializedAgent
from app.forecasting.predictor import run_forecast
from app.simulation.what_if import run_what_if


class ForecastingScenarioAgent(BaseSpecializedAgent):
    """
    Runs baseline time-series projections, what-if sensitivity analyses,
    and goal-seek scenarios with explicit assumptions.
    """

    def __init__(self):
        super().__init__(
            name="ForecastingScenarioAgent",
            description="Projects future time-series trends and simulates business what-if scenarios with explicit assumptions.",
        )

    def forecast_trend(
        self,
        df: pd.DataFrame,
        date_column: str,
        target_column: str,
        horizon: int = 6,
        frequency: str = "M",
    ) -> Dict[str, Any]:
        """Runs baseline projection with model evaluation and horizon extrapolation."""
        if date_column not in df.columns:
            return {"error": f"Date column '{date_column}' not found."}
        if target_column not in df.columns:
            return {"error": f"Target metric column '{target_column}' not found."}

        res = run_forecast(
            df=df,
            date_column=date_column,
            target_column=target_column,
            horizon=horizon,
            frequency=frequency,
        )
        return {
            "forecast_result": res,
            "assumptions": [
                f"Historical patterns in {target_column} continue without structural breaks.",
                f"Projection horizon is fixed at {horizon} periods ({frequency}).",
                "Seasonality and trend coefficients are estimated from available history.",
            ],
        }

    def simulate_what_if(
        self,
        df: pd.DataFrame,
        metric_columns: Dict[str, str],
        adjustments: List[Dict[str, Any]],
        elasticity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Runs what-if scenario testing with sensitivity adjustments."""
        res = run_what_if(
            df=df,
            metric_columns=metric_columns,
            adjustments=adjustments,
            elasticity=elasticity,
        )
        return {
            "scenario_result": res,
            "assumptions": [
                f"Metric sensitivity adjusted by: {[a.get('change_pct') for a in adjustments]}%",
                f"Elasticity coefficient: {elasticity if elasticity is not None else 'linear 1.0'}",
                "Operating costs and fixed overhead are assumed invariant unless explicitly adjusted.",
            ],
        }


forecasting_scenario_agent = ForecastingScenarioAgent()
