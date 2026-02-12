from flask import Flask, render_template_string
from threading import Thread
import os
import psycopg2
from datetime import datetime

app = Flask('')

def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# --- HTML CSS STYLES (Simple Dark Mode) ---
STYLE = """
<style>
    body { font-family: sans-serif; background-color: #2c2f33; color: #ffffff; padding: 20px; }
    h1 { color: #7289da; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #23272a; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #99aab5; }
    th { background-color: #7289da; color: white; }
    tr:hover { background-color: #2c2f33; }
    .card { background-color: #23272a; border: 1px solid #7289da; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
    img { max-width: 100%; border-radius: 5px; margin-top: 10px; }
    .date { color: #99aab5; font-size: 0.9em; }
    a { color: #7289da; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
    .nav { margin-bottom: 20px; }
</style>
"""

@app.route('/')
def home():
    return f"{STYLE}<h1>I'm Alive!</h1><div class='nav'><a href='/dates'>View Date Ideas</a> | <a href='/memories'>View Memories</a></div>"

@app.route('/dates')
def dates():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT category, idea, completed FROM date_ideas ORDER BY category')
    dates = cur.fetchall()
    cur.close()
    conn.close()
    
    html = f"{STYLE}<h1>Date Ideas</h1><div class='nav'><a href='/'>Home</a> | <a href='/memories'>Memories</a></div>"
    html += "<table><tr><th>Category</th><th>Idea</th><th>Status</th></tr>"
    
    for category, idea, completed in dates:
        status = "Done" if completed else "To Do"
        html += f"<tr><td>{category}</td><td>{idea}</td><td>{status}</td></tr>"
    
    html += "</table>"
    return html

@app.route('/memories')
def memories():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT content, image_url, date_added FROM memories ORDER BY date_added DESC')
    memories = cur.fetchall()
    cur.close()
    conn.close()

    html = f"{STYLE}<h1>Memories</h1><div class='nav'><a href='/'>Home</a> | <a href='/dates'>Date Ideas</a></div>"
    
    for content, image_url, date_added in memories:
        date_str = date_added.strftime('%Y-%m-%d') if date_added else "Unknown Date"
        img_html = f"<br><img src='{image_url}' width='300'>" if image_url else ""
        text = content if content else "Image Memory"
        
        html += f"""
        <div class="card">
            <div class="date">{date_str}</div>
            <p>{text}</p>
            {img_html}
        </div>
        """
    return html

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()