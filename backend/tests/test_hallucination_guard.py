import pytest

from backend.app.evaluation.hallucination_guard import hallucination_guard


@pytest.fixture
def sample_ground_truth():
    return {
        "metrics": {
            "tech_cagr": 8.14,
            "net_jobs_added": 56700,
            "tech_total_growth_pct": 47.9,
            "peak_vacancies": 21300,
            "tech_median_wage": 7350,
            "national_median_wage": 5350,
            "tech_premium_pct": 37.4
        },
        "datasets": {
            "singstat": [
                {"year": 2020, "quarter": "Q1", "employment_thousands": 118.4, "sector": "Information & Communications"},
                {"year": 2024, "quarter": "Q4", "employment_thousands": 175.1, "sector": "Information & Communications"}
            ],
            "mom": [
                {"year": 2022, "quarter": "Q1", "period": "2022-Q1", "tech_job_vacancies": 21300, "tech_retrenchments": 780, "vacancy_to_unemployed_ratio": 2.42}
            ],
            "wages": [
                {"industry": "Information & Communications", "role_level": "Industry Overall", "median_gross_wage_sgd": 7350, "year": 2024},
                {"industry": "National", "role_level": "Median", "median_gross_wage_sgd": 5350, "year": 2024}
            ]
        }
    }


def test_accurate_report_validation(sample_ground_truth):
    grounded_report = {
        "title": "Singapore Tech Employment 2020-2024",
        "executive_summary": "Between 2020 and 2024, Singapore's tech employment expanded from 118.4k to 175.1k workers, achieving an 8.14% CAGR.",
        "key_findings": [
            {
                "heading": "Peak Vacancies",
                "body": "Tech job openings peaked at 21,300 in 2022-Q1 with a vacancy ratio of 2.42.",
                "statistical_evidence": "21,300 peak vacancies",
                "citation_id": "MOM-LMR-2024"
            },
            {
                "heading": "Salary Premium",
                "body": "The median gross salary reached S$7,350 in 2024 compared to national median of S$5,350, a 37.4% premium.",
                "statistical_evidence": "S$7,350 vs S$5,350",
                "citation_id": "DATAGOVSG-WAGES-V2"
            }
        ]
    }

    res = hallucination_guard.verify_report(grounded_report, ground_truth=sample_ground_truth)
    assert res["is_factually_consistent"] is True
    assert res["accuracy_percentage"] == 100.0
    assert res["hallucination_score"] == 0.0
    assert len(res["discrepancies"]) == 0
    assert len(res["verified_facts"]) >= 5


def test_hallucination_guard_detects_fabrications(sample_ground_truth):
    hallucinated_report = {
        "title": "Fabricated Report",
        "executive_summary": "Singapore tech workforce reached 950,000 workers in 2024 with a 98.5% growth rate.",
        "key_findings": [
            {
                "heading": "Inflated Retrenchments",
                "body": "Retrenchments exceeded 85,000 workers and wages plummeted to S$1,200.",
                "statistical_evidence": "85,000 retrenchments, S$1,200 wages",
                "citation_id": "FAKE-SRC"
            }
        ]
    }

    res = hallucination_guard.verify_report(hallucinated_report, ground_truth=sample_ground_truth)
    assert res["is_factually_consistent"] is False
    assert len(res["discrepancies"]) >= 3
    assert res["hallucination_score"] > 0.5

    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("950,000" in t for t in flagged_tokens)
    assert any("98.5%" in t for t in flagged_tokens)
    assert any("1,200" in t for t in flagged_tokens)


def test_hallucination_guard_catches_subtle_numerical_errors(sample_ground_truth):
    subtle_hallucinated_report = {
        "title": "Subtle Inflation Report",
        "executive_summary": "The median gross salary was reported as S$17,350 instead of 7,350.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(subtle_hallucinated_report, ground_truth=sample_ground_truth)
    assert res["is_factually_consistent"] is False
    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("17,350" in t for t in flagged_tokens)


def test_semantic_metric_binding_catches_cross_domain_fabrication(sample_ground_truth):
    """
    Asserts that numbers appearing elsewhere in datasets cannot masquerade as other metrics:
    1. 'Retrenchments hit 7,350' (7350 is a wage, NOT retrenchments) must fail!
    2. 'CAGR was 47.9%' (47.9% is total growth, NOT CAGR) must fail!
    """
    cross_domain_report = {
        "title": "Cross-Domain Semantic Collision Report",
        "executive_summary": "Annual employment CAGR was 47.9% across the five-year window.",
        "key_findings": [
            {
                "heading": "Retrenchment Spike",
                "body": "Quarterly retrenchments hit 7,350 during the restructuring wave.",
                "statistical_evidence": "7,350 retrenchments",
                "citation_id": "MOM-LMR"
            }
        ]
    }
    res = hallucination_guard.verify_report(cross_domain_report, ground_truth=sample_ground_truth)
    assert res["is_factually_consistent"] is False
    assert len(res["discrepancies"]) >= 2
    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("7,350" in t for t in flagged_tokens)
    assert any("47.9%" in t for t in flagged_tokens)


def test_close_number_mutation_catches_approximate_wages(sample_ground_truth):
    """
    Asserts that S$7,400 (which is within 1% of S$7,350) is strictly caught as a discrepancy,
    rather than passing due to loose tolerance.
    """
    close_mutation_report = {
        "title": "Close Wage Mutation Report",
        "executive_summary": "Median gross salary in tech reached S$7,400 per month.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(close_mutation_report, ground_truth=sample_ground_truth)
    assert res["is_factually_consistent"] is False
    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("7,400" in t for t in flagged_tokens)


def test_dynamic_ground_truth_datasets_passed():
    custom_gt = {
        "metrics": {"custom_metric": 42.8},
        "datasets": {
            "singstat": [{"employment_thousands": 250.5, "year": 2023, "quarter": "Q2"}]
        }
    }
    report = {
        "title": "Custom Data Report",
        "executive_summary": "Employment recorded was 250.5k with a custom metric of 42.8%.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(report, ground_truth=custom_gt)
    assert res["is_factually_consistent"] is True
    assert res["hallucination_score"] == 0.0
    assert len(res["verified_facts"]) >= 2


def test_consistency_across_repeated_evaluations(sample_ground_truth):
    report = {
        "title": "Consistent Policy Synthesis",
        "executive_summary": "Employment grew from 118.4k to 175.1k.",
        "key_findings": []
    }
    run1 = hallucination_guard.verify_report(report, ground_truth=sample_ground_truth)
    run2 = hallucination_guard.verify_report(report, ground_truth=sample_ground_truth)
    assert run1["hallucination_score"] == run2["hallucination_score"]
    assert run1["accuracy_percentage"] == run2["accuracy_percentage"]
    assert len(run1["verified_facts"]) == len(run2["verified_facts"])


def test_hallucination_guard_unverifiable_when_ground_truth_empty():
    """
    Finding 6 / Section 2 Verification:
    If zero ground truth datasets are provided, hallucination guard returns
    verification_status='unverifiable' instead of assuming stale hardcoded facts.
    """
    report = {
        "title": "Unverified Report",
        "executive_summary": "Employment reached 175.1k with 8.14% CAGR.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(report, ground_truth={})
    assert res["is_factually_consistent"] is False
    assert res["verification_status"] == "unverifiable"
    assert res["accuracy_percentage"] == 0.0
    assert len(res["discrepancies"]) == 1
    assert res["discrepancies"][0]["verification_status"] == "UNVERIFIABLE"


def test_rag_numbers_not_flagged_as_hallucinations(sample_ground_truth):
    """
    Finding 8: RAG policy whitepapers contain empirical figures (e.g., 35% target, S$500M budget).
    When indexed into ground truth under RAG_POLICY_FACT, they are verified as ground truth.
    """
    rag_chunks = [
        {
            "doc_title": "Singapore Smart Nation 2.0 Roadmap",
            "section": "Funding Allocation",
            "content": "The National AI Strategy committed S$500M to talent development and targeted 35% growth in AI engineering roles by 2026."
        }
    ]
    report = {
        "title": "Smart Nation Policy Progress",
        "executive_summary": "Under the Smart Nation 2.0 Roadmap, S$500M was committed to talent development targeting 35% growth in AI roles.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(report, ground_truth=sample_ground_truth, rag_chunks=rag_chunks)
    assert res["is_factually_consistent"] is True
    assert res["hallucination_score"] == 0.0
    flagged = [d["token"] for d in res["discrepancies"]]
    assert not any("500" in t or "35%" in t for t in flagged)


def test_sector_isolated_ground_truth_rejection():
    """
    Step 2 / Ground Truth Sector Isolation:
    A finance number must not verify a tech claim, and vice versa.
    When a report claims a finance headcount figure in a tech sector context,
    the hallucination guard flags a cross-sector semantic mismatch.
    """
    multi_sec_gt = {
        "metrics": {
            "sector_metrics": {
                "Information & Communications": {"tech_cagr": 8.14, "net_jobs_added": 56700},
                "Financial & Insurance Services": {"tech_cagr": 5.20, "net_jobs_added": 32000}
            }
        },
        "datasets": {
            "singstat": [
                {"year": 2024, "quarter": "Q4", "employment_thousands": 175.1, "sector": "Information & Communications"},
                {"year": 2024, "quarter": "Q4", "employment_thousands": 245.5, "sector": "Financial & Insurance Services"}
            ],
            "wages": [
                {"industry": "Information & Communications", "median_gross_wage_sgd": 7350, "year": 2024},
                {"industry": "Financial & Insurance Services", "median_gross_wage_sgd": 8800, "year": 2024}
            ]
        }
    }

    # Cross-sector attribution: claiming finance headcount (245.5k) for the technology sector
    invalid_report = {
        "title": "Cross-Sector Verification Check",
        "executive_summary": "In the technology sector, total employment reached 245.5k with median wage of S$7,350.",
        "key_findings": [
            {
                "heading": "Technology Headcount",
                "body": "Singapore tech workforce reached 245.5k workers by 2024.",
                "sentiment": "positive",
                "statistical_evidence": "245.5k tech workers",
                "citation_id": "SINGSTAT-M015661"
            }
        ]
    }

    res = hallucination_guard.verify_report(invalid_report, ground_truth=multi_sec_gt)
    assert res["is_factually_consistent"] is False
    assert len(res["discrepancies"]) >= 1

    # Ensure the discrepancy correctly notes that 245.5k belongs to Financial & Insurance Services
    mismatch_disc = next(d for d in res["discrepancies"] if "245.5" in d["token"])
    assert "Financial & Insurance Services" in mismatch_disc["reason"]
    assert "Information & Communications" in mismatch_disc["reason"] or "tech" in mismatch_disc["claimed_context"].lower()

