from flask import Flask, request, jsonify
import os
import requests
from datetime import datetime
import time
import json

app = Flask(__name__)

# Notion-Zugangsdaten aus Umgebungsvariablen
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 🔁 Einträge aus Notion abrufen (echter Seiteninhalt)
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Standard: 5 Einträge
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    query_payload = {
        "page_size": limit,
        "sorts": [
            {
                "property": "Created time",
                "direction": "descending"
            }
        ]
    }

    query_response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=headers,
        json=query_payload
    )

    if query_response.status_code != 200:
        print("Fehler bei der Abfrage der Datenbank:", query_response.text)
        return jsonify({"error": "Failed to query Notion"}), 500

    pages = query_response.json().get("results", [])
    entries = []

    for page in pages:
        page_id = page["id"]
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        block_response = requests.get(blocks_url, headers=headers)

        if block_response.status_code != 200:
            print(f"Fehler beim Laden der Page-Blocks: {page_id}")
            entries.append("[Fehler beim Laden dieses Eintrags]")
            continue

        blocks = block_response.json().get("results", [])
        text_parts = []

        for block in blocks:
            if block.get("type") == "paragraph":
                for rich in block["paragraph"].get("rich_text", []):
                    text_parts.append(rich.get("plain_text", ""))

        entry_text = "\n".join(text_parts).strip()
        entries.append(entry_text if entry_text else "[Leer]")

        time.sleep(0.2)  # Respektiere Rate-Limits

    return jsonify({"entries": entries}), 200

# ✅ Eintrag in Notion speichern
@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")
    rating = data.get("rating", 7)  # Optionaler Rating-Wert

    if not text:
        return jsonify({"error": "No text provided"}), 400

    today = datetime.now().strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": { "database_id": NOTION_DATABASE_ID },
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
        print("Fehler beim Speichern:", response.text)
        return jsonify({"error": "Failed to save to Notion"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
