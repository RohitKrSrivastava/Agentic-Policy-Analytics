import pytest
from backend.app.tools.data_quality import quality_engine

def test_data_quality_null_imputation():
    raw_data = [
        {"Period": "2020-Q1", "Employment Value": 100.0},
        {"Period": "2020-Q2", "Employment Value": None}, # missing value
        {"Period": "2020-Q3", "Employment Value": 120.0},
        {"Period": "2020-Q4", "Employment Value": 130.0}
    ]

    cleaned, report = quality_engine.audit_and_clean(
        data=raw_data,
        dataset_name="Test Employment Series",
        source_type="Test Source",
        data_format="JSON",
        numeric_columns=["Employment Value"]
    )

    assert report.total_records == 4
    assert report.missing_values_handled == 1
    # Check that column name was normalized
    assert "employment_value" in cleaned[0]
    # Check imputed value (should not be None)
    assert cleaned[1]["employment_value"] is not None
    assert cleaned[1]["employment_value"] == 100.0 # forward filled

def test_data_quality_outlier_treatment():
    raw_data = [
        {"metric": 10.0},
        {"metric": 11.0},
        {"metric": 10.5},
        {"metric": 11.2},
        {"metric": 950.0} # extreme outlier
    ]

    cleaned, report = quality_engine.audit_and_clean(
        data=raw_data,
        dataset_name="Outlier Test Series",
        source_type="Test Source",
        data_format="JSON",
        numeric_columns=["metric"]
    )

    assert report.outliers_identified >= 1
    # Check capped value
    assert cleaned[-1]["metric"] < 900.0
