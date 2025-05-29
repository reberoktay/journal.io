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

    # Dynamischer Titel: aus GPT oder aus erstem Satz fallback
    title = data.get("title")
    if not title:
        title = text.split(".")[0][:50]

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
                        "content": title
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
                    "text": {"content": text}
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
