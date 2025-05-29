from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 🔄 Einträge aus Notion abrufen – mit Debug-Ausgabe
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Standard = 5
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

    # 🔍 Debug-Ausgabe für Logs (zur Fehleranalyse)
    print("NOTION RESPONSE STATUS:", response.status_code)
    print("NOTION RESPONSE TEXT:", response.text)

    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    results = response.json().get("results", [])
    entries = []

    for result in results:
        entry_text = ""
        if "properties" in result:
            props = result["properties"]
            for key, prop in props.items():
                if prop.get("type") == "title":
                    entry_text += " ".join(t.get("plain_text", "") for t in prop.get("title", [])) + "\n"
                elif prop.get("type") == "rich_text":
                    entry_text += " ".join(t.get("plain_text", "") for t in prop.get("rich_text", [])) + "\n"
        entries.append(entry_text.strip())

    return jsonify({"entries": entries}), 200


# 📝 GPT-Journaleintrag in Notion speichern
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
