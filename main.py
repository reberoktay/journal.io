from flask import Flask, request, jsonify
import os
import requests
import datetime
import time

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 🔄 Einträge aus Notion lesen (Child Blocks)
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))

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
        print("❌ Fehler beim Query:", query_response.text)
        return jsonify({"error": "Failed to query Notion"}), 500

    results = query_response.json().get("results", [])
    entries = []

    for result in results:
        page_id = result.get("id")
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        block_response = requests.get(blocks_url, headers=headers)

        if block_response.status_code != 200:
            print(f"❌ Fehler bei Page {page_id}:", block_response.text)
            entries.append("[Fehler beim Laden]")
            continue

        blocks = block_response.json().get("results", [])
        content = []

        for block in blocks:
            block_type = block.get("type")
            if block_type and "text" in block.get(block_type, {}):
                for t in block[block_type].get("text", []):
                    content.append(t.get("plain_text", ""))

        full_text = "\n".join(content).strip()
        entries.append(full_text or "[Leer]")
        time.sleep(0.1)

    return jsonify({"entries": entries}), 200


# ✅ Eintrag in Notion speichern (inkl. Bewertung & Datum)
@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")
    rating = data.get("rating", 7)

    if not text:
        return jsonify({"error": "No text provided"}), 400

    today = datetime.date.today().isoformat()

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
        print("❌ Fehler beim Speichern:", response.text)
        return jsonify({"error": "Failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
