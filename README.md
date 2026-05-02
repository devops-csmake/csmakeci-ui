# csmakeci-ui

Browser UI for [csmakeci-server](../csmakeci-server). Runs as a separate Flask process that fetches data from the API server and renders server-side HTML — no Node.js, no build step.

## Requirements

- Python 3.9+
- A running [csmakeci-server](../csmakeci-server) instance

## Install

```sh
git clone https://github.com/your-org/csmakeci-ui
cd csmakeci-ui
pip install -e .
# or: uv sync
```

Dependencies: `flask`, `pyyaml` — installed automatically. No frontend toolchain needed.

## Without installing

```sh
cd csmakeci-ui
python -m csmakeci_ui serve --server-url http://127.0.0.1:8080

# or with uv, no prior sync needed
uv run python -m csmakeci_ui serve --server-url http://127.0.0.1:8080
```

## Quick start

```sh
# Point at a local csmakeci-server (default)
csmakeci-ui serve

# Point at a server running elsewhere
csmakeci-ui serve --server-url http://ci.internal:8080

# Change the UI port
csmakeci-ui serve --port 9001
```

On startup the UI server checks that the API server is reachable and prints both URLs:

```
csmakeci-ui 0.1.0
  UI server  : http://127.0.0.1:8081
  API server : http://127.0.0.1:8080  (csmakeci 0.1.0)
```

Then open `http://127.0.0.1:8081` in a browser.

## Running both together

```sh
# Terminal 1 — API server
cd ../csmakeci-server
csmakeci-server serve

# Terminal 2 — UI server
cd ../csmakeci-ui
csmakeci-ui serve --server-url http://127.0.0.1:8080
```

## CLI options

```
csmakeci-ui serve [options]

  --server-url URL   URL of the csmakeci-server API  (default: http://127.0.0.1:8080)
  --host HOST        Bind host for the UI server      (default: 127.0.0.1)
  --port PORT        Bind port for the UI server      (default: 8081)
  --debug            Enable Flask debug/reload mode
```

## Pages

| URL | Description |
|---|---|
| `/` | Dashboard — workflow cards, sparklines, recent runs |
| `/visualize?workflow=<name>` | Flow visualizer with step inspector |
| `/run/<id>` | Run detail — steps, live log stream, artifacts |
| `/settings` | Secrets, environment variables, runners |

**Search:** press `⌘K` / `Ctrl+K` from any page.

**Theme:** toggle between Paper (light) and Graphite (dark) with the button at the bottom of the sidebar. The preference is saved in `localStorage`.

## Secrets providers

The UI manages secrets directly — the API server has no secrets knowledge. Runtime access during builds is handled by csmakeci.

The provider is configured when starting the UI server. The default is `local`, which reads from the same directory csmake uses (`~/.csmake/secrets/`) so both tools share one store.

| Provider | Description |
|---|---|
| `local` | Plain files in `~/.csmake/secrets/` (default) |
| `vault` | HashiCorp Vault KV v2 — authenticates via token |

To use a different provider, pass `--secrets-type` and any provider-specific options (see `csmakeci-ui serve --help` once those flags are wired in), or configure it programmatically via `create_app(server_url, secrets_config={"type": "vault", "addr": "..."})`.

Adding a new provider means dropping a subclass of `BaseSecretsProvider` into `csmakeci_ui/secrets/` and registering it in `csmakeci_ui/secrets/__init__.py`. No changes to the server required.

## Architecture

The UI server is a thin proxy — it holds no state of its own:

```
Browser  ──HTMX/forms──►  csmakeci-ui (Flask, :8081)  ──urllib──►  csmakeci-server (:8080)
                                │
                                └──SSE logs──────────────────────────────────────────►  Browser
                                   (browser connects directly to the API server)
```

- Page navigation and form submissions go to the UI server, which fetches from the API and renders Jinja2 templates.
- Live run logs are streamed directly from the API server's SSE endpoint (`/run/<id>/stream`) — the browser opens that `EventSource` connection directly, so log streaming works even if the UI server restarts.
- Action routes (`/action/...`) on the UI server receive form POSTs and proxy them as JSON to the API server.

## Deploying behind a reverse proxy

The UI server is a standard Flask/WSGI app. Example with nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

If the UI and API servers are on different origins, the API server already sends CORS headers so the browser can connect to the SSE stream directly.
