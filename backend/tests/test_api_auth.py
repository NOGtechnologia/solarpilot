def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_setup_flow(client):
    st = client.get("/api/auth/status").json()
    assert st["has_users"] is False and st["authenticated"] is False
    assert client.get("/api/sites").status_code == 401
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "secret123"})
    assert r.status_code == 200
    assert client.get("/api/auth/status").json()["authenticated"] is True
    # zweiter Admin per Setup nicht möglich
    r = client.post("/api/auth/setup", json={"username": "x", "password": "secret123"})
    assert r.status_code == 409


def test_login_logout_and_rate_limit(admin):
    admin.post("/api/auth/logout")
    assert admin.get("/api/sites").status_code == 401
    r = admin.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert r.status_code == 200 and r.json()["token"]
    token = r.json()["token"]
    admin.post("/api/auth/logout")
    # Bearer-Token funktioniert ebenfalls
    assert admin.get("/api/sites", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    for _ in range(10):
        assert (
            admin.post(
                "/api/auth/login", json={"username": "admin", "password": "nope"}
            ).status_code
            == 401
        )
    assert (
        admin.post(
            "/api/auth/login", json={"username": "admin", "password": "secret123"}
        ).status_code
        == 429
    )


def test_users_admin_only(admin):
    r = admin.post("/api/users", json={"username": "viewer", "password": "viewer123"})
    assert r.status_code == 200
    uid = r.json()["id"]
    admin.post("/api/auth/logout")
    admin.post("/api/auth/login", json={"username": "viewer", "password": "viewer123"})
    assert admin.get("/api/sites").status_code == 200
    assert admin.post("/api/sites", json={"name": "x", "lat": 1, "lon": 1}).status_code == 403
    assert admin.get("/api/users").status_code == 403
    admin.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert len(admin.get("/api/users").json()) == 2
    assert (
        admin.put(f"/api/users/{uid}/password", json={"password": "newpass123"}).status_code == 200
    )
    assert admin.delete(f"/api/users/{uid}").status_code == 200


def test_public_dashboard(admin):
    admin.put("/api/settings/general", json={"public_dashboard": True})
    admin.post("/api/auth/logout")
    assert admin.get("/api/sites").status_code == 200
    assert admin.post("/api/sites", json={"name": "x", "lat": 1, "lon": 1}).status_code == 401


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
