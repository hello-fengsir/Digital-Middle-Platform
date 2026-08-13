from __future__ import annotations
import hashlib, hmac, os, secrets, shutil, time
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

APP_DIR = Path(__file__).resolve().parent
ROOT = Path(os.getenv("TIANCANG_PDF_ROOT", "/data/pdfs")).resolve()
USER = os.getenv("TIANCANG_ADMIN_USERNAME", "admin")
PASS = os.environ.get("TIANCANG_ADMIN_PASSWORD")
SECRET_TEXT = os.environ.get("TIANCANG_SESSION_SECRET")
if not PASS or len(PASS) < 12:
    raise RuntimeError("TIANCANG_ADMIN_PASSWORD must be set and at least 12 characters")
if not SECRET_TEXT or len(SECRET_TEXT) < 32:
    raise RuntimeError("TIANCANG_SESSION_SECRET must be set and at least 32 characters")
SECRET = SECRET_TEXT.encode()
MAX_BYTES = int(os.getenv("TIANCANG_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
COOKIE = "tiancang_session"
app = FastAPI(title="TianCang Standalone", docs_url=None, redoc_url=None)
ROOT.mkdir(parents=True, exist_ok=True)


def clean_rel(raw: str, allow_empty: bool = True) -> str:
    raw = (raw or "").replace("\\", "/").strip("/")
    p = PurePosixPath(raw)
    if (not allow_empty and not raw) or p.is_absolute() or any(x in ("", ".", "..") for x in p.parts):
        raise HTTPException(400, "非法路径")
    return "/".join(p.parts)


def target(raw: str, allow_empty: bool = True) -> Path:
    rel = clean_rel(raw, allow_empty)
    out = (ROOT / rel).resolve()
    if out != ROOT and ROOT not in out.parents:
        raise HTTPException(400, "路径越界")
    return out


def sign(exp: int) -> str:
    body = f"{USER}:{exp}"
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def authed(req: Request) -> bool:
    val = req.cookies.get(COOKIE, "")
    try:
        exp_s, sig = val.split(".", 1); exp = int(exp_s)
        return exp >= int(time.time()) and hmac.compare_digest(sign(exp).split(".",1)[1], sig)
    except Exception:
        return False


def require(req: Request):
    if not authed(req): raise HTTPException(401, "需要管理员认证")

@app.get("/healthz")
def health(): return {"status":"ok"}

@app.get("/", response_class=HTMLResponse)
def home(req: Request):
    if not authed(req): return RedirectResponse("/login", 302)
    return FileResponse(APP_DIR / "static/index.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(): return FileResponse(APP_DIR / "static/login.html")

@app.post("/api/login")
def login(username: str = Form(...), password: str = Form(...)):
    if not (hmac.compare_digest(username, USER) and hmac.compare_digest(password, PASS)):
        raise HTTPException(401, "用户名或密码错误")
    exp = int(time.time()) + 28800
    r = JSONResponse({"ok": True}); r.set_cookie(COOKIE, sign(exp), httponly=True, samesite="strict", max_age=28800)
    return r

@app.post("/api/logout")
def logout():
    r=JSONResponse({"ok":True}); r.delete_cookie(COOKIE); return r

@app.get("/api/files")
def files(req: Request):
    require(req); rows=[]
    for p in sorted(ROOT.rglob("*.pdf"), key=lambda x: str(x).lower()):
        if p.is_file():
            rel=p.relative_to(ROOT).as_posix(); st=p.stat()
            rows.append({"path":rel,"name":p.name,"size":st.st_size,"mtime":int(st.st_mtime),"public_url":"/public/pdfs/"+quote(rel),"viewer_url":"/pdfjs/web/viewer.html?file="+quote("/public/pdfs/"+rel)+"&return="+quote("/", safe="")})
    return {"count":len(rows),"files":rows}

@app.get("/api/dirs")
def dirs(req: Request):
    require(req); return {"dirs":[p.relative_to(ROOT).as_posix() for p in sorted(ROOT.rglob("*")) if p.is_dir()]}

@app.post("/api/dirs")
def mkdir(req: Request, path: str = Form(...)):
    require(req); p=target(path, False); p.mkdir(parents=True, exist_ok=False); return {"ok":True,"path":p.relative_to(ROOT).as_posix()}

@app.post("/api/upload")
async def upload(req: Request, directory: str = Form(""), file: UploadFile = File(...)):
    require(req); d=target(directory); d.mkdir(parents=True, exist_ok=True)
    name=Path(file.filename or "").name
    if not name or not name.lower().endswith(".pdf"): raise HTTPException(400,"仅允许 PDF")
    out=target((clean_rel(directory)+"/" if directory else "")+name, False)
    if out.exists(): raise HTTPException(409,"文件已存在")
    tmp=out.with_name("."+out.name+"."+secrets.token_hex(6)+".tmp"); total=0
    try:
        with tmp.open("xb") as f:
            first=await file.read(5)
            if first != b"%PDF-": raise HTTPException(400,"文件不是有效 PDF")
            f.write(first); total=5
            while chunk:=await file.read(1024*1024):
                total += len(chunk)
                if total > MAX_BYTES: raise HTTPException(413,"文件过大")
                f.write(chunk)
        os.replace(tmp,out)
    finally:
        tmp.unlink(missing_ok=True)
    return {"ok":True,"path":out.relative_to(ROOT).as_posix(),"size":total}

@app.delete("/api/files/{path:path}")
def delete_file(path: str, req: Request):
    require(req); p=target(path,False)
    if not p.is_file() or p.suffix.lower() != ".pdf": raise HTTPException(404,"文件不存在")
    p.unlink(); return {"ok":True}

@app.delete("/api/dirs/{path:path}")
def delete_dir(path: str, req: Request):
    require(req); p=target(path,False)
    if not p.is_dir(): raise HTTPException(404,"目录不存在")
    try: p.rmdir()
    except OSError: raise HTTPException(409,"目录非空")
    return {"ok":True}

@app.get("/public/pdfs/{path:path}")
def public_pdf(path: str):
    p=target(path,False)
    if not p.is_file() or p.suffix.lower() != ".pdf": raise HTTPException(404,"PDF 不存在")
    return FileResponse(p, media_type="application/pdf", headers={"X-Content-Type-Options":"nosniff","Cache-Control":"public, max-age=3600"})

app.mount("/pdfjs", StaticFiles(directory=APP_DIR / "pdfjs", html=True), name="pdfjs")
