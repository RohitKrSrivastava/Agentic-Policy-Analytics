import pytest
from backend.app.evaluation.hallucination_guard import hallucination_guard

def test_accurate_report_validation():
    # Report containing exact grounded numbers
    grounded_report = {
        "title": "Singapore Tech Employment 2020-2024",
        "executive_summary": "Between 2020 and 2024, Singapore's tech employment expanded from 118.4k to 175.1k workers, achieving a 10.3% CAGR.",
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

    res = hallucination_guard.verify_report(grounded_report, ground_truth={})
    assert res["is_factually_consistent"] is True
    assert res["accuracy_percentage"] == 100.0
    assert res["hallucination_score"] == 0.0
    assert len(res["verified_facts"]) >= 4

def test_hallucination_guard_detects_fabrications():
    # Report containing completely ungrounded fabricated statistics
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

    res = hallucination_guard.verify_report(hallucinated_report, ground_truth={})
    # Since none of 950,000, 98.5%, 85,000, 1,200 match ground truth, verified facts will be 0
    assert len(res["verified_facts"]) == 0
    assert res["total_claims_audited"] == 0

def test_consistency_across_repeated_evaluations():
    report = {
        "title": "Consistent Policy Synthesis",
        "executive_summary": "Employment grew from 118.4k to 175.1k.",
        "key_findings": []
    }
    run1 = hallucination_guard.verify_report(report, ground_truth={})
    run2 = hallucination_guard.verify_report(report, ground_truth={})
    assert run1["hallucination_score"] == run2["hallucination_score"]
    assert run1["accuracy_percentage"] == run2["accuracy_percentage"]
