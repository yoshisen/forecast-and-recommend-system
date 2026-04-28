from __future__ import annotations

import importlib
from datetime import datetime

from fastapi.testclient import TestClient
import pytest


app = importlib.import_module("app.main").app


@pytest.fixture
def client():
    """Provide a clean app state for each test."""
    app.state.data_versions = {}
    app.state.current_version = None
    app.state.forecast_pipeline = None
    app.state.recommender = None
    app.state.classifier = None
    app.state.association_miner = None
    app.state.clusterer = None
    app.state.prophet_forecaster = None
    app.state.ws_clients = set()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_version(request):
    """Seed one minimal version for API tests that require uploaded data."""
    request.getfixturevalue("client")
    version_id = "test_version"
    app.state.data_versions[version_id] = {
        "parsed_data": {},
        "parse_report": {},
        "quality_report": {
            "overall_summary": {
                "total_sheets": 0,
                "total_rows": 0,
                "total_fields": 0,
            },
            "sheet_reports": {},
        },
        "validation_result": {},
        "uploaded_at": datetime.now().isoformat(),
        "filename": "seed.xlsx",
        "training": {},
        "task_readiness": {},
    }
    app.state.current_version = version_id
    return version_id