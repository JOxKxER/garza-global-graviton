"""
obs_overlay_server.py - Streamer Ad & Anti-Cheat OBS Overlay Server
Provides dynamic, transparent HTML browser source endpoints for YouTube & TikTok creators.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import db_manager as db

class OBSOverlayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/overlay":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Fetch latest security event and active sponsor ad
            events = db.get_recent_events(limit=1)
            latest_action = events[0]['action_taken'] if events else "All Nodes Secure (128-Tick)"
            
            ads = db.get_active_advertisements()
            current_ad = ads[0] if ads else {"company_name": "Garza Global Graviton", "ad_copy": "Secure 128-Tick Competitive Infrastructure"}

            html = f"""
            <html>
                <head>
                    <style>
                        body {{ background-color: transparent; color: #ffffff; font-family: monospace; margin: 20px; }}
                        .overlay-container {{ display: flex; flex-direction: column; gap: 10px; width: 380px; }}
                        .box {{ background: rgba(15, 23, 42, 0.90); border: 2px solid #3b82f6; padding: 12px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.6); }}
                        .title {{ color: #38bdf8; font-weight: bold; font-size: 13px; margin-bottom: 4px; }}
                        .status {{ color: #4ade80; font-size: 11px; }}
                        .sponsor-tag {{ color: #facc15; font-size: 11px; font-weight: bold; }}
                        .ad-text {{ color: #cbd5e1; font-size: 11px; margin-top: 2px; }}
                    </style>
                </head>
                <body>
                    <div class="overlay-container">
                        <!-- Anti-Cheat Status Box -->
                        <div class="box">
                            <div class="title">🛡️ INTEGRITY VAULT NODE</div>
                            <div class="status">Status: PROTECTED (128-Tick)</div>
                            <hr style="border-color: #334155; margin: 6px 0;">
                            <div style="font-size: 10px; color: #94a3b8;">{latest_action}</div>
                        </div>

                        <!-- Streamer Sponsor Ad Banner Box -->
                        <div class="box" style="border-color: #f59e0b;">
                            <div class="sponsor-tag">🌟 FEATURED COMMUNITY PARTNER</div>
                            <div class="title" style="color: #fef08a; margin-top: 2px;">{current_ad['company_name']}</div>
                            <div class="ad-text">{current_ad['ad_copy']}</div>
                        </div>
                    </div>
                </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_overlay_server():
    server = HTTPServer(('127.0.0.1', 8080), OBSOverlayHandler)
    print("🎥 OBS Stream Overlay & Ad Server running at http://localhost:8080/overlay")
    server.serve_forever()

if __name__ == "__main__":
    run_overlay_server()