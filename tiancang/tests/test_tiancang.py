import importlib, os
from pathlib import Path
from fastapi.testclient import TestClient


def load(tmp_path: Path):
    os.environ.update(TIANCANG_PDF_ROOT=str(tmp_path), TIANCANG_ADMIN_USERNAME="admin", TIANCANG_ADMIN_PASSWORD="test-only-password", TIANCANG_SESSION_SECRET="test-only-session-secret-32-bytes")
    import app
    return importlib.reload(app)


def test_auth_crud_public_and_traversal(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    app = load(tmp_path)
    c = TestClient(app.app)
    assert c.get("/", follow_redirects=False).status_code == 302
    assert c.get("/api/files").status_code == 401
    assert c.post("/api/login", data={"username":"admin","password":"wrong"}).status_code == 401
    assert c.post("/api/login", data={"username":"admin","password":"test-only-password"}).status_code == 200
    assert c.post("/api/dirs", data={"path":"虚构/长目录"}).status_code == 200
    fake = b"%PDF-1.4\n% temporary fictitious test only\n%%EOF\n"
    name = "虚构测试_" + "长名称" * 20 + ".pdf"
    r = c.post("/api/upload", data={"directory":"虚构/长目录"}, files={"file":(name, fake, "application/pdf")})
    assert r.status_code == 200
    public = c.get("/public/pdfs/虚构/长目录/" + name)
    assert public.status_code == 200 and public.headers["content-type"].startswith("application/pdf") and public.content.startswith(b"%PDF-")
    assert c.get("/public/pdfs/%2e%2e/out.pdf").status_code in (400,404)
    assert c.post("/api/dirs", data={"path":"../escape"}).status_code == 400
    assert c.delete("/api/dirs/虚构/长目录").status_code == 409
    assert c.delete("/api/files/虚构/长目录/" + name).status_code == 200
    assert c.delete("/api/dirs/虚构/长目录").status_code == 200
    assert not list(tmp_path.rglob("*.pdf"))


def test_upload_rejects_non_pdf(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    app = load(tmp_path)
    c = TestClient(app.app)
    c.post("/api/login", data={"username":"admin","password":"test-only-password"})
    assert c.post("/api/upload", files={"file":("x.pdf", b"not pdf", "application/pdf")}).status_code == 400


def test_viewer_return_contract(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    app = load(tmp_path)
    c = TestClient(app.app)
    c.post("/api/login", data={"username":"admin","password":"test-only-password"})
    (tmp_path / "contract.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    row = c.get("/api/files").json()["files"][0]
    assert row["viewer_url"].endswith("&return=%2F")
    viewer = c.get("/pdfjs/web/viewer.html").text
    return_js = c.get("/pdfjs/web/tiancang-return.js").text
    assert "tiancangReturnButton" in viewer and "返回天仓目录" in viewer
    assert "target.origin !== window.location.origin" in return_js
    assert "target.pathname !== directoryPath" in return_js
    assert "window.history.back" not in return_js
    assert "document.referrer" in return_js and "window.location.assign" in return_js
    assert "pageRotateCw" in return_js and "tiancangRotateButton" in return_js
    css = c.get("/pdfjs/web/viewer.css").text
    assert "TianCang narrow-toolbar override" in css
    assert "grid-template-rows: 44px 44px" in css
    assert "#tiancangReturnButton" in css and "min-width: 44px" in css
