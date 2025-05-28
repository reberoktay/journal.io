from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# Helper: Hole die Textinhalte einer Seite (Body-Text)
def fetch_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return ""
    data = response.json()
    content_blocks = data.get("results", [])
    text_parts = []
    for block in content_blocks:
        if block.get("type") == "paragraph":
            texts = block.get("paragraph", {}).get("rich_text", [])
            for text in texts:
                plain = text.get("plain_text", "")
                if plain:
                    text_parts.append(plain)
    return "\n".join(text_parts).strip()

# Neue Route: Beliebig viele vollständige Einträge inkl. Body abrufen
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Standardmäßig 5
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

    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(query_url, headers=headers, json=query_payload)

    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    results = response.json().get("results", [])
    entries = []

    for result in results:
        page_id = result.get("id")
        title = "Unbenannt"
        if "Titel" in result["properties"]:
            title_data = result["properties"]["Titel"]["title"]
            if title_data:
                title = title_data[0]["plain_text"]

        body = fetch_page_content(page_id)
        full_text = f"# {title}\n\n{body}"
        entries.append(full_text)

    return jsonify({"entries": entries}), 200

# Bestehende Save-Route bleibt erhalten
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

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({"error": "Failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
