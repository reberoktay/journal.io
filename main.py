from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route("/save", methods=["POST"])
def save_entry():
    data = request.get_json()
    text = data.get("text")

    if not text:
        return jsonify({"error": "No text provided"}), 400

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

    response = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({"error": "Failed to save"}), 500

@app.route("/read_entries", methods=["GET"])
def read_entries():
    try:
        limit = int(request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400

    query_payload = {
        "page_size": limit,
        "sorts": [{
            "property": "Created time",
            "direction": "descending"
        }]
    }

    query_response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=NOTION_HEADERS,
        json=query_payload
    )

    if query_response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    pages = query_response.json().get("results", [])
    full_entries = []

    for page in pages:
        page_id = page["id"]
        blocks_response = requests.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100",
            headers=NOTION_HEADERS
        )

        if blocks_response.status_code != 200:
            continue

        blocks = blocks_response.json().get("results", [])
        entry_text = []

        for block in blocks:
            rich_text = block.get(block["type"], {}).get("rich_text", [])
            for t in rich_text:
                entry_text.append(t.get("plain_text", ""))

        if entry_text:
            full_entries.append("\n".join(entry_text).strip())
        else:
            full_entries.append("(Kein Inhalt gefunden)")

    return jsonify({"entries": full_entries}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
