
import pytest

from backend.app.tools.government_sources import data_connector
from backend.app.tools.statistical_engine import statistical_engine


@pytest.mark.asyncio
async def test_singstat_csv_extraction():
    res = await data_connector.fetch_singstat_employment(sector="Information & Communications", start_year=2020, end_year=2024)
    assert res["status"] == "success"
    assert res["format"] == "CSV"
    assert res["total_records"] == 20
    assert res["data"][0]["employment_thousands"] == 118.4
    assert res["data"][-1]["employment_thousands"] == 175.1

@pytest.mark.asyncio
async def test_mom_json_extraction():
    res = await data_connector.fetch_mom_labour_indicators(start_year=2020, end_year=2024)
    assert res["status"] == "success"
    assert res["format"] == "JSON"
    assert res["total_records"] == 20
    assert any(r["quarter"] == "Q1" and r["year"] == 2022 and r["tech_job_vacancies"] == 21300 for r in res["data"])

@pytest.mark.asyncio
async def test_datagovsg_wages_extraction():
    res = await data_connector.fetch_datagovsg_wages()
    assert res["status"] == "success"
    assert res["total_records"] > 0
    records = res["data"]
    # Check 2024 median wage
    w2024 = [r for r in records if r["year"] == 2024 and "industry overall" in r["role_level"].lower()]
    assert len(w2024) > 0
    assert w2024[0]["median_gross_wage_sgd"] == 7350

@pytest.mark.asyncio
async def test_mom_turnover_excel_extraction():
    res = await data_connector.fetch_mom_turnover_excel()
    assert res["status"] == "success"
    assert res["format"] == "Excel (.xlsx)"
    assert res["total_records"] > 0

@pytest.mark.asyncio
async def test_internal_sqlite_db_extraction():
    res = await data_connector.fetch_internal_policy_kpis()
    assert res["status"] == "success"
    assert res["format"] == "SQLite DB"
    assert len(res["initiatives"]) >= 5
    assert len(res["kpis"]) >= 8

def test_cagr_calculation():
    # 100 to 200 in 5 years
    cagr = statistical_engine.calculate_cagr(100.0, 200.0, 5.0)
    assert cagr == 14.87

def test_employment_dynamics_analytics():
    sample_records = [
        {"year": 2020, "quarter": "Q1", "sector": "Information & Communications", "employment_thousands": 118.4, "growth_rate_yoy": 5.2, "local_workforce_pct": 74.8, "productivity_index": 112.4},
        {"year": 2024, "quarter": "Q4", "sector": "Information & Communications", "employment_thousands": 175.1, "growth_rate_yoy": 6.0, "local_workforce_pct": 79.7, "productivity_index": 139.6}
    ]
    res = statistical_engine.analyze_employment_dynamics(sample_records)
    assert res["tech_start_employment"] == 118.4
    assert res["tech_end_employment"] == 175.1
    assert res["net_jobs_added"] == 56700
    assert res["chart"].chart_type == "composed"


def test_cross_indicator_correlation_and_confidence_bands():
    """
    Finding 10: Econometric Indicator Correlation & 95% Confidence Intervals
    Verifies Pearson r, p-value, sample size N, and 95% forecast prediction bands.
    """
    # 1. 95% Confidence bands test
    quarterly_series = [
        {"year": 2020, "quarter": f"Q{q}", "sector": "Information & Communications", "employment_thousands": 118.0 + i * 2.8}
        for i, q in enumerate([1, 2, 3, 4] * 3)
    ]
    res = statistical_engine.analyze_employment_dynamics(quarterly_series)
    assert res["forecast_confidence_band"] is not None
    cb = res["forecast_confidence_band"]
    assert "r_squared" in cb
    assert "p_value" in cb
    assert cb["q4_lower_95"] < cb["q4_forecast"] < cb["q4_upper_95"]

    # 2. Cross-indicator correlation test
    singstat_records = [
        {"year": 2020 + (i // 4), "quarter": f"Q{(i % 4) + 1}", "sector": "Information & Communications", "employment_thousands": 120.0 + i * 2.5}
        for i in range(12)
    ]
    mom_records = [
        {"year": 2020 + (i // 4), "quarter": f"Q{(i % 4) + 1}", "period": f"{2020 + (i // 4)}-Q{(i % 4) + 1}", "tech_job_vacancies": 20000 - i * 500, "tech_retrenchments": 500 + i * 80}
        for i in range(12)
    ]
    corr = statistical_engine.calculate_cross_indicator_correlation(singstat_records, mom_records)
    assert corr["has_correlation"] is True
    assert corr["sample_size"] == 12
    assert "sample_limitation_note" in corr
    vr = corr["vacancies_vs_retrenchments"]
    assert vr["pearson_r"] is not None
    assert vr["p_value"] is not None
    assert "interpretive_summary" in vr
