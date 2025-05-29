from flask import Flask, request, jsonify
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Notion Konfiguration aus Umgebungsvariablen
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 🔁 Flexible Eintragsabfrage (Standard: letzte 5)
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Standard: 5 Einträge
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "page_size": limit,
        "sorts": [
            {
                "property": "Created time",
                "direction": "descending"
            }
        ]
    }

    response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    results = response.json().get("results", [])
    entries = []

    for result in results:
        content = []
        if "children" in result:
            for block in result["children"]:
                if block.get("type") == "paragraph":
                    texts = block["paragraph"].get("rich_text", [])
                    for t in texts:
                        content.append(t.get("plain_text", ""))
        else:
            # Fallback für Inhalt aus Titeln oder Properties
            props = result.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "rich_text":
                    for r in prop["rich_text"]:
                        content.append(r.get("plain_text", ""))

        entries.append(" ".join(content).strip())

    return jsonify({"entries": entries}), 200

# ✅ Speichern eines neuen Eintrags mit Bewertung + Datum
@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")
    rating = data.get("rating", 7)  # Optional, Standardbewertung = 7

    if not text:
        return jsonify({"error": "No text provided"}), 400

    today = datetime.now().strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Titel": {
                "title": [{
                    "text": {
                        "content": "GPT Journal Entry"
                    }
                }]
            },
            "Datum": {
                "date": {
                    "start": today
                }
            },
            "Bewertung": {
                "number": rating
            }
        },
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": text
                    }
                }]
            }
        }]
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({"error": "Failed to save to Notion"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
