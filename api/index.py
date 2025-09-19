import os
import requests
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

TMDB_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_KEY:
    raise SystemExit("⚠️ Please set TMDB_API_KEY environment variable")

TMDB_BASE = "https://api.themoviedb.org/3"

def fetch_tmdb(tmdb_id: int, media_type: str = "tv"):
    url = f"{TMDB_BASE}/{media_type}/{tmdb_id}"
    params = {
        "api_key": TMDB_KEY,
        "language": "en-US",
        "append_to_response": "credits,images,external_ids"
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.split('/')
        query_params = parse_qs(parsed_path.query)
        
        # Root endpoint
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "ok": True,
                "routes": [
                    "/api/anime/by-tmdb/<tmdb_id>?type=tv",
                    "/api/anime/by-tmdb/<tmdb_id>?type=movie"
                ],
                "env_required": ["TMDB_API_KEY"],
                "notes": [
                    "Uses TMDb API directly",
                    "Append '?type=tv' for anime series, '?type=movie' for anime films",
                    "Response includes titles, overview, episodes, genres, credits, images, external ids"
                ]
            }
            self.wfile.write(json.dumps(response).encode())
            return
        
        # API endpoint for TMDb lookup
        if parsed_path.path.startswith('/api/anime/by-tmdb/'):
            try:
                # Extract TMDB ID from path
                tmdb_id = int(path_parts[-1])
                
                # Get media type from query params
                media_type = query_params.get('type', ['tv'])[0]
                if media_type not in ("tv", "movie"):
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "type must be tv or movie"
                    }).encode())
                    return
                
                # Fetch data from TMDb
                data = fetch_tmdb(tmdb_id, media_type=media_type)
                if not data:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "matched": False, 
                        "message": "No TMDb match found"
                    }).encode())
                    return
                
                # Return successful response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "matched": True,
                    "tmdb_id": tmdb_id,
                    "tmdb_type": media_type,
                    "tmdb_data": data
                }).encode())
                
            except (ValueError, IndexError):
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Invalid TMDB ID format"
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Internal server error: {str(e)}"
                }).encode())
            return
        
        # Handle 404 for unknown routes
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "error": "Route not found"
        }).encode())
