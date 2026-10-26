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

    res = hallucination_guard.verify_report(grounded_report)
    assert res["is_factually_consistent"] is True
    assert res["accuracy_percentage"] == 100.0
    assert res["hallucination_score"] == 0.0
    assert len(res["discrepancies"]) == 0
    assert len(res["verified_facts"]) >= 5

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

    res = hallucination_guard.verify_report(hallucinated_report)
    # The guard MUST populate discrepancies and reject factual consistency!
    assert res["is_factually_consistent"] is False
    assert len(res["discrepancies"]) >= 3
    assert res["hallucination_score"] > 0.5
    
    # Check that the specific fabricated numbers are caught in discrepancies
    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("950,000" in t for t in flagged_tokens)
    assert any("98.5%" in t for t in flagged_tokens)
    assert any("1,200" in t for t in flagged_tokens)

def test_hallucination_guard_catches_subtle_numerical_errors():
    # Substring test: S$17,350 must NOT match ground truth S$7,350!
    subtle_hallucinated_report = {
        "title": "Subtle Inflation Report",
        "executive_summary": "The median gross salary was reported as S$17,350 instead of 7,350.",
        "key_findings": []
    }
    res = hallucination_guard.verify_report(subtle_hallucinated_report)
    assert res["is_factually_consistent"] is False
    flagged_tokens = [d["token"] for d in res["discrepancies"]]
    assert any("17,350" in t for t in flagged_tokens)

def test_dynamic_ground_truth_datasets_passed():
    # Test that custom ground truth datasets are properly indexed and matched
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

def test_consistency_across_repeated_evaluations():
    report = {
        "title": "Consistent Policy Synthesis",
        "executive_summary": "Employment grew from 118.4k to 175.1k.",
        "key_findings": []
    }
    run1 = hallucination_guard.verify_report(report)
    run2 = hallucination_guard.verify_report(report)
    assert run1["hallucination_score"] == run2["hallucination_score"]
    assert run1["accuracy_percentage"] == run2["accuracy_percentage"]
    assert len(run1["verified_facts"]) == len(run2["verified_facts"])
