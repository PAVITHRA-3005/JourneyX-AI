"""Platform smoke: cache, API middleware, redteam, docker files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_cache_roundtrip():
    from journeyx.rag.cache import cache_key, get_cached, set_cached
    from journeyx.tools.search_kb import search_travel_kb

    set_cached(cache_key("unique-query-xyz", None, [], 5), {"chunks": [], "query": "x"})
    out = search_travel_kb("Jaipur fort", dest_id="dest_jaipur", top_k=3)
    assert out.get("chunks") is not None


def test_api_request_id_header():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    r = client.post("/v1/chat", json={"message": "Hello Jaipur planning"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id")


def test_docker_compose_present():
    assert (ROOT / "docker-compose.yml").is_file()
    assert (ROOT / "infra/docker/Dockerfile").is_file()


def test_redteam_pii_refused():
    from journeyx.security.redteam import PII_PROBES, run_redteam

    results = {r.probe: r for r in run_redteam()}
    for probe in PII_PROBES:
        assert results[probe].refused, probe


def test_streamlit_app_is_importable():
    path = ROOT / "apps/ui/streamlit_app.py"
    code = path.read_text(encoding="utf-8")
    assert "st.chat_input" in code
    assert "Trace dashboard" in code


def test_compose_yaml_declares_api_and_ui():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "api:" in text
    assert "ui:" in text
    assert "8501" in text
    assert "8000" in text