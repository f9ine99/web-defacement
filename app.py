from flask import Flask, render_template, request, session
from flask_session import Session
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import difflib

app = Flask(__name__)

# Configure Flask-Session to use filesystem-based sessions
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Function to fetch website info
def fetch_website_info(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            textual_content = soup.get_text()
            dom_tree = soup.prettify()
            content_length = len(response.text)
            return {
                "textual_content": textual_content,
                "dom_tree": dom_tree,
                "content_length": content_length
            }
        else:
            return None
    except Exception as e:
        return None

# Function to create baseline
def create_baseline(url, info):
    domain_name = url.split('//')[-1].split('/')[0].replace('.', '_')
    json_file_path = os.path.join('baseline', f'{domain_name}_baseline.json')
    if os.path.exists(json_file_path):
        pass
    else:
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(info, json_file, ensure_ascii=False, indent=4)

# Function to compare with baseline
def compare_with_baseline(url, current_info):
    domain_name = url.split('//')[-1].split('/')[0].replace('.', '_')
    baseline_json_path = os.path.join('baseline', f'{domain_name}_baseline.json')
    if os.path.exists(baseline_json_path):
        with open(baseline_json_path, 'r', encoding='utf-8') as baseline_file:
            baseline_info = json.load(baseline_file)
        textual_content_changed = current_info['textual_content'] != baseline_info['textual_content']
        dom_changed = current_info['dom_tree'] != baseline_info['dom_tree']
        content_length_changed = current_info['content_length'] != baseline_info['content_length']
        changes = []
        if textual_content_changed:
            changes.append("Textual content has changed.")
            changes.extend(list(difflib.unified_diff(baseline_info['textual_content'].splitlines(), current_info['textual_content'].splitlines())))
        if dom_changed:
            changes.append("DOM structure has changed.")
            changes.extend(list(difflib.unified_diff(baseline_info['dom_tree'].splitlines(), current_info['dom_tree'].splitlines())))
        if content_length_changed:
            changes.append("Content length has changed.")
        return changes
    else:
        return ["Baseline file does not exist. Please create a baseline first."]

# Function to check if a website is alive
def check_website_alive(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False

@app.route("/", methods=["GET", "POST"])
def index():
    if 'website_info' not in session:
        session['website_info'] = None

    if request.method == "POST":
        url = request.form["url"]
        current_info = fetch_website_info(url)
        website_status = "Alive" if check_website_alive(url) else "Down"

        if current_info:
            create_baseline(url, current_info)
            changes = compare_with_baseline(url, current_info)
            session['website_info'] = current_info
            return render_template("monitor.html", changes=changes, website_info=session['website_info'], website_status=website_status)
        else:
            changes = ["Failed to fetch the webpage."]
            return render_template("monitor.html", changes=changes, website_info=session['website_info'], website_status=website_status)

    return render_template("monitor.html", changes=[], website_info=session['website_info'], website_status=None)

if __name__ == "__main__":
    if not os.path.exists('baseline'):
        os.mkdir('baseline')
    app.run(debug=True)
