import http.server
import urllib.request
import urllib.error


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
        if path == "/scans" and method == "POST":
            target = "http://scan-orchestrator:8080" + path
        elif path.startswith("/scans/") and method == "GET":
            target = "http://scan-status:8080" + path
        else:
            self._cors(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(target, data=body, method=method)
        req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        req.add_header("Authorization", self.headers.get("Authorization", ""))

        try:
            resp = urllib.request.urlopen(req, timeout=60)
            data = resp.read()
            status = resp.status
        except urllib.error.HTTPError as e:
            data = e.read()
            status = e.code

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 8000), Proxy).serve_forever()
