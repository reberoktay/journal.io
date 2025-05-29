from flask import Flask, request, jsonify
import os
import requests
from datetime import datetime

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 📥 Journaleintrag speichern
@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")
    rating = data.get("rating", 7)
    date = datetime.today().strftime('%Y-%m-%d')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # 📌 Titel dynamisch aus dem ersten Satz (max. 50 Zeichen)
    title_text = text.strip().split(".")[0][:50]

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
                        "content": title_text or "GPT Journal Entry"
                    }
                }]
            },
            "Datum": {
                "date": {"start": date}
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
                    "text": { "content": text }
                }]
            }
        }]
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({
            "error": "Failed to save",
            "status": response.status_code,
            "response": response.text
        }), 500

# 📤 Journaleinträge lesen
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "page_size": limit,
        "sorts": [{
            "property": "Datum",
            "direction": "descending"
        }]
    }

    query_response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=headers,
        json=payload
    )

    if query_response.status_code != 200:
        return jsonify({
            "error": "Failed to query Notion",
            "status": query_response.status_code,
            "response": query_response.text
        }), 500

    results = query_response.json().get("results", [])
    entries = []

    for result in results:
        # Inhalte aus der Seite lesen
        page_id = result["id"]
        blocks_response = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers
        )
        if blocks_response.status_code == 200:
            blocks = blocks_response.json().get("results", [])
            text_content = []
            for block in blocks:
                if block["type"] == "paragraph":
                    for rich_text in block["paragraph"]["rich_text"]:
                        text_content.append(rich_text.get("plain_text", ""))
            entries.append(" ".join(text_content).strip())

    return jsonify({"entries": entries}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
