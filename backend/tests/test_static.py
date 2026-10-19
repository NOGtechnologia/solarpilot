from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app, next_segment_path


def test_next_segment_path():
    assert next_segment_path("settings/__next.settings.__PAGE__.txt") == (
        "settings/__next.settings/__PAGE__.txt"
    )
    assert next_segment_path("__next.x.y.z.txt") == "__next.x/y/z.txt"
    assert next_segment_path("settings/index.txt") is None
    assert next_segment_path("__next._tree.txt") is None


def test_static_export_served_with_prefetch_fallback(tmp_path, monkeypatch):
    (tmp_path / "settings" / "__next.settings").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "404.html").write_text("nope")
    (tmp_path / "settings" / "index.html").write_text("settings")
    (tmp_path / "settings" / "__next.settings" / "__PAGE__.txt").write_text("rsc")
    monkeypatch.setattr(get_settings(), "static_dir", tmp_path)
    with TestClient(create_app()) as c:
        assert c.get("/").text == "<h1>home</h1>"
        assert c.get("/settings/").text == "settings"
        assert c.get("/settings/__next.settings.__PAGE__.txt").text == "rsc"
        r = c.get("/gibt-es-nicht/")
        assert r.status_code == 404 and r.text == "nope"
        assert c.get("/api/nope").json()["detail"]
