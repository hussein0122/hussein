from __future__ import annotations

import hmac
import os
import secrets
import time
from datetime import timedelta
from functools import wraps

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

OWNER = "hussein0122"
REPO = "hussein"
WORKFLOW = "shorts.yml"
ADMIN_EMAIL = "husseinsead3@gmail.com"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "")
if len(app.secret_key) < 32:
    raise RuntimeError("SESSION_SECRET must be a random value of at least 32 characters")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

_login_attempts: dict[str, list[float]] = {}


def csrf_token() -> str:
    token = session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def require_csrf() -> None:
    supplied = request.form.get("csrf") or request.headers.get("X-CSRF-Token", "")
    if not supplied or not hmac.compare_digest(supplied, session.get("csrf", "")):
        abort(400, "Invalid CSRF token")


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("admin_email") != ADMIN_EMAIL:
            if request.path.startswith("/api/"):
                return jsonify(error="تسجيل الدخول مطلوب"), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


def github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_ACTIONS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_ACTIONS_TOKEN is not configured in the hosting environment")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
    return response


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_email") == ADMIN_EMAIL:
        return redirect(url_for("dashboard"))
    error = ""
    if request.method == "POST":
        require_csrf()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        now = time.time()
        attempts = [t for t in _login_attempts.get(ip, []) if now - t < 900]
        if len(attempts) >= 8:
            return render_template("login.html", error="محاولات كثيرة. حاول بعد 15 دقيقة."), 429
        attempts.append(now)
        _login_attempts[ip] = attempts
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        stored_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
        configured_password = os.environ.get("ADMIN_PASSWORD", "")
        password_ok = (bool(stored_hash) and check_password_hash(stored_hash, password)) or (bool(configured_password) and hmac.compare_digest(configured_password, password))
        valid = email == ADMIN_EMAIL and password_ok
        if valid:
            session.clear()
            session.permanent = True
            session["admin_email"] = ADMIN_EMAIL
            session["csrf"] = secrets.token_urlsafe(32)
            _login_attempts.pop(ip, None)
            return redirect(url_for("dashboard"))
        error = "بيانات الدخول غير صحيحة."
    return render_template("login.html", error=error)


@app.post("/logout")
@login_required
def logout():
    require_csrf()
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def dashboard():
    return render_template("dashboard.html", admin_email=ADMIN_EMAIL)


@app.get("/api/status")
@login_required
def status():
    try:
        response = requests.get(
            f"{API}/actions/runs",
            headers=github_headers(),
            params={"per_page": 8},
            timeout=20,
        )
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
        latest = next((r for r in runs if r.get("path", "").endswith(WORKFLOW)), None)
        return jsonify(
            connected=True,
            workflow="ShortsPilot AR",
            latest=latest,
            recent=[{
                "id": r.get("id"),
                "run_number": r.get("run_number"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "created_at": r.get("created_at"),
                "run_started_at": r.get("run_started_at"),
                "html_url": r.get("html_url"),
                "event": r.get("event"),
            } for r in runs if r.get("path", "").endswith(WORKFLOW)][:6],
        )
    except requests.RequestException as exc:
        return jsonify(connected=False, error=f"GitHub API: {type(exc).__name__}"), 502
    except RuntimeError as exc:
        return jsonify(connected=False, error=str(exc)), 503


@app.post("/api/run")
@login_required
def run_now():
    require_csrf()
    try:
        response = requests.post(
            f"{API}/actions/workflows/{WORKFLOW}/dispatches",
            headers=github_headers(),
            json={"ref": "main"},
            timeout=20,
        )
        if response.status_code != 204:
            return jsonify(ok=False, error=f"GitHub رفض بدء التشغيل (HTTP {response.status_code})."), 502
        return jsonify(ok=True, message="تم إرسال طلب التشغيل إلى GitHub Actions. تابع الحالة من لوحة التحكم.")
    except requests.RequestException as exc:
        return jsonify(ok=False, error=f"تعذر الاتصال بـ GitHub: {type(exc).__name__}"), 502
    except RuntimeError as exc:
        return jsonify(ok=False, error=str(exc)), 503



@app.post("/api/cancel")
@login_required
def cancel_run():
    require_csrf()
    payload = request.get_json(silent=True) or {}
    run_id = payload.get("run_id")
    if not isinstance(run_id, int) or run_id <= 0:
        return jsonify(ok=False, error="رقم التشغيل غير صالح."), 400
    try:
        headers = github_headers()
        check = requests.get(f"{API}/actions/runs/{run_id}", headers=headers, timeout=20)
        if check.status_code != 200:
            return jsonify(ok=False, error="لم أستطع التحقق من التشغيل المطلوب."), 404
        run = check.json()
        if not run.get("path", "").endswith(WORKFLOW):
            return jsonify(ok=False, error="هذا التشغيل لا يخص بوت ShortsPilot."), 403
        if run.get("status") not in ("queued", "in_progress", "waiting", "pending"):
            return jsonify(ok=False, error="التشغيل انتهى بالفعل."), 409
        response = requests.post(f"{API}/actions/runs/{run_id}/cancel", headers=headers, timeout=20)
        if response.status_code not in (202, 409):
            return jsonify(ok=False, error=f"GitHub رفض إيقاف التشغيل (HTTP {response.status_code})."), 502
        return jsonify(ok=True, message="تم إرسال طلب الإيقاف إلى GitHub Actions.")
    except requests.RequestException as exc:
        return jsonify(ok=False, error=f"تعذر الاتصال بـ GitHub: {type(exc).__name__}"), 502
    except RuntimeError as exc:
        return jsonify(ok=False, error=str(exc)), 503


@app.get("/api/csrf")
@login_required
def csrf():
    return jsonify(token=csrf_token())
