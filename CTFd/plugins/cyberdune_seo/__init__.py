"""Search discovery for the public CyberDune homepage."""
from flask import Response, request


PUBLIC_ORIGIN = "https://ctf.cyberdune.online"


def load(app):
    @app.route("/sitemap.xml", endpoint="cyberdune_sitemap")
    def sitemap():
        # Only advertise the public landing page, never accounts or challenges.
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{PUBLIC_ORIGIN}/</loc></url></urlset>\n"
        )
        return Response(xml, mimetype="application/xml")

    @app.after_request
    def search_headers(response):
        if request.endpoint == "views.robots" and response.status_code == 200:
            text = response.get_data(as_text=True)
            line = f"Sitemap: {PUBLIC_ORIGIN}/sitemap.xml"
            if line not in text.splitlines():
                response.set_data(text.rstrip() + "\n\n" + line + "\n")
        path = request.path.rstrip("/")
        if path in ("/login", "/register", "/reset_password", "/confirm", "/settings", "/team") or path.startswith(("/api/", "/admin/", "/reset_password/", "/confirm/")) or path == "/admin":
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
