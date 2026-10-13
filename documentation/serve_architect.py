"""Serve documentation with shared assets on localhost port 1110."""
"python3 -m documentation.serve_architect"
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent


class DocumentationHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/architect/index.html")
            self.end_headers()
            return
        super().do_GET()


if __name__ == "__main__":
    handler = partial(DocumentationHandler, directory=str(DOCS_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 1110), handler)
    print("Serving http://127.0.0.1:1110/", flush=True)
    server.serve_forever()
