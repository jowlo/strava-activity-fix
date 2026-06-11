"""OAuth2 callback server for initial token exchange."""

import http.server
import urllib.parse
import threading


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler to capture the OAuth callback."""

    code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization successful!</h1>"
                b"<p>You can close this window and return to the terminal.</p></body></html>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error: No code received.</h1></body></html>")

    def log_message(self, format, *args):
        pass  # Suppress request logs


def wait_for_code(port: int = 8000, timeout: int = 120) -> str | None:
    """Start a temporary HTTP server to capture the OAuth callback code."""
    server = http.server.HTTPServer(("0.0.0.0", port), OAuthCallbackHandler)
    server.timeout = timeout

    OAuthCallbackHandler.code = None

    def serve():
        while OAuthCallbackHandler.code is None:
            server.handle_request()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    server.server_close()

    return OAuthCallbackHandler.code
