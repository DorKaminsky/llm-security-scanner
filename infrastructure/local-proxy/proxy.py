import http.server
import urllib.request
import urllib.error
import json


LAMBDA_INVOKE = "/2015-03-31/functions/function/invocations"


def _invoke_lambda(host: str, method: str, path: str, headers, body: bytes | None) -> tuple[int, bytes]:
    """Wrap an HTTP request as an API Gateway event and invoke the Lambda RIE."""
    event = {
        "httpMethod": method,
        "path": path,
        "headers": dict(headers),
        "pathParameters": {},
        "queryStringParameters": {},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": "local-user-id"}
            }
        },
        "body": body.decode() if body else None,
    }
    # Extract path params for /scans/{scan_id}
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "scans":
        event["pathParameters"]["scan_id"] = parts[1]

    payload = json.dumps(event).encode()
    req = urllib.request.Request(
        f"http://{host}{LAMBDA_INVOKE}",
        data=payload,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result.get("statusCode", 200), result.get("body", "{}").encode()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        self._proxy("POST")

    def do_GET(self):
        self._proxy("GET")

    def do_OPTIONS(self):
        self._cors(200)

    def _cors(self, code):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def _proxy(self, method):
        path = self.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        if path == "/scans" and method == "POST":
            host = "scan-orchestrator:8080"
        elif path.startswith("/scans/") and method == "GET":
            host = "scan-status:8080"
        else:
            self._cors(404)
            return

        status, data = _invoke_lambda(host, method, path, self.headers, body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 8000), Proxy).serve_forever()

