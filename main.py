from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 📥 Route: GPT-Eintrag in Notion speichern
@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")

    if not text:
        return jsonify({"error": "No text provided"}), 400

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
                    "text": { "content": "GPT Journal Entry" }
                }]
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
        return jsonify({"error": "Failed to save to Notion"}), 500

# 📤 Route: Beliebig viele Einträge abrufen (inkl. Fließtext)
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Default: 5
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    query_payload = {
        "page_size": limit,
        "sorts": [{
            "property": "Datum",
            "direction": "descending"
        }]
    }

    db_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    db_response = requests.post(db_url, headers=headers, json=query_payload)

    if db_response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    pages = db_response.json().get("results", [])
    entries = []

    for page in pages:
        entry = {}
        page_id = page["id"]

        # Titel aus Properties
        props = page.get("properties", {})
        title_prop = next((p for p in props.values() if p.get("type") == "title"), {})
        title_text = ""
        if "title" in title_prop:
            for part in title_prop["title"]:
                title_text += part["text"]["content"]
        entry["title"] = title_text

        # Datum (optional)
        if "Datum" in props and "date" in props["Datum"]:
            entry["date"] = props["Datum"]["date"]["start"]
        else:
            entry["date"] = None

        # Bewertung (optional)
        if "Bewertung" in props and "number" in props["Bewertung"]:
            entry["rating"] = props["Bewertung"]["number"]
        else:
            entry["rating"] = None

        # Page Content auslesen
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=headers)

        if blocks_response.status_code == 200:
            blocks = blocks_response.json().get("results", [])
            paragraphs = []
            for block in blocks:
                if block.get("type") == "paragraph":
                    for text in block["paragraph"].get("rich_text", []):
                        paragraphs.append(text.get("plain_text", ""))
            entry["content"] = "\n".join(paragraphs)
        else:
            entry["content"] = ""

        entries.append(entry)

    return jsonify({"entries": entries}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
