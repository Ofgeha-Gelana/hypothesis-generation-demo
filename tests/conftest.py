"""
Test configuration and fixtures.

Heavy production dependencies (llama_index, prefect, torch, etc.) are not
installed in the test environment, so we stub them out via sys.modules BEFORE
any project code is imported.  This file is the first thing pytest loads, so
the stubs are in place for every test.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub heavy/absent production packages so project modules can be imported.
# ---------------------------------------------------------------------------
_STUBS = [
    # LLM / LlamaIndex
    "llama_index",
    "llama_index.core",
    "llama_index.core.llms",
    "llama_index.llms",
    "llama_index.llms.openai",
    "llama_index.llms.anthropic",
    # ML / embeddings
    "torch",
    "torchvision",
    "torchaudio",
    "sentence_transformers",
    "faiss",
    # Orchestration
    "prefect",
    "prefect.deployments",
    "prefect.states",
    "prefect.client",
    "prefect_dask",
    "dask",
    "dask.distributed",
    # Bioinformatics / genomics
    "gseapy",
    "gwaslab",
    "pysam",
    "cyvcf2",
    "pronto",
    "tiledbsoma",
    "cellxgene_census",
    # Misc
    "outlines",
    "pengines",
    "bokeh",
    "bokeh.plotting",
    "optuna",
    "openai",
    # MongoDB driver has a broken OpenSSL transitive dep in this environment;
    # stub it since all DB handlers are mocked in tests.
    "pymongo",
    "pymongo.errors",
    "pymongo.collection",
    "pymongo.database",
    "pymongo.mongo_client",
    "bson",
    "bson.objectid",
]

for _mod in _STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# ---------------------------------------------------------------------------
# Now it's safe to import project code and pytest helpers.
# ---------------------------------------------------------------------------
import os
import pytest
import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

TEST_USER_ID = "test-user-123"
TEST_JWT_SECRET = "test-secret-for-testing"


def make_token(user_id: str = TEST_USER_ID, secret: str = TEST_JWT_SECRET) -> str:
    """Generate a signed JWT for use in auth tests."""
    return jwt.encode({"user_id": user_id}, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Per-test mock fixtures for DB handlers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_project_handler():
    m = MagicMock()
    m.get_projects.return_value = []
    m.delete_project.return_value = False
    m.bulk_delete_projects.return_value = {
        "success": True, "deleted_count": 0, "total_requested": 0
    }
    m.load_analysis_state.return_value = None
    return m


@pytest.fixture
def mock_analysis_handler():
    m = MagicMock()
    m.get_credible_sets_for_project.return_value = []
    return m


@pytest.fixture
def mock_hypothesis_handler():
    m = MagicMock()
    m.get_hypotheses.return_value = []
    return m


@pytest.fixture
def mock_file_handler():
    m = MagicMock()
    m.get_file_metadata.return_value = {"download_url": None, "record_count": 0}
    return m


# ---------------------------------------------------------------------------
# Core test app + client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app(
    mock_project_handler,
    mock_analysis_handler,
    mock_hypothesis_handler,
    mock_file_handler,
):
    """FastAPI test app with all external dependencies mocked out."""
    from src.api.routes.internal import router as internal_router
    from src.api.routes.projects import router as projects_router
    from src.api.auth import get_current_user_id
    from src.api.dependencies import (
        get_analysis_handler,
        get_config,
        get_enrichment_handler,
        get_enrichr,
        get_file_handler,
        get_gene_expression_handler,
        get_gwas_library_handler,
        get_hypothesis_handler,
        get_llm,
        get_phenotype_handler,
        get_project_handler,
        get_prolog_query,
        get_storage,
        get_summary_handler,
        get_task_handler,
        get_user_handler,
    )

    app = FastAPI()
    app.include_router(internal_router)
    app.include_router(projects_router)

    # Bypass JWT auth — return a fixed user ID for all authenticated routes.
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

    # Wire in mock handlers.
    app.dependency_overrides[get_project_handler] = lambda: mock_project_handler
    app.dependency_overrides[get_analysis_handler] = lambda: mock_analysis_handler
    app.dependency_overrides[get_hypothesis_handler] = lambda: mock_hypothesis_handler
    app.dependency_overrides[get_file_handler] = lambda: mock_file_handler
    app.dependency_overrides[get_enrichment_handler] = lambda: MagicMock()
    app.dependency_overrides[get_gene_expression_handler] = lambda: MagicMock()
    app.dependency_overrides[get_gwas_library_handler] = lambda: MagicMock()
    app.dependency_overrides[get_config] = lambda: MagicMock()
    app.dependency_overrides[get_storage] = lambda: MagicMock()
    app.dependency_overrides[get_user_handler] = lambda: MagicMock()
    app.dependency_overrides[get_summary_handler] = lambda: MagicMock()
    app.dependency_overrides[get_task_handler] = lambda: MagicMock()
    app.dependency_overrides[get_prolog_query] = lambda: MagicMock()
    app.dependency_overrides[get_llm] = lambda: MagicMock()
    app.dependency_overrides[get_enrichr] = lambda: MagicMock()
    app.dependency_overrides[get_phenotype_handler] = lambda: MagicMock()

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def auth_client(test_app, monkeypatch):
    """Client that exercises real JWT validation (JWT_SECRET patched to a test value)."""
    import src.api.auth as auth_module
    monkeypatch.setattr(auth_module, "JWT_SECRET", TEST_JWT_SECRET)

    from src.api.auth import get_current_user_id
    test_app.dependency_overrides.pop(get_current_user_id, None)

    return TestClient(test_app)
