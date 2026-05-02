"""CLI: csmakeci-ui serve"""
from __future__ import annotations

import argparse
import sys


def main():
    ap = argparse.ArgumentParser(
        prog="csmakeci-ui",
        description="csmakeci-ui — web UI for a csmakeci-server instance",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="Start the UI server")
    p_serve.add_argument("--server-url", default="http://127.0.0.1:8080",
                         metavar="URL",
                         help="URL of the csmakeci-server API (default: http://127.0.0.1:8080)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8081)
    p_serve.add_argument("--debug", action="store_true")

    args = ap.parse_args()

    if args.cmd == "serve":
        _cmd_serve(args)


def _cmd_serve(args):
    from csmakeci_ui import server

    # Verify server reachability before starting
    from csmakeci_ui.client import ServerClient
    client = ServerClient(args.server_url, timeout=3)
    try:
        status = client.get("/api/status")
        version = status.get("version", "?")
        print(f"csmakeci-ui 0.1.0")
        print(f"  UI server  : http://{args.host}:{args.port}")
        print(f"  API server : {args.server_url}  (csmakeci {version})")
        print()
    except Exception as e:
        print(f"Warning: cannot reach API server at {args.server_url}: {e}", file=sys.stderr)
        print(f"  Starting UI anyway — pages will show errors until the server is reachable.")
        print()

    app = server.create_app(args.server_url)
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
