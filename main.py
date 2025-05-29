from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# --------- Flexible: Journal-Einträge lesen ---------
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

    print("NOTION RESPONSE STATUS:", response.status_code)
    print("NOTION RESPONSE TEXT:", response.text)

    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    results = response.json().get("results", [])
    entries = []

    for result in results:
        props = result.get("properties", {})
        entry = {}

        # Lese alle Felder mit type rich_text (egal wie sie heißen)
        for field_name, prop in props.items():
            if prop.get("type") == "rich_text":
                texts = [r.get("plain_text", "") for r in prop["rich_text"]]
                entry[field_name] = " ".join(texts).strip()
            elif prop.get("type") == "title":
                texts = [r.get("plain_text", "") for r in prop["title"]]
                entry[field_name] = " ".join(texts).strip()
            elif prop.get("type") == "number":
                entry[field_name] = prop.get("number")
            elif prop.get("type") == "date":
                entry[field_name] = prop["date"]["start"] if prop.get("date") else ""
        entries.append(entry)

    return jsonify({"entries": entries}), 200

# --------- Journal-Eintrag speichern ---------
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
                    "text": {
                        "content": "GPT Journal Entry"
                    }
                }]
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

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=payload
    )

    print("SAVE TO NOTION STATUS:", response.status_code)
    print("SAVE TO NOTION RESPONSE:", response.text)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({"error": "Failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
