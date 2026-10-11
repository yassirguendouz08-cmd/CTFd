"""Intentionally vulnerable training app: authorization trusts a role cookie."""
import os
from html import escape
from http.cookies import CookieError, SimpleCookie
from wsgiref.simple_server import make_server


def create_app(flag):
    if not flag:
        raise ValueError("FLAG must be provided by the instance launcher")

    def application(environ, start_response):
        cookies = SimpleCookie()
        try:
            cookies.load(environ.get("HTTP_COOKIE", ""))
        except CookieError:
            cookies.clear()
        role = cookies["role"].value if "role" in cookies else "guest"
        path = environ.get("PATH_INFO", "/")
        headers = [("Content-Type", "text/html; charset=utf-8"),
                   ("Cache-Control", "no-store"),
                   ("X-Content-Type-Options", "nosniff")]
        status = "200 OK"
        if path == "/robots.txt":
            headers[0] = ("Content-Type", "text/plain; charset=utf-8")
            content = "User-agent: *\nDisallow: /admin\n"
        elif path == "/":
            if "role" not in cookies:
                headers.append(("Set-Cookie", "role=guest; Path=/; SameSite=Lax"))
            content = page("Cookie Mirage", "Welcome to the CyberDune staff portal.",
                           '<p>Current role: <code>' + escape(role) + '</code></p>'
                           '<a href="/admin">Open the admin vault →</a>')
        elif path == "/admin":
            # This is the challenge's intentional access-control vulnerability.
            if role == "admin":
                content = page("Admin vault", "Access granted.",
                               "<p>Your instance flag:</p><code>" + escape(flag) + "</code>")
            else:
                status = "403 Forbidden"
                content = page("Access denied", "Only administrators can open this vault.",
                               '<a href="/">Back to portal</a>')
        else:
            status = "404 Not Found"
            content = page("Not found", "This page does not exist.", '<a href="/">Home</a>')
        body = content.encode("utf-8")
        headers.append(("Content-Length", str(len(body))))
        start_response(status, headers)
        return [body]

    return application


def page(title, subtitle, content):
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cookie Mirage · CyberDune</title><style>
body{background:#09090b;color:#fafafa;font:18px system-ui;margin:0;min-height:100vh;
display:grid;place-items:center}main{margin:24px;padding:40px;max-width:600px;
border:1px solid #dc262650;border-radius:12px;background:#18181b}
small,a{color:#f87171}h1{font-size:42px}p{color:#a1a1aa;line-height:1.6}
code{color:#fafafa;overflow-wrap:anywhere}a{display:inline-block;margin-top:24px}
</style><main><small>CYBERDUNE / STAFF PORTAL</small><h1>""" + escape(title) + \
        "</h1><p>" + escape(subtitle) + "</p>" + content + "</main></html>"


if __name__ == "__main__":
    app = create_app(os.environ.get("FLAG", ""))
    with make_server("0.0.0.0", 8080, app) as server:
        server.serve_forever()
