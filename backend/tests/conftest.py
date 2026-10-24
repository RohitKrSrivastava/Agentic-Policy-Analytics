import pytest
import os
import sys

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Initialize SQLite database
    init_db()
    yield
