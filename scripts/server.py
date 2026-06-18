import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from audit_engine import analyze_contract


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI_DIR = os.path.join(ROOT_DIR, "ui")


class AuditorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            self.write_json({
                "ok": True,
                "engine": "genlayer-auditor-live",
            })
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/audit":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self.send_error(400, "Request body is required")
                return

            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            contract_name = str(payload.get("contractName") or "SubmittedContract.py").strip()
            source = str(payload.get("contractSource") or "")

            if not source.strip():
                self.send_error(400, "contractSource is required")
                return

            self.write_json(analyze_contract(contract_name, source))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as exc:
            self.send_error(500, f"Audit failed: {exc}")

    def write_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    host = os.environ.get("GENLAYER_AUDITOR_HOST", "127.0.0.1")
    port = int(os.environ.get("GENLAYER_AUDITOR_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), AuditorHandler)
    print(f"GenLayer Auditor live at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
