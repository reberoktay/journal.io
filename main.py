from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# === Einträge flexibel lesen ===
@app.route("/read_entries", methods=["GET"])
def read_entries():
    limit = int(request.args.get("limit", 5))  # Default = 5
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

    # Debugging: Gib Status und Inhalt der Notion-Antwort aus!
    print("NOTION RESPONSE STATUS:", response.status_code)
    print("NOTION RESPONSE TEXT:", response.text)

    if response.status_code != 200:
        return jsonify({"error": "Failed to query Notion"}), 500

    results = response.json().get("results", [])
    entries = []

    for result in results:
        entry = {}
        # Titel, Datum und Bewertung abrufen, falls vorhanden:
        props = result.get("properties", {})
        # Titel
        title_data = props.get("Titel", {}).get("title", [])
        entry["title"] = title_data[0]["plain_text"] if title_data else ""
        # Datum
        date_data = props.get("Datum", {}).get("date", {})
        entry["date"] = date_data.get("start", "")
        # Bewertung
        rating_data = props.get("Bewertung", {}).get("number", None)
        entry["rating"] = rating_data if rating_data is not None else ""
        # Optional: KI-Zusammenfassung, falls du sie als property hast:
        summary_data = props.get("KI-Zusammenfassung", {}).get("rich_text", [])
        entry["summary"] = summary_data[0]["plain_text"] if summary_data else ""
        entries.append(entry)

    return jsonify({"entries": entries}), 200

# === Eintrag speichern ===
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
    print("NOTION SAVE RESPONSE STATUS:", response.status_code)
    print("NOTION SAVE RESPONSE TEXT:", response.text)

    if response.status_code in [200, 201]:
        return jsonify({"message": "Saved to Notion!"}), 200
    else:
        return jsonify({"error": "Failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
