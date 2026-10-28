import math
import re
from typing import Any


class HallucinationVerificationGuard:
    """
    Automated Ground-Truth Factuality Verifier & Hallucination Detector.
    Scans LLM-generated reports for quantitative claims (percentages, headcounts, dollar values)
    and validates them against authoritative underlying source data using SEMANTIC METRIC BINDING.

    Enforces domain binding:
    - Wage claims (S$, salary, income) only match wage benchmarks.
    - Retrenchment claims only match retrenchment records.
    - CAGR claims only match compound annual growth rates, never total net growth.
    - Strict tolerances (e.g. $2 for wages, 0.05% for CAGR) prevent close-value mutations.
    """

    NUMERIC_PATTERN = re.compile(
        r'(?<![A-Za-z0-9_])(?:S?\$)?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?(?:\s*[kKmMbB])?(?![A-Za-z0-9_])'
    )

    @classmethod
    def extract_claims_with_context(cls, text: str) -> list[dict[str, Any]]:
        results = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue
            for match in cls.NUMERIC_PATTERN.finditer(sentence_clean):
                token = match.group(0).strip()
                if len(token) < 2 and not token.isdigit():
                    continue
                results.append({
                    "token": token,
                    "context": sentence_clean,
                    "start": match.start(),
                    "end": match.end()
                })
        return results

    @classmethod
    def classify_claim_semantic_type(cls, token: str, context: str, start: int = -1, end: int = -1) -> str:
        # Extract immediate surrounding words to prevent cross-clause context pollution
        if start >= 0 and end >= 0:
            window_start = max(0, start - 35)
            window_end = min(len(context), end + 35)
            local_ctx = context[window_start:window_end].lower()
        else:
            local_ctx = context.lower()

        t_clean = token.lower()

        # 1. Currency or Wage
        if token.startswith("S$") or token.startswith("$") or any(w in local_ctx for w in ["wage", "salary", "income", "gross monthly", "remuneration", "pay", "earn"]):
            return "WAGE"

        # 2. Headcount / Jobs (Numbers ending in k, m, or associated with employment words)
        if t_clean.endswith("k") or t_clean.endswith("m") or any(w in local_ctx for w in ["workers", "jobs", "employment", "headcount", "resident workforce", "positions", "net jobs"]):
            if "%" not in token:
                return "HEADCOUNT"

        # 3. Retrenchments
        if any(w in local_ctx for w in ["retrench", "redundanc", "layoff", "laid off"]):
            return "RETRENCHMENT"

        # 4. Ratio (ratios in economics are small decimal values e.g. 1.75, 2.42)
        cand_floats = cls.parse_numeric_value(token)
        if cand_floats and cand_floats[0] <= 15.0 and any(w in local_ctx for w in ["ratio", "unemployed"]):
            return "RATIO"

        # 5. Vacancies
        if any(w in local_ctx for w in ["vacanc", "job opening", "openings"]):
            return "VACANCY"

        # 6. Percentage-based metrics
        if "%" in token:
            if "cagr" in local_ctx or "compound annual" in local_ctx:
                return "CAGR"
            if any(w in local_ctx for w in ["re-entry", "reentry"]):
                return "REENTRY_RATE"
            return "PERCENTAGE"

        return "GENERAL"

    @staticmethod
    def parse_numeric_value(token: str) -> list[float] | None:
        cleaned = token.replace("S$", "").replace("$", "").replace("%", "").replace(",", "").strip()
        multiplier = 1.0
        has_suffix = False

        if cleaned.lower().endswith("k"):
            multiplier = 1_000.0
            cleaned = cleaned[:-1].strip()
            has_suffix = True
        elif cleaned.lower().endswith("m"):
            multiplier = 1_000_000.0
            cleaned = cleaned[:-1].strip()
            has_suffix = True
        elif cleaned.lower().endswith("b"):
            multiplier = 1_000_000_000.0
            cleaned = cleaned[:-1].strip()
            has_suffix = True

        try:
            val = float(cleaned)
        except ValueError:
            return None

        candidates = [val * multiplier]
        if has_suffix:
            candidates.append(val)
        if val >= 1000 and multiplier == 1.0:
            candidates.append(round(val / 1000.0, 2))
        if "%" in token:
            candidates.append(round(val / 100.0, 4))

        return candidates

    @staticmethod
    def is_benign_structural_token(token: str, val: float) -> bool:
        clean = token.replace("$", "").replace("%", "").strip()
        # Years
        if 1990 <= val <= 2035 and "." not in clean and "%" not in token and "$" not in token:
            return True
        # Version numbers or table numbers
        if clean in ["1.0", "2.0", "3.0", "14.1", "2.5", "0.2"]:
            return True
        # Plain single digits with no prefix/suffix
        if val in [1.0, 2.0, 3.0, 4.0, 5.0] and token in ["1", "2", "3", "4", "5"]:
            return True
        return False

    @staticmethod
    def extract_claim_sector(context: str, token_pos: int | None = None) -> str | None:
        c_lower = context.lower()
        mentions: list[tuple[int, str]] = []
        for m in re.finditer(r'\b(financial|banking|finance|insurance)\b', c_lower):
            mentions.append((m.start(), "Financial & Insurance Services"))
        for m in re.finditer(r'\b(tech|ict|information|software|infocomm)\b', c_lower):
            mentions.append((m.start(), "Information & Communications"))
        for m in re.finditer(r'\b(overall|economy-wide)\b', c_lower):
            mentions.append((m.start(), "Overall Economy"))

        if not mentions:
            return None

        if token_pos is not None:
            # Pick the sector mention closest to the candidate token in the sentence
            mentions.sort(key=lambda item: abs(item[0] - token_pos))
            return mentions[0][1]

        return mentions[0][1]

    def build_ground_truth_index(self, ground_truth: dict[str, Any], rag_chunks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        index: list[dict[str, Any]] = []

        def normalize_sector(raw: str | None) -> str | None:
            if not raw:
                return None
            r_lower = raw.lower()
            if any(k in r_lower for k in ["fin", "bank", "insur"]):
                return "Financial & Insurance Services"
            if any(k in r_lower for k in ["tech", "ict", "information", "software", "infocomm"]):
                return "Information & Communications"
            if any(k in r_lower for k in ["overall", "economy", "national"]):
                return "Overall Economy"
            return raw

        def add_entry(val: float, category: str, source: str, desc: str, tol: float = 0.1, sector: str | None = None):
            if val is not None and not math.isnan(val):
                index.append({
                    "value": float(val),
                    "category": category,
                    "source": source,
                    "description": desc,
                    "tolerance": tol,
                    "sector": sector
                })

        # 1. Computed Metrics
        metrics = ground_truth.get("metrics", {})
        if isinstance(metrics, dict):
            primary_sec = normalize_sector(metrics.get("sector", "Information & Communications"))

            # Multi-sector specific metrics
            sector_metrics = metrics.get("sector_metrics", {})
            if isinstance(sector_metrics, dict):
                for sec_name, s_m in sector_metrics.items():
                    s_norm = normalize_sector(sec_name)
                    if isinstance(s_m, dict):
                        if s_m.get("tech_cagr") is not None:
                            add_entry(s_m["tech_cagr"], "CAGR", "computed_metrics", f"{sec_name} CAGR: {s_m['tech_cagr']}%", tol=0.05, sector=s_norm)
                        if s_m.get("net_jobs_added") is not None:
                            add_entry(s_m["net_jobs_added"], "HEADCOUNT", "computed_metrics", f"{sec_name} net jobs: {s_m['net_jobs_added']}", tol=1.0, sector=s_norm)
                            add_entry(round(s_m["net_jobs_added"] / 1000.0, 1), "HEADCOUNT", "computed_metrics", f"{sec_name} net jobs (k): {s_m['net_jobs_added']/1000.0:.1f}k", tol=0.1, sector=s_norm)
                        if s_m.get("tech_start_employment") is not None:
                            add_entry(s_m["tech_start_employment"], "HEADCOUNT", "computed_metrics", f"{sec_name} start emp: {s_m['tech_start_employment']}k", tol=0.1, sector=s_norm)
                        if s_m.get("tech_end_employment") is not None:
                            add_entry(s_m["tech_end_employment"], "HEADCOUNT", "computed_metrics", f"{sec_name} end emp: {s_m['tech_end_employment']}k", tol=0.1, sector=s_norm)

            if metrics.get("tech_cagr") is not None:
                add_entry(metrics["tech_cagr"], "CAGR", "computed_metrics", f"Tech CAGR: {metrics['tech_cagr']}%", tol=0.05, sector=primary_sec)
            if metrics.get("overall_cagr") is not None:
                add_entry(metrics["overall_cagr"], "CAGR", "computed_metrics", f"Overall CAGR: {metrics['overall_cagr']}%", tol=0.05, sector="Overall Economy")
            if metrics.get("tech_total_growth_pct") is not None:
                add_entry(metrics["tech_total_growth_pct"], "PERCENTAGE", "computed_metrics", f"Tech total growth: {metrics['tech_total_growth_pct']}%", tol=0.1, sector=primary_sec)
            if metrics.get("net_jobs_added") is not None:
                add_entry(metrics["net_jobs_added"], "HEADCOUNT", "computed_metrics", f"Net jobs added: {metrics['net_jobs_added']}", tol=1.0, sector=primary_sec)
                add_entry(round(metrics["net_jobs_added"] / 1000.0, 1), "HEADCOUNT", "computed_metrics", f"Net jobs added (k): {metrics['net_jobs_added']/1000.0:.1f}k", tol=0.1, sector=primary_sec)
            if metrics.get("tech_median_wage") is not None:
                add_entry(metrics["tech_median_wage"], "WAGE", "computed_metrics", f"Tech median wage: S${metrics['tech_median_wage']}", tol=2.0, sector=primary_sec)
            if metrics.get("national_median_wage") is not None:
                add_entry(metrics["national_median_wage"], "WAGE", "computed_metrics", f"National median wage: S${metrics['national_median_wage']}", tol=2.0, sector="Overall Economy")
            if metrics.get("tech_premium_pct") is not None:
                add_entry(metrics["tech_premium_pct"], "PERCENTAGE", "computed_metrics", f"Tech wage premium: {metrics['tech_premium_pct']}%", tol=0.1, sector=primary_sec)
            if metrics.get("peak_vacancies") is not None:
                add_entry(metrics["peak_vacancies"], "VACANCY", "computed_metrics", f"Peak vacancies: {metrics['peak_vacancies']}", tol=1.0, sector=None)
                add_entry(round(metrics["peak_vacancies"] / 1000.0, 1), "VACANCY", "computed_metrics", f"Peak vacancies (k): {metrics['peak_vacancies']/1000.0:.1f}k", tol=0.1, sector=None)
            if metrics.get("latest_vacancies") is not None:
                add_entry(metrics["latest_vacancies"], "VACANCY", "computed_metrics", f"Latest vacancies: {metrics['latest_vacancies']}", tol=1.0, sector=None)
                add_entry(round(metrics["latest_vacancies"] / 1000.0, 1), "VACANCY", "computed_metrics", f"Latest vacancies (k): {metrics['latest_vacancies']/1000.0:.1f}k", tol=0.1, sector=None)
            if metrics.get("peak_retrenchments") is not None:
                add_entry(metrics["peak_retrenchments"], "RETRENCHMENT", "computed_metrics", f"Peak retrenchments: {metrics['peak_retrenchments']}", tol=1.0, sector=None)
            if metrics.get("latest_retrenchments") is not None:
                add_entry(metrics["latest_retrenchments"], "RETRENCHMENT", "computed_metrics", f"Latest retrenchments: {metrics['latest_retrenchments']}", tol=1.0, sector=None)
            if metrics.get("latest_reentry_rate") is not None:
                add_entry(metrics["latest_reentry_rate"], "REENTRY_RATE", "computed_metrics", f"Reentry rate: {metrics['latest_reentry_rate']}%", tol=0.1, sector=None)
            if metrics.get("vacancy_to_unemployed_ratio") is not None:
                add_entry(metrics["vacancy_to_unemployed_ratio"], "RATIO", "computed_metrics", f"Vacancy to unemployed ratio: {metrics['vacancy_to_unemployed_ratio']}", tol=0.05, sector="Overall Economy")

            for k, v in metrics.items():
                if isinstance(v, (int, float)) and not math.isnan(v):
                    add_entry(float(v), "GENERAL", "computed_metrics", f"Metric {k}: {v}", tol=0.25, sector=None)

        # 2. Raw / Cleaned Datasets
        datasets = ground_truth.get("datasets", {})
        if isinstance(datasets, dict):
            for row in datasets.get("singstat", []):
                if isinstance(row, dict):
                    row_sec = normalize_sector(row.get("sector", "Information & Communications"))
                    period = f"{row.get('year', '')}-{row.get('quarter', '')}"
                    if "employment_thousands" in row and isinstance(row["employment_thousands"], (int, float)):
                        emp_k = float(row["employment_thousands"])
                        add_entry(emp_k, "HEADCOUNT", "singstat_tech_employment.csv", f"SingStat {row_sec} {period} employment (k): {emp_k}k", tol=0.1, sector=row_sec)
                        add_entry(emp_k * 1000.0, "HEADCOUNT", "singstat_tech_employment.csv", f"SingStat {row_sec} {period} total headcount: {int(emp_k*1000):,}", tol=1.0, sector=row_sec)
                    if "growth_rate_yoy" in row and isinstance(row["growth_rate_yoy"], (int, float)):
                        add_entry(float(row["growth_rate_yoy"]), "PERCENTAGE", "singstat_tech_employment.csv", f"SingStat {row_sec} {period} YoY: {row['growth_rate_yoy']}%", tol=0.1, sector=row_sec)
                    if "local_workforce_pct" in row and isinstance(row["local_workforce_pct"], (int, float)):
                        add_entry(float(row["local_workforce_pct"]), "PERCENTAGE", "singstat_tech_employment.csv", f"SingStat {row_sec} {period} local share: {row['local_workforce_pct']}%", tol=0.1, sector=row_sec)
                    if "productivity_index" in row and isinstance(row["productivity_index"], (int, float)):
                        add_entry(float(row["productivity_index"]), "GENERAL", "singstat_tech_employment.csv", f"SingStat {row_sec} {period} productivity: {row['productivity_index']}", tol=0.1, sector=row_sec)

            for row in datasets.get("mom", []):
                if isinstance(row, dict):
                    period = f"{row.get('year', '')}-{row.get('quarter', '')}"
                    if "tech_job_vacancies" in row and isinstance(row["tech_job_vacancies"], (int, float)):
                        add_entry(float(row["tech_job_vacancies"]), "VACANCY", "mom_labour_market_indicators.json", f"MOM {period} vacancies: {row['tech_job_vacancies']}", tol=1.0, sector=None)
                        add_entry(round(float(row["tech_job_vacancies"]) / 1000.0, 1), "VACANCY", "mom_labour_market_indicators.json", f"MOM {period} vacancies (k): {float(row['tech_job_vacancies'])/1000.0:.1f}k", tol=0.1, sector=None)
                    if "tech_retrenchments" in row and isinstance(row["tech_retrenchments"], (int, float)):
                        add_entry(float(row["tech_retrenchments"]), "RETRENCHMENT", "mom_labour_market_indicators.json", f"MOM {period} retrenchments: {row['tech_retrenchments']}", tol=1.0, sector=None)
                    if "vacancy_to_unemployed_ratio" in row and isinstance(row["vacancy_to_unemployed_ratio"], (int, float)):
                        add_entry(float(row["vacancy_to_unemployed_ratio"]), "RATIO", "mom_labour_market_indicators.json", f"MOM {period} ratio: {row['vacancy_to_unemployed_ratio']}", tol=0.05, sector="Overall Economy")
                    if "reentry_rate_pct" in row and isinstance(row["reentry_rate_pct"], (int, float)):
                        add_entry(float(row["reentry_rate_pct"]), "REENTRY_RATE", "mom_labour_market_indicators.json", f"MOM {period} re-entry: {row['reentry_rate_pct']}%", tol=0.1, sector=None)

            for row in datasets.get("wages", []):
                if isinstance(row, dict):
                    ind = row.get("industry") or row.get("role", "National")
                    row_sec = normalize_sector(ind)
                    for col in ["median_gross_wage_sgd", "p25_gross_wage_sgd", "p75_gross_wage_sgd"]:
                        if col in row and isinstance(row[col], (int, float)):
                            add_entry(float(row[col]), "WAGE", "datagovsg_wages_by_sector.json", f"Data.gov.sg {ind} {col}: S${row[col]}", tol=2.0, sector=row_sec)

            all_rag = (rag_chunks or []) + datasets.get("rag_chunks", []) + ground_truth.get("rag_chunks", [])
            for chunk in all_rag:
                if isinstance(chunk, dict):
                    doc_title = chunk.get("doc_title") or chunk.get("title") or chunk.get("doc_id", "Policy Whitepaper")
                    content = chunk.get("content", "")
                    for raw_tok in re.findall(r'(\$?\d[\d,]*(?:\.\d+)?%?(?:\s*[kKmMbB])?)', content):
                        for clean_num in self.parse_numeric_value(raw_tok):
                            if not self.is_benign_structural_token(raw_tok, clean_num):
                                add_entry(clean_num, "RAG_POLICY_FACT", doc_title, f"Policy Whitepaper ({doc_title}): {raw_tok}", tol=0.25)

        return index

    def verify_report(self, report_dict: dict[str, Any], ground_truth: dict[str, Any] | None = None, rag_chunks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        ground_truth = ground_truth or {}
        gt_index = self.build_ground_truth_index(ground_truth, rag_chunks=rag_chunks)

        if not gt_index:
            return {
                "is_factually_consistent": False,
                "verification_status": "unverifiable",
                "accuracy_percentage": 0.0,
                "hallucination_score": 1.0,
                "total_claims_audited": 0,
                "verified_facts": [],
                "discrepancies": [{
                    "token": "N/A",
                    "claimed_context": "No ground truth available",
                    "verification_status": "UNVERIFIABLE",
                    "reason": "Zero ground-truth datasets or metrics provided for verification."
                }],
                "summary": "Unverifiable: Zero ground-truth datasets or metrics available."
            }

        text_sections: list[str] = [
            report_dict.get("title", ""),
            report_dict.get("executive_summary", "")
        ]
        for f in report_dict.get("key_findings", []):
            if isinstance(f, dict):
                text_sections.append(f"{f.get('heading', '')}. {f.get('body', '')} {f.get('statistical_evidence', '')}")
        for r in report_dict.get("policy_recommendations", []):
            if isinstance(r, str):
                text_sections.append(r)

        claim_items: list[dict[str, Any]] = []
        for sec in text_sections:
            if sec:
                claim_items.extend(self.extract_claims_with_context(sec))

        verified_facts: list[dict[str, Any]] = []
        discrepancies: list[dict[str, Any]] = []
        seen_tokens: set[str] = set()

        for item in claim_items:
            token = item["token"]
            context = item["context"]
            start_pos = item.get("start", -1)
            end_pos = item.get("end", -1)

            if token in seen_tokens:
                continue
            seen_tokens.add(token)

            cand_vals = self.parse_numeric_value(token)
            if not cand_vals:
                continue

            is_benign = any(self.is_benign_structural_token(token, val) for val in cand_vals)
            if is_benign:
                continue

            claim_category = self.classify_claim_semantic_type(token, context, start_pos, end_pos)

            matched_fact = None
            semantic_mismatch_detected = None

            for cand in cand_vals:
                for entry in gt_index:
                    gt_val = entry["value"]
                    gt_cat = entry["category"]
                    tol = entry["tolerance"]

                    if abs(cand - gt_val) <= tol:
                        gt_sec = entry.get("sector")
                        claim_sec = self.extract_claim_sector(context, token_pos=start_pos)

                        # Explicit cross-sector isolation between distinct industry sectors (e.g. ICT vs Finance)
                        # National baselines ("Overall Economy") remain compatible across reports
                        if claim_sec and gt_sec and claim_sec != gt_sec and claim_sec != "Overall Economy" and gt_sec != "Overall Economy":
                            semantic_mismatch_detected = {
                                "claimed_category": f"{claim_category} ({claim_sec})",
                                "conflicting_ground_truth_category": f"{gt_cat} ({gt_sec})",
                                "conflicting_description": f"{entry['description']} [Belongs to {gt_sec}]"
                            }
                            continue

                        compatible = (
                            claim_category == gt_cat or
                            (claim_category == "PERCENTAGE" and gt_cat in ["PERCENTAGE", "CAGR", "TOTAL_GROWTH", "REENTRY_RATE"]) or
                            (claim_category == "GENERAL") or
                            (gt_cat == "GENERAL") or
                            (gt_cat == "RAG_POLICY_FACT")
                        )

                        # Explicit forbidden cross-domain bindings
                        if claim_category == "WAGE" and gt_cat != "WAGE" and gt_cat != "RAG_POLICY_FACT":
                            compatible = False
                        if gt_cat == "WAGE" and claim_category != "WAGE":
                            compatible = False
                        if claim_category == "RETRENCHMENT" and gt_cat != "RETRENCHMENT" and gt_cat != "RAG_POLICY_FACT":
                            compatible = False
                        if gt_cat == "RETRENCHMENT" and claim_category != "RETRENCHMENT":
                            compatible = False
                        if claim_category == "CAGR" and gt_cat != "CAGR" and gt_cat != "RAG_POLICY_FACT":
                            compatible = False

                        if compatible:
                            matched_fact = {
                                "token": token,
                                "matched_value": gt_val,
                                "category": gt_cat,
                                "source": entry["source"],
                                "verification_status": "EXACT_GROUND_TRUTH_MATCH",
                                "context": entry["description"]
                            }
                            break
                        else:
                            semantic_mismatch_detected = {
                                "claimed_category": claim_category,
                                "conflicting_ground_truth_category": gt_cat,
                                "conflicting_description": entry["description"]
                            }
                if matched_fact:
                    break

            if matched_fact:
                verified_facts.append(matched_fact)
            else:
                if semantic_mismatch_detected:
                    discrepancies.append({
                        "token": token,
                        "claimed_context": context[:140] + ("..." if len(context) > 140 else ""),
                        "verification_status": "SEMANTIC_DOMAIN_MISMATCH",
                        "reason": f"Value '{token}' is claimed in context of '{semantic_mismatch_detected['claimed_category']}', but in source data this number belongs to '{semantic_mismatch_detected['conflicting_ground_truth_category']}' ({semantic_mismatch_detected['conflicting_description']})."
                    })
                else:
                    discrepancies.append({
                        "token": token,
                        "claimed_context": context[:140] + ("..." if len(context) > 140 else ""),
                        "verification_status": "UNGROUNDED_OR_FABRICATED_METRIC",
                        "reason": f"Value '{token}' does not match any authoritative source record or computed statistical model in ground truth within acceptable tolerance."
                    })

        total_analyzed = len(verified_facts) + len(discrepancies)

        if total_analyzed == 0:
            accuracy_pct = 100.0
            hallucination_score = 0.0
            summary = "No quantitative claims detected in text."
            verif_status = "verified"
        else:
            accuracy_pct = round((len(verified_facts) / total_analyzed) * 100.0, 1)
            hallucination_score = round(len(discrepancies) / total_analyzed, 3)
            if len(discrepancies) == 0:
                summary = f"Audited {total_analyzed} quantitative claims: {len(verified_facts)} verified against ground truth; 0 discrepancies detected."
                verif_status = "verified"
            elif len(verified_facts) > 0:
                summary = f"Audited {total_analyzed} quantitative claims: {len(verified_facts)} verified; {len(discrepancies)} ungrounded or fabricated claims flagged as discrepancies."
                verif_status = "partially_verified"
            else:
                summary = f"Audited {total_analyzed} quantitative claims: 0 verified; {len(discrepancies)} ungrounded claims flagged."
                verif_status = "unverified"

        return {
            "is_factually_consistent": len(discrepancies) == 0 and len(verified_facts) > 0,
            "verification_status": verif_status,
            "hallucination_score": hallucination_score,
            "accuracy_percentage": accuracy_pct,
            "total_claims_audited": total_analyzed,
            "verified_facts": verified_facts,
            "discrepancies": discrepancies,
            "summary": summary
        }


hallucination_guard = HallucinationVerificationGuard()
