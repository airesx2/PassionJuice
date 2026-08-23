#=====RUNS ON FLASK=====
#displaying data

from flask import Flask, send_from_directory, request
import csv
import os
from datetime import datetime

from assessment.climate import get_site_climate_profile

app = Flask(__name__) #create webapp obj

#nav bar html snippet
NAV = """ 
<div class="nav">
    <a href="/">Tree Dex</a>
    <a href="/planting">Planting Recs</a>
</div>
"""

DEX_DIR = "dex"
LOG_FILE = os.path.join(DEX_DIR, "log.csv")


def format_timestamp(raw):
    """parse timestamp string from log.csv

    Args:
        raw (str): timestamp string from log.csv

    Returns:
        str: readable timestamp
    """
    try:
        dt = datetime.strptime(raw, "%Y%m%d_%H%M%S")
    except (ValueError, TypeError): 
        return raw
    return dt.strftime("%b %d, %Y · %I:%M %p").replace(" 0", " ")

def load_catches():
    """turn csv row into dict key by header row col name

    Returns:
        list[dict]: List of catch dictionaries
    """
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
                <div class = "species">🌳 {c.get('species','tree').title() }</div>
                <div class = "time"> {c.get("timestamp", "")}</div>
            </div>
        </div>
        """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title> ݁ ˖𓂃.𖠰 Tree Dex</title>
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
            .nav {{
                display: flex;
                justify-content: center;
                gap: 18px;
                margin-bottom: 20px;
            }}
            .nav a {{
                color: #e8f5e8;
                text-decoration: none;
                font-size: 0.95em;
                padding: 6px 14px;
                border-radius: 999px;
                background: rgba(0,0,0,0.15);
            }}
            .nav a:hover {{ background: rgba(0,0,0,0.3); }}
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
        {NAV}
        <h1> ݁ ˖𓂃.𖠰 Tree Dex</h1>
        <div class="counter">You've caught {total} trees!</div>
        <div class="grid">
            {cards if cards else '<p class="empty">No catches yet. Run detect.py to start collecting!</p>'}
        </div>
    </body>
    </html>
    """
    return html

@app.route("/planting")
def planting():
    zip_code = request.args.get("zip", "").strip()
    result_html = ""

    if zip_code:
        try:
            profile = get_site_climate_profile(zip_code)
            result_html = f"""
            <div class="profile">
                <div class="stat"><span>Hardiness Zone</span><strong>{profile['hardiness_zone']}</strong></div>
                <div class="stat"><span>Avg Temp</span><strong>{profile['avg_temp_c']}&deg;C</strong></div>
                <div class="stat"><span>Avg Annual Rainfall</span><strong>{profile['avg_annual_precip_mm']:.0f} mm</strong></div>
                <div class="stat"><span>Coordinates</span><strong>{profile['lat']:.3f}, {profile['lon']:.3f}</strong></div>
            </div>
            <p class="hint">Raw data for now &mdash; turning this into an actual planting recommendation is next.</p>
            """
        except RuntimeError as e:
            result_html = f'<p class="error">{e}</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tree Dex &middot; Planting Recs</title>
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
            h1 {{ text-align: center; font-size: 2em; margin-bottom: 20px; text-shadow: 0 2px 6px rgba(0,0,0,0.25); }}
            .nav {{ display: flex; justify-content: center; gap: 18px; margin-bottom: 20px; }}
            .nav a {{ color: #e8f5e8; text-decoration: none; font-size: 0.95em; padding: 6px 14px; border-radius: 999px; background: rgba(0,0,0,0.15); }}
            .nav a:hover {{ background: rgba(0,0,0,0.3); }}
            form {{ text-align: center; margin-bottom: 30px; }}
            input {{ padding: 8px 12px; border-radius: 8px; border: none; font-size: 1em; width: 160px; }}
            button {{ padding: 8px 16px; border-radius: 8px; border: none; background: #4a7a68; color: white; font-size: 1em; margin-left: 8px; cursor: pointer; }}
            button:hover {{ background: #3d6a58; }}
            .profile {{ max-width: 500px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
            .stat {{ background: rgba(0,0,0,0.15); border-radius: 10px; padding: 14px; text-align: center; }}
            .stat span {{ display: block; font-size: 0.8em; opacity: 0.8; margin-bottom: 4px; }}
            .stat strong {{ font-size: 1.3em; }}
            .hint {{ text-align: center; margin-top: 20px; opacity: 0.8; font-size: 0.9em; }}
            .error {{ text-align: center; color: #ffb3b3; }}
        </style>
    </head>
    <body>
        {NAV}
        <h1>🌱 ⊹ ࣪ ˖ Planting Recommendations</h1>
        <form method="get">
            <input type="text" name="zip" placeholder="ZIP code" value="{zip_code}">
            <button type="submit">Look up</button>
        </form>
        {result_html}
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    app.run(debug=True, port=5000)
    