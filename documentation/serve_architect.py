"""Serve the architect HTML documentation on localhost port 1110."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent / "architect"


if __name__ == "__main__":
    handler = partial(SimpleHTTPRequestHandler, directory=str(DOCS_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 1110), handler)
    print("Serving http://127.0.0.1:1110/", flush=True)
    server.serve_forever()
