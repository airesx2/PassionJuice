#=====RUNS ON FLASK=====

from flask import Flask, render_template_string, send_from_directory
import csv
import os
from datetime import datetime

app = Flask(__name__)

DEX_DIR = "dex"
LOG_FILE = os.path.join(DEX_DIR, "log.csv")

def format_timestamp(raw):
    try:
        dt = datetime.strptime(raw, "%Y%m%d_%H%M%S")
    except (ValueError, TypeError):
        return raw
    return dt.strftime("%b %d, %Y · %I:%M %p").replace(" 0", " ")

def load_catches():
    catches = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline = "") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["timestamp"] = format_timestamp(row.get("timestamp", ""))
                catches.append(row)
    return catches



# Serve the cropped images
@app.route("/dex/crops/<path:filename>")
def crops(filename):
    return send_from_directory(os.path.join(DEX_DIR, "crops"), filename)

@app.route("/")
def index():
    catches = load_catches()
    total = len(catches)

    cards = ""
    for c in catches:
        frame = os.path.basename(c.get("crop_file", ""))
        cards += f"""
        <div class = "card">
            <div class="img-wrap">
                <img src = "/dex/crops/{frame}" alt = "tree" >
                <span class="conf-pill">{c.get('confidence', '?')}%</span>
            </div>
            <div class="info">
                <div class = "species">𖠰 {c.get('species','tree').title() }</div>
                <div class = "time"> {c.get("timestamp", "")}</div>
            </div>
        </div>
        """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tree Dex</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: radial-gradient(circle at top, #a4bdb8, #7f9a94 70%);
                color: #e8f5e8;
                margin: 0;
                padding: 40px 20px 60px;
                min-height: 100vh;
            }}
            h1 {{
                text-align: center;
                font-size: 2.4em;
                letter-spacing: 2px;
                margin-bottom: 6px;
                color: #e8f5e8;
                text-shadow: 0 2px 6px rgba(0,0,0,0.25);
            }}
            .counter {{
                text-align: center;
                font-size: 1.15em;
                margin-bottom: 40px;
                color: #90ee90;
                letter-spacing: 0.5px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                gap: 22px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            .card {{
                background: linear-gradient(160deg, #bfd2cb, #b6cac3);
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 4px 14px rgba(0,0,0,0.28);
                border: 1px solid rgba(232,245,232,0.15);
                transition: transform 0.18s ease, box-shadow 0.18s ease;
            }}
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 22px rgba(0,0,0,0.35);
            }}
            .img-wrap {{ position: relative; }}
            .card img {{
                width: 100%;
                height: 150px;
                object-fit: cover;
                display: block;
            }}
            .conf-pill {{
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(30, 40, 35, 0.55);
                color: #90ee90;
                font-size: 0.75em;
                font-weight: 600;
                padding: 3px 9px;
                border-radius: 999px;
                backdrop-filter: blur(2px);
            }}
            .info {{ padding: 12px 14px 14px; }}
            .species {{
                font-weight: 600;
                font-size: 1.1em;
                color: #eef7ee;
                margin-bottom: 4px;
            }}
            .time {{ font-size: 0.75em; color: #dde7d4; opacity: 0.8; }}
            .empty {{
                text-align: center;
                color: #d7d9cb;
                font-size: 1.1em;
                grid-column: 1 / -1;
            }}
        </style>
    </head>
    <body>
        <h1>𖠰 Tree Dex</h1>
        <div class="counter">You've caught {total} trees!</div>
        <div class="grid">
            {cards if cards else '<p class="empty">No catches yet. Run detect.py to start collecting!</p>'}
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    app.run(debug=True, port=5000)
    