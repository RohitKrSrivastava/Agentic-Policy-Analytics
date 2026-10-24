from fastapi import APIRouter
from backend.app.tools.government_sources import data_connector

router = APIRouter()

@router.get("")
async def list_government_datasets():
    """
    Returns metadata for all 4 integrated Singapore Government data sources.
    """
    return [
        {
            "id": "singstat_tech_employment",
            "name": "DOS SingStat Infocomm Employment & Growth (Table 14.1)",
            "agency": "Department of Statistics Singapore",
            "format": "CSV",
            "update_cadence": "Quarterly",
            "time_range": "2020 - 2024",
            "key_attributes": ["employment_thousands", "growth_rate_yoy", "local_workforce_pct", "productivity_index"]
        },
        {
            "id": "mom_labour_market",
            "name": "MOM Labour Market Report: Vacancies, Retrenchments & Re-entry Rates",
            "agency": "Ministry of Manpower Singapore",
            "format": "JSON",
            "update_cadence": "Quarterly",
            "time_range": "2020 - 2024",
            "key_attributes": ["tech_job_vacancies", "tech_retrenchments", "vacancy_to_unemployed_ratio", "reentry_rate_pct"]
        },
        {
            "id": "datagovsg_wages",
            "name": "Data.gov.sg Gross Monthly Income from Work by Industry & Role",
            "agency": "GovTech / Data.gov.sg",
            "format": "REST API (JSON)",
            "update_cadence": "Annual",
            "time_range": "2020 - 2024",
            "key_attributes": ["median_gross_wage_sgd", "p25_gross_wage_sgd", "p75_gross_wage_sgd", "industry", "role_level"]
        },
        {
            "id": "mom_turnover_excel",
            "name": "MOM Labour Turnover & Resignation Survey",
            "agency": "Ministry of Manpower Singapore",
            "format": "Excel (.xlsx)",
            "update_cadence": "Quarterly",
            "time_range": "2020 - 2024",
            "key_attributes": ["Recruitment_Rate_Pct", "Resignation_Rate_Pct", "Net_Turnover_Rate"]
        },
        {
            "id": "internal_policy_db",
            "name": "Internal Policy Initiatives & TeSA KPI Benchmarks",
            "agency": "IMDA / MDDI Singapore",
            "format": "SQLite Database",
            "update_cadence": "Annual",
            "time_range": "2016 - 2024",
            "key_attributes": ["initiative_name", "lead_agency", "budget_allocated_millions", "target_pmet_upskilled"]
        }
    ]

@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str):
    """
    Returns a sample data preview for interactive inspection.
    """
    if dataset_id == "singstat_tech_employment":
        res = await data_connector.fetch_singstat_employment(start_year=2023, end_year=2024)
        return res
    elif dataset_id == "mom_labour_market":
        res = await data_connector.fetch_mom_labour_indicators(start_year=2023, end_year=2024)
        return res
    elif dataset_id == "datagovsg_wages":
        res = await data_connector.fetch_datagovsg_wages()
        return res
    elif dataset_id == "mom_turnover_excel":
        res = await data_connector.fetch_mom_turnover_excel()
        return res
    elif dataset_id == "internal_policy_db":
        res = await data_connector.fetch_internal_policy_kpis()
        return res
    else:
        return {"error": f"Unknown dataset '{dataset_id}'"}
