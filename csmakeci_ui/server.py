"""Flask UI server — fetches data from csmakeci-server, renders Jinja2 templates.

Secrets are managed here in the UI layer directly via a pluggable provider
(csmakeci_ui.secrets).  The API server has no secrets knowledge.
"""
from __future__ import annotations

import time
from typing import Any

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from csmakeci_ui.client import ServerClient
from csmakeci_ui.secrets import load_provider
from csmakeci_ui.secrets.base import BaseSecretsProvider

app = Flask(__name__)

_client: ServerClient | None = None
_secrets: BaseSecretsProvider | None = None


def create_app(server_url: str, secrets_config: dict | None = None) -> Flask:
    global _client, _secrets
    _client = ServerClient(server_url)
    _secrets = load_provider(secrets_config or {})
    return app


def _c() -> ServerClient:
    assert _client is not None, "create_app() must be called first"
    return _client


def _sp() -> BaseSecretsProvider:
    assert _secrets is not None, "create_app() must be called first"
    return _secrets


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

@app.context_processor
def _inject():
    return {
        "server_url": _client.base_url if _client else "",
        "fmt_duration": _fmt_duration,
        "fmt_relative": _fmt_relative,
        "fmt_ts": _fmt_ts,
    }


def _fmt_duration(started: float | None, finished: float | None) -> str:
    if not started:
        return "—"
    secs = (finished or time.time()) - started
    m, s = int(secs // 60), int(secs % 60)
    return f"{m}m {s:02d}s"


def _fmt_relative(ts: float | None) -> str:
    if not ts:
        return "—"
    diff = time.time() - ts
    if diff < 60:    return "just now"
    if diff < 3600:  return f"{int(diff/60)} min ago"
    if diff < 86400: return f"{int(diff/3600)} hr ago"
    return f"{int(diff/86400)}d ago"


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return ""
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


import re as _re

@app.template_filter("regex_findall")
def _regex_findall(value: str, pattern: str):
    return _re.findall(pattern, value or "")


import os as _os

@app.template_filter("dirname")
def _dirname(value: str) -> str:
    return _os.path.dirname(value) or value


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    data = _c().get("/api/workflows")
    runs_data = _c().get("/api/runs", limit=25)
    return render_template(
        "dashboard.html",
        workflows=data.get("workflows", []),
        runs=runs_data.get("runs", []),
        stats=data.get("stats", {}),
    )


@app.route("/workflow/<name>")
def workflow_detail(name: str):
    return redirect(url_for("visualize", workflow=name))


@app.route("/run/<run_id>")
def run_detail(run_id: str):
    data = _c().get(f"/api/runs/{run_id}")
    if not data:
        abort(404)
    stream_url = _c().stream_url(run_id)
    return render_template(
        "run.html",
        run=data["run"],
        steps=data.get("steps", []),
        phase_memory=data.get("phase_memory", []),
        artifacts=data.get("artifacts", []),
        stream_url=stream_url,
        log_api_url=_c().base_url + f"/api/runs/{run_id}/log",
    )


@app.route("/visualize")
def visualize():
    workflow_name = request.args.get("workflow", "")
    file_path = request.args.get("file", "")
    selected_cmd_id = request.args.get("cmd", "")
    selected_step_id = request.args.get("step", "")
    right_tab = request.args.get("tab", "inspector")

    if workflow_name:
        data = _c().get("/api/visualize", workflow=workflow_name, cmd=selected_cmd_id or None)
    elif file_path:
        data = _c().get("/api/visualize", file=file_path, cmd=selected_cmd_id or None)
    else:
        data = {}

    workflows_data = _c().get("/api/workflows")

    section_map = {s["id"]: s for s in data.get("sections", []) if s.get("kind") not in ("special", "aspect")}
    insp_section = section_map.get(selected_step_id) if selected_step_id else None

    return render_template(
        "visualize.html",
        sections=data.get("sections", []),
        section_map=section_map,
        phases=data.get("phases", []),
        commands=data.get("commands", []),
        subcommands=data.get("subcommands", []),
        selected_cmd=data.get("selected_cmd"),
        flow_tree=data.get("flow_tree", []),
        aspects_by_target=data.get("aspects_by_target", {}),
        buckets=data.get("buckets", []),
        referenced_sections=data.get("referenced_sections", []),
        referenced_aspects=data.get("referenced_aspects", []),
        insp_section=insp_section,
        right_tab=right_tab,
        source_label=data.get("source_label", ""),
        workflow_name=workflow_name,
        workflow_obj=None,
        workflows_list=workflows_data.get("workflows", []),
    )


@app.route("/settings")
@app.route("/settings/<section>")
def settings(section: str = "secrets"):
    env_data = _c().get("/api/env")
    return render_template(
        "settings.html",
        section=section,
        secrets=_sp().list(),
        secrets_provider=_sp().info(),
        env_vars=env_data.get("env_vars", []),
        server_api=_c().base_url,
    )


# ---------------------------------------------------------------------------
# Search (proxied to API server, URLs rewritten to local)
# ---------------------------------------------------------------------------

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    results = _c().get("/api/search", q=q) if q else []
    for r in results:
        if r["type"] == "workflow":
            r["url"] = url_for("visualize", workflow=r["id"])
        elif r["type"] == "run":
            r["url"] = url_for("run_detail", run_id=r["id"])
    return jsonify(results)


# ---------------------------------------------------------------------------
# Action proxies — workflow/run actions forward to the API server
# ---------------------------------------------------------------------------

@app.route("/action/run/<workflow>", methods=["POST"])
def action_trigger_run(workflow: str):
    result = _c().post(f"/api/workflow/{workflow}/run")
    run_id = result.get("run_id")
    if run_id:
        return redirect(url_for("run_detail", run_id=run_id))
    abort(500)


@app.route("/action/cancel/<run_id>", methods=["POST"])
def action_cancel_run(run_id: str):
    _c().post(f"/api/runs/{run_id}/cancel")
    return redirect(url_for("run_detail", run_id=run_id))


# ---------------------------------------------------------------------------
# Secrets actions — handled locally via the secrets provider, not the API server
# ---------------------------------------------------------------------------

@app.route("/action/secrets", methods=["POST"])
def action_add_secret():
    _sp().set(
        name=request.form.get("name", "").strip(),
        value=request.form.get("value", "").strip(),
        scope_kind=request.form.get("scope_kind", "org"),
        scope_id=request.form.get("scope_id", ""),
    )
    return redirect(url_for("settings", section="secrets"))


@app.route("/action/secrets/<name>/delete", methods=["POST"])
def action_delete_secret(name: str):
    _sp().delete(name)
    return redirect(url_for("settings", section="secrets"))


@app.route("/action/secrets/auth", methods=["POST"])
def action_secrets_auth():
    try:
        _sp().authenticate(dict(request.form))
    except ValueError as e:
        return render_template(
            "settings.html",
            section="secrets",
            secrets=_sp().list(),
            secrets_provider=_sp().info(),
            secrets_auth_error=str(e),
            env_vars=[],
            server_api=_c().base_url,
        )
    return redirect(url_for("settings", section="secrets"))


# ---------------------------------------------------------------------------
# Env var actions — forwarded to the API server (env vars are run-scoped config)
# ---------------------------------------------------------------------------

@app.route("/action/env", methods=["POST"])
def action_add_env():
    data = {
        "name": request.form.get("name", ""),
        "value": request.form.get("value", ""),
        "scope_kind": request.form.get("scope_kind", "org"),
        "scope_id": request.form.get("scope_id", ""),
    }
    _c().post("/api/env", data)
    return redirect(url_for("settings", section="env"))


@app.route("/action/env/<int:var_id>/delete", methods=["POST"])
def action_delete_env(var_id: int):
    _c().delete(f"/api/env/{var_id}")
    return redirect(url_for("settings", section="env"))
