import json
import logging
import os
import sqlite3
from typing import Any

import httpx
import pandas as pd
from pydantic import BaseModel

from backend.app.config import settings

logger = logging.getLogger("government_sources")

class DataGovSgWageRecord(BaseModel):
    industry: str | None = None
    role_level: str | None = None
    role: str | None = None
    year: int | None = None
    median_gross_wage_sgd: float | None = None
    p25_gross_wage_sgd: float | None = None
    p75_gross_wage_sgd: float | None = None


class GovernmentDataConnector:
    """
    Unified Data Connector for Singapore Government Portals:
    1. DOS SingStat (Department of Statistics Singapore) - CSV
    2. MOM Statistics (Ministry of Manpower) - JSON & Excel (.xlsx)
    3. Data.gov.sg - REST API v2 / JSON
    4. Internal Policy DB (IMDA / GovTech) - SQLite
    """
    def __init__(self):
        self.raw_dir = settings.DATA_RAW_DIR

    async def fetch_singstat_employment(self, sector: str | None = None, start_year: int = 2020, end_year: int = 2024) -> dict[str, Any]:
        """
        Extracts employment time series from DOS SingStat (Table 14.1 / M015661).
        Format: CSV
        """
        csv_path = os.path.join(self.raw_dir, "singstat_tech_employment.csv")
        try:
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"SingStat CSV file not found at {csv_path}")

            df = pd.read_csv(csv_path)

            # Filter by year
            df = df[(df["year"] >= start_year) & (df["year"] <= end_year)]

            # Filter by sector if specified
            if sector:
                df_filtered = df[df["sector"].str.contains(sector, case=False, na=False)]
                if not df_filtered.empty:
                    df = df_filtered

            records = df.to_dict(orient="records")
            return {
                "source": "Department of Statistics Singapore (DOS SingStat)",
                "dataset_id": "M015661-Table-14.1",
                "format": "CSV",
                "status": "success",
                "total_records": len(records),
                "data": records
            }
        except Exception as e:
            logger.error(f"Error fetching SingStat data: {e}")
            return {
                "source": "DOS SingStat",
                "status": "error",
                "error": str(e),
                "data": []
            }

    async def fetch_mom_labour_indicators(self, start_year: int = 2020, end_year: int = 2024) -> dict[str, Any]:
        """
        Extracts quarterly labour market indicators from Ministry of Manpower (MOM).
        Format: JSON
        """
        json_path = os.path.join(self.raw_dir, "mom_labour_market_indicators.json")
        try:
            if not os.path.exists(json_path):
                raise FileNotFoundError(f"MOM JSON file not found at {json_path}")

            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            records = [r for r in payload.get("records", []) if start_year <= r.get("year", 0) <= end_year]
            return {
                "source": "Ministry of Manpower Singapore (MOM)",
                "dataset_id": payload.get("series_id", "MOM-LMR-TECH"),
                "format": "JSON",
                "status": "success",
                "total_records": len(records),
                "description": payload.get("description", ""),
                "data": records
            }
        except Exception as e:
            logger.error(f"Error fetching MOM data: {e}")
            return {
                "source": "MOM Statistics",
                "status": "error",
                "error": str(e),
                "data": []
            }

    async def fetch_mom_turnover_excel(self, sector: str | None = "Information & Communications") -> dict[str, Any]:
        """
        Extracts Job Vacancy & Labour Turnover statistics from Ministry of Manpower.
        Format: Excel (.xlsx)
        """
        excel_path = os.path.join(self.raw_dir, "mom_job_vacancies_and_retrenchment.xlsx")
        try:
            if not os.path.exists(excel_path):
                raise FileNotFoundError(f"MOM Excel file not found at {excel_path}")

            df = pd.read_excel(excel_path, sheet_name=0)
            if sector:
                df = df[df["Sector"].str.contains(sector, case=False, na=False)]

            records = df.to_dict(orient="records")
            return {
                "source": "MOM Labour Turnover & Job Vacancy Survey",
                "dataset_id": "MOM-EXCEL-TURNOVER-2024",
                "format": "Excel (.xlsx)",
                "status": "success",
                "total_records": len(records),
                "data": records
            }
        except Exception as e:
            logger.error(f"Error fetching MOM Excel: {e}")
            return {
                "source": "MOM Excel",
                "status": "error",
                "error": str(e),
                "data": []
            }

    async def fetch_datagovsg_wages(self, industry: str | None = "Information & Communications") -> dict[str, Any]:
        """
        Extracts wage benchmarks. Connects to live Data.gov.sg API v2 with automatic fallback
        to the local verified Data.gov.sg snapshot if offline or rate-limited.
        Validates records through DataGovSgWageRecord Pydantic schema before pipeline ingestion.
        Format: REST API / JSON
        """
        live_api_endpoint = "https://data.gov.sg/api/action/datastore_search"
        resource_id = "d_09b4dbcb30a84d4fb4e5f2cfbb3238bb"

        # Try live API first
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(live_api_endpoint, params={"resource_id": resource_id, "limit": 100})
                if res.status_code == 200:
                    api_json = res.json()
                    raw_records = api_json.get("result", {}).get("records", [])
                    validated_records = []
                    for r in raw_records:
                        try:
                            val_rec = DataGovSgWageRecord(**r).model_dump(exclude_unset=False)
                            validated_records.append(val_rec)
                        except Exception as val_err:
                            logger.warning(f"Skipping malformed Data.gov.sg record: {val_err}")
                    if validated_records:
                        return {
                            "source": "Data.gov.sg API v2 (Live Endpoint)",
                            "dataset_id": resource_id,
                            "format": "REST API (JSON)",
                            "access_method": "Live REST API (Data.gov.sg v2)",
                            "status": "success",
                            "total_records": len(validated_records),
                            "data": validated_records
                        }
        except Exception as api_err:
            logger.warning(f"Live Data.gov.sg API call bypassed/failed ({api_err}). Using verified local snapshot.")

        # Fallback to local Data.gov.sg snapshot
        json_path = os.path.join(self.raw_dir, "datagovsg_wages_by_sector.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_records = data.get("result", {}).get("records", [])
            validated_records = []
            for r in raw_records:
                try:
                    val_rec = DataGovSgWageRecord(**r).model_dump(exclude_unset=False)
                    validated_records.append(val_rec)
                except Exception as val_err:
                    logger.warning(f"Skipping malformed snapshot record: {val_err}")

            if industry:
                validated_records = [
                    r for r in validated_records
                    if (r.get("industry") and industry.lower() in r.get("industry", "").lower())
                    or (r.get("industry") and "national" in r.get("industry", "").lower())
                ]

            return {
                "source": "Data.gov.sg API v2 (Verified Snapshot)",
                "dataset_id": resource_id,
                "format": "JSON API",
                "access_method": "Local Verified Snapshot (Cached Offline Data)",
                "status": "success",
                "total_records": len(validated_records),
                "data": validated_records
            }
        except Exception as e:
            return {
                "source": "Data.gov.sg",
                "status": "error",
                "access_method": "Unavailable",
                "error": str(e),
                "data": []
            }

    async def fetch_internal_policy_kpis(self) -> dict[str, Any]:
        """
        Extracts policy target benchmarks and funding allocations from Internal Policy DB.
        Format: SQLite Database (.db)
        """
        db_path = os.path.join(self.raw_dir, "internal_policy_database.db")
        try:
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Internal Policy SQLite DB not found at {db_path}")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            initiatives = [dict(row) for row in cursor.execute("SELECT * FROM policy_initiatives").fetchall()]
            kpis = [dict(row) for row in cursor.execute("SELECT * FROM policy_kpis").fetchall()]
            conn.close()

            return {
                "source": "Internal Policy Database (IMDA / MDDI)",
                "format": "SQLite DB",
                "status": "success",
                "initiatives": initiatives,
                "kpis": kpis,
                "total_records": len(initiatives) + len(kpis)
            }
        except Exception as e:
            logger.error(f"Error querying Internal Policy DB: {e}")
            return {"source": "Internal DB", "status": "error", "error": str(e), "data": []}

data_connector = GovernmentDataConnector()
