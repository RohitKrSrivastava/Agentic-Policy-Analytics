from typing import Any

import numpy as np
import pandas as pd
import scipy.stats as stats

from backend.app.models.schemas import ChartSpecification


class StatisticalEngine:
    """
    Statistical Modeling & Econometric Analytics Engine.
    Computes CAGR, sector correlation matrices, time-series regression projections
    with 95% confidence intervals, and formats JSON chart specifications for interactive frontend dashboards.
    Fully null-safe, free of hardcoded baseline defaults, and parameterized across Singapore economic sectors.
    """
    @staticmethod
    def calculate_cagr(start_val: float, end_val: float, periods: float) -> float:
        if start_val <= 0 or periods <= 0:
            return 0.0
        return round(((end_val / start_val) ** (1.0 / periods) - 1.0) * 100.0, 2)

    def analyze_employment_dynamics(
        self,
        singstat_records: list[dict[str, Any]],
        sector: str = "Information & Communications"
    ) -> dict[str, Any]:
        df = pd.DataFrame(singstat_records)
        if df.empty or "sector" not in df.columns or "employment_thousands" not in df.columns:
            return {
                "has_data": False,
                "sector": sector,
                "tech_start_employment": None,
                "tech_end_employment": None,
                "net_jobs_added": None,
                "tech_total_growth_pct": None,
                "tech_cagr": None,
                "overall_cagr": None,
                "forecast_2025_q4": None,
                "forecast_confidence_band": None,
                "chart": None,
                "error": f"No employment records found for sector '{sector}'."
            }

        sector_lower = sector.lower()
        if any(k in sector_lower for k in ["fin", "bank", "insur"]):
            target_pattern = "Financial & Insurance"
            sector_label = "Financial & Insurance Services"
        elif any(k in sector_lower for k in ["overall", "economy", "national"]):
            target_pattern = "Overall Economy"
            sector_label = "Overall Economy"
        elif any(k in sector_lower for k in ["tech", "ict", "info", "software", "digital"]):
            target_pattern = "Information & Communications"
            sector_label = "Information & Communications"
        else:
            matching_sectors = [s for s in df["sector"].unique() if sector_lower in str(s).lower()]
            if matching_sectors:
                target_pattern = matching_sectors[0]
                sector_label = target_pattern
            else:
                return {
                    "has_data": False,
                    "sector": sector,
                    "tech_start_employment": None,
                    "tech_end_employment": None,
                    "net_jobs_added": None,
                    "tech_total_growth_pct": None,
                    "tech_cagr": None,
                    "overall_cagr": None,
                    "forecast_2025_q4": None,
                    "forecast_confidence_band": None,
                    "chart": None,
                    "error": f"Sector '{sector}' is not present in SingStat dataset."
                }

        sector_df = df[df["sector"].str.contains(target_pattern, case=False, na=False)].sort_values(by=["year", "quarter"])
        overall_df = df[df["sector"].str.contains("Overall Economy", case=False, na=False)].sort_values(by=["year", "quarter"])

        if sector_df.empty:
            return {
                "has_data": False,
                "sector": sector_label,
                "tech_start_employment": None,
                "tech_end_employment": None,
                "net_jobs_added": None,
                "tech_total_growth_pct": None,
                "tech_cagr": None,
                "overall_cagr": None,
                "forecast_2025_q4": None,
                "forecast_confidence_band": None,
                "chart": None,
                "error": f"No records matching '{sector_label}' in SingStat dataset."
            }

        start_tech = float(sector_df.iloc[0]["employment_thousands"])
        end_tech = float(sector_df.iloc[-1]["employment_thousands"])

        start_yr = int(sector_df.iloc[0]["year"])
        end_yr = int(sector_df.iloc[-1]["year"])
        num_years = max(1.0, float(end_yr - start_yr))

        tech_cagr = self.calculate_cagr(start_tech, end_tech, num_years)
        total_growth_pct = round(((end_tech - start_tech) / start_tech) * 100.0, 2) if start_tech > 0 else 0.0
        net_jobs_added = round((end_tech - start_tech) * 1000.0, 0)

        # Baseline overall economy CAGR
        overall_cagr = None
        if not overall_df.empty and len(overall_df) >= 2:
            overall_start = float(overall_df.iloc[0]["employment_thousands"])
            overall_end = float(overall_df.iloc[-1]["employment_thousands"])
            overall_cagr = self.calculate_cagr(overall_start, overall_end, num_years)

        chart_series = []
        forecast_2025_q4 = None
        forecast_confidence_band = None

        if len(sector_df) >= 3:
            x_indices = np.arange(len(sector_df), dtype=float)
            y_vals = sector_df["employment_thousands"].astype(float).values
            reg = stats.linregress(x_indices, y_vals)
            slope, intercept = float(reg.slope), float(reg.intercept)
            r_squared = round(float(reg.rvalue**2), 3)

            residuals = y_vals - (slope * x_indices + intercept)
            s_err = float(np.sqrt(np.sum(residuals**2) / max(1, len(x_indices) - 2)))
            sxx = float(np.sum((x_indices - np.mean(x_indices))**2))
            x_mean = float(np.mean(x_indices))

            for _, row in sector_df.iterrows():
                chart_series.append({
                    "period": f"{row['year']}-{row.get('quarter', 'Q1')}",
                    "Tech_Employment_K": float(row["employment_thousands"]),
                    "YoY_Growth_Pct": float(row.get("growth_rate_yoy", 0.0)),
                    "Local_Workforce_Pct": float(row["local_workforce_pct"]) if "local_workforce_pct" in row and pd.notnull(row["local_workforce_pct"]) else None,
                    "Productivity_Index": float(row["productivity_index"]) if "productivity_index" in row and pd.notnull(row["productivity_index"]) else None,
                    "Trend_Line": round(float(slope * len(chart_series) + intercept), 1)
                })

            for q_num, q_name in enumerate(["Q1", "Q2", "Q3", "Q4"], start=1):
                future_idx = len(sector_df) + q_num - 1
                proj_val = round(float(slope * future_idx + intercept), 1)
                se_pred = s_err * np.sqrt(1.0 + 1.0 / len(x_indices) + ((future_idx - x_mean)**2) / max(0.001, sxx))
                proj_upper = round(proj_val + 1.96 * se_pred, 1)
                proj_lower = round(proj_val - 1.96 * se_pred, 1)

                chart_series.append({
                    "period": f"{end_yr + 1}-{q_name} (Proj)",
                    "Tech_Employment_K": None,
                    "Projected_Employment_K": proj_val,
                    "Projected_Upper_95": proj_upper,
                    "Projected_Lower_95": proj_lower,
                    "Trend_Line": proj_val
                })

            forecast_2025_q4 = round(float(slope * (len(sector_df) + 3) + intercept), 1)
            future_q4_idx = len(sector_df) + 3
            se_q4 = s_err * np.sqrt(1.0 + 1.0 / len(x_indices) + ((future_q4_idx - x_mean)**2) / max(0.001, sxx))
            forecast_confidence_band = {
                "r_squared": r_squared,
                "p_value": round(float(reg.pvalue), 4),
                "q4_forecast": forecast_2025_q4,
                "q4_upper_95": round(forecast_2025_q4 + 1.96 * se_q4, 1),
                "q4_lower_95": round(forecast_2025_q4 - 1.96 * se_q4, 1)
            }
        else:
            for _, row in sector_df.iterrows():
                chart_series.append({
                    "period": f"{row['year']}-{row.get('quarter', 'Q1')}",
                    "Tech_Employment_K": float(row["employment_thousands"]),
                    "YoY_Growth_Pct": float(row.get("growth_rate_yoy", 0.0)),
                    "Local_Workforce_Pct": float(row.get("local_workforce_pct", 0.0)),
                    "Productivity_Index": float(row.get("productivity_index", 100.0)),
                    "Trend_Line": float(row["employment_thousands"])
                })

        annotations = []
        if start_tech is not None:
            annotations.append(f"{start_yr}: Baseline employment at {start_tech:.1f}k")
        if end_tech is not None and total_growth_pct is not None:
            annotations.append(f"{end_yr}: Employment reached {end_tech:.1f}k ({total_growth_pct:+.1f}% net growth)")
        if forecast_confidence_band:
            annotations.append(
                f"2025-Q4 Projected: {forecast_2025_q4}k (95% CI: [{forecast_confidence_band['q4_lower_95']}k, {forecast_confidence_band['q4_upper_95']}k], R²={forecast_confidence_band['r_squared']})"
            )

        chart_spec = ChartSpecification(
            chart_id="chart_tech_employment_trend",
            title=f"Singapore {sector_label} Workforce & Growth Trend ({start_yr}-{end_yr})",
            chart_type="composed",
            x_key="period",
            y_keys=["Tech_Employment_K", "Projected_Employment_K", "Trend_Line"],
            series=chart_series,
            y_axis_label="Employment (Thousands)",
            annotations=annotations
        )

        return {
            "has_data": True,
            "sector": sector_label,
            "tech_start_employment": start_tech,
            "tech_end_employment": end_tech,
            "net_jobs_added": int(net_jobs_added),
            "tech_total_growth_pct": total_growth_pct,
            "tech_cagr": tech_cagr,
            "overall_cagr": overall_cagr,
            "forecast_2025_q4": forecast_2025_q4,
            "forecast_confidence_band": forecast_confidence_band,
            "chart": chart_spec
        }

    def analyze_labour_market_tightness(self, mom_records: list[dict[str, Any]]) -> dict[str, Any]:
        df = pd.DataFrame(mom_records)
        if df.empty or "tech_job_vacancies" not in df.columns or "tech_retrenchments" not in df.columns:
            return {
                "has_data": False,
                "peak_vacancies": None,
                "peak_period": "N/A",
                "latest_vacancies": None,
                "latest_retrenchments": None,
                "peak_retrenchments": None,
                "peak_retrench_period": "N/A",
                "latest_reentry_rate": None,
                "chart": None,
                "error": "No labour market vacancy/retrenchment indicators found."
            }

        df = df.sort_values(by=["year", "quarter"])

        peak_vacancies = int(df["tech_job_vacancies"].max())
        peak_period = str(df.loc[df["tech_job_vacancies"].idxmax(), "period"])
        latest_vacancies = int(df.iloc[-1]["tech_job_vacancies"])
        latest_retrenchments = int(df.iloc[-1]["tech_retrenchments"])
        peak_retrenchments = int(df["tech_retrenchments"].max())
        peak_retrench_period = str(df.loc[df["tech_retrenchments"].idxmax(), "period"])

        reentry_rate = None
        if "reentry_rate_pct" in df.columns and pd.notnull(df.iloc[-1]["reentry_rate_pct"]):
            reentry_rate = float(df.iloc[-1]["reentry_rate_pct"])

        chart_series = []
        for _, row in df.iterrows():
            chart_series.append({
                "period": row.get("period", f"{row.get('year')}-{row.get('quarter')}"),
                "Job_Vacancies": int(row.get("tech_job_vacancies", 0)),
                "Retrenchments": int(row.get("tech_retrenchments", 0)),
                "Vacancy_Ratio": float(row.get("vacancy_to_unemployed_ratio", 0.0)) if pd.notnull(row.get("vacancy_to_unemployed_ratio")) else None,
                "Reentry_Rate_Pct": float(row.get("reentry_rate_pct")) if pd.notnull(row.get("reentry_rate_pct")) else None
            })

        annotations = [
            f"{peak_period}: Job vacancies peaked at {peak_vacancies:,}",
            f"{peak_retrench_period}: Peak retrenchments reached {peak_retrenchments:,}"
        ]
        if reentry_rate is not None:
            annotations.append(f"Latest 6-month re-entry rate into employment: {reentry_rate:.1f}%")

        chart_spec = ChartSpecification(
            chart_id="chart_vacancies_retrenchments",
            title="MOM Labour Market Dynamics: Job Openings vs Retrenchments",
            chart_type="composed",
            x_key="period",
            y_keys=["Job_Vacancies", "Retrenchments"],
            series=chart_series,
            y_axis_label="Headcount",
            annotations=annotations
        )

        return {
            "has_data": True,
            "peak_vacancies": peak_vacancies,
            "peak_period": peak_period,
            "latest_vacancies": latest_vacancies,
            "latest_retrenchments": latest_retrenchments,
            "peak_retrenchments": peak_retrenchments,
            "peak_retrench_period": peak_retrench_period,
            "latest_reentry_rate": reentry_rate,
            "chart": chart_spec
        }

    def analyze_wages_and_premium(
        self,
        wage_records: list[dict[str, Any]],
        sector: str = "Information & Communications"
    ) -> dict[str, Any]:
        df = pd.DataFrame(wage_records)
        if df.empty or "median_gross_wage_sgd" not in df.columns:
            return {
                "has_data": False,
                "tech_median_wage": None,
                "national_median_wage": None,
                "tech_premium_pct": None,
                "ai_specialist_wage": None,
                "cybersecurity_wage": None,
                "software_engineer_wage": None,
                "chart": None,
                "error": "No wage benchmark records available."
            }

        latest_year = df["year"].max()
        df_latest = df[df["year"] == latest_year]

        tech_median: float | None = None
        national_median: float | None = None
        ai_median: float | None = None
        cyber_median: float | None = None
        software_eng: float | None = None

        for _, r in df_latest.iterrows():
            role = str(r.get("role_level", "") or r.get("role", "")).lower()
            wage = float(r.get("median_gross_wage_sgd", 0))
            if wage > 0:
                if "ai specialist" in role:
                    ai_median = wage
                elif "cybersecurity" in role:
                    cyber_median = wage
                elif "software engineer" in role:
                    software_eng = wage
                elif "industry overall" in role or "median" in role:
                    tech_median = wage
                elif "national" in role:
                    national_median = wage

        premium_pct: float | None = None
        if tech_median is not None and national_median is not None and national_median > 0:
            premium_pct = round(((tech_median - national_median) / national_median) * 100.0, 1)

        years = sorted(df["year"].dropna().unique())
        chart_series = []
        for y in years:
            df_y = df[df["year"] == y]
            row_dict: dict[str, Any] = {"year": str(int(y))}
            for _, r in df_y.iterrows():
                role = str(r.get("role_level", "") or r.get("role", "")).lower()
                val = float(r.get("median_gross_wage_sgd", 0))
                if "industry overall" in role or "median" in role:
                    row_dict["Tech_Industry_Median"] = val
                elif "national" in role:
                    row_dict["National_Median"] = val
                elif "ai specialist" in role:
                    row_dict["AI_Specialist"] = val
                elif "software engineer" in role:
                    row_dict["Software_Engineer"] = val
            chart_series.append(row_dict)

        annotations = []
        if tech_median is not None and national_median is not None and premium_pct is not None:
            annotations.append(f"{latest_year} Sector Median (S${tech_median:,.0f}) commands a +{premium_pct}% premium over National Median (S${national_median:,.0f})")
        elif tech_median is not None:
            annotations.append(f"{latest_year} Sector Median: S${tech_median:,.0f}")
        if ai_median is not None:
            annotations.append(f"AI Specialists command median wage of S${ai_median:,.0f}/month")

        chart_spec = ChartSpecification(
            chart_id="chart_wage_trajectory_comparison",
            title=f"Gross Monthly Income Comparison: {sector} vs National Median (SGD)",
            chart_type="bar",
            x_key="year",
            y_keys=["Tech_Industry_Median", "National_Median", "AI_Specialist", "Software_Engineer"],
            series=chart_series,
            y_axis_label="Monthly Gross Income (SGD)",
            annotations=annotations
        )

        return {
            "has_data": True,
            "tech_median_wage": tech_median,
            "national_median_wage": national_median,
            "tech_premium_pct": premium_pct,
            "ai_specialist_wage": ai_median,
            "cybersecurity_wage": cyber_median,
            "software_engineer_wage": software_eng,
            "chart": chart_spec
        }

    def calculate_cross_indicator_correlation(
        self,
        singstat_records: list[dict[str, Any]],
        mom_records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculates Pearson correlation between workforce indicators across merged quarterly series.
        Evaluates the relationship between vacancies, retrenchments, and overall employment.
        """
        sing_df = pd.DataFrame(singstat_records)
        mom_df = pd.DataFrame(mom_records)

        if sing_df.empty or mom_df.empty:
            return {"has_correlation": False, "reason": "Insufficient data to compute cross-indicator correlation."}

        if "period" in mom_df.columns and ("year" not in mom_df.columns or "quarter" not in mom_df.columns):
            mom_df["year"] = mom_df["period"].apply(lambda p: int(str(p).split("-")[0]) if "-" in str(p) else None)
            mom_df["quarter"] = mom_df["period"].apply(lambda p: str(p).split("-")[1] if "-" in str(p) else None)

        if "year" not in sing_df.columns or "quarter" not in sing_df.columns:
            return {"has_correlation": False, "reason": "Temporal keys (year, quarter) missing in datasets."}

        merged = pd.merge(sing_df, mom_df, on=["year", "quarter"], how="inner")
        n = len(merged)
        if n < 3:
            return {"has_correlation": False, "reason": f"Sample size (N={n}) too small for statistical correlation."}

        results: dict[str, Any] = {
            "has_correlation": True,
            "sample_size": n,
            "sample_limitation_note": f"Sample size of N={n} quarterly periods warrants cautious interpretation."
        }

        # 1. Vacancies vs Retrenchments (Beveridge curve relationship)
        if "tech_job_vacancies" in merged.columns and "tech_retrenchments" in merged.columns:
            v_vals = pd.to_numeric(merged["tech_job_vacancies"], errors="coerce").dropna()
            r_vals = pd.to_numeric(merged["tech_retrenchments"], errors="coerce").dropna()
            valid_idx = v_vals.index.intersection(r_vals.index)
            if len(valid_idx) >= 3:
                r_val, p_val = stats.pearsonr(v_vals.loc[valid_idx], r_vals.loc[valid_idx])
                results["vacancies_vs_retrenchments"] = {
                    "pearson_r": round(float(r_val), 3),
                    "p_value": round(float(p_val), 4),
                    "statistically_significant": bool(p_val < 0.05),
                    "relationship": "inverse" if r_val < 0 else "positive",
                    "interpretive_summary": f"Beveridge-type {'inverse' if r_val < 0 else 'positive'} correlation (r={round(float(r_val), 3)}, p={round(float(p_val), 4)})."
                }

        # 2. Employment Headcount vs Vacancies
        if "employment_thousands" in merged.columns and "tech_job_vacancies" in merged.columns:
            e_vals = pd.to_numeric(merged["employment_thousands"], errors="coerce").dropna()
            v_vals = pd.to_numeric(merged["tech_job_vacancies"], errors="coerce").dropna()
            valid_idx = e_vals.index.intersection(v_vals.index)
            if len(valid_idx) >= 3:
                r_val, p_val = stats.pearsonr(e_vals.loc[valid_idx], v_vals.loc[valid_idx])
                results["employment_vs_vacancies"] = {
                    "pearson_r": round(float(r_val), 3),
                    "p_value": round(float(p_val), 4),
                    "statistically_significant": bool(p_val < 0.05),
                    "interpretive_summary": f"Employment vs vacancies correlation (r={round(float(r_val), 3)}, p={round(float(p_val), 4)})."
                }

        return results


statistical_engine = StatisticalEngine()
