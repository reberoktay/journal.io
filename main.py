from flask import Flask, request, jsonify
import os
import requests
import openai

app = Flask(__name__)

# Lade Umgebungsvariablen
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Setup für OpenAI
openai.api_key = OPENAI_API_KEY

# Hilfsfunktion: Letzte 5 Einträge aus Notion lesen
def get_last_journal_entries(limit=5):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "page_size": limit,
        "sorts": [{"property": "Datum", "direction": "descending"}]
    }
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    data = res.json()

    entries = []
    for result in data["results"]:
        props = result.get("properties", {})
        content = ""
        if "Text" in props and "rich_text" in props["Text"]:
            content = "".join([t.get("plain_text", "") for t in props["Text"]["rich_text"]])
        entries.append(content)

    return entries

# Route: GPT-Coach mit Kontext starten
@app.route("/reflect", methods=["POST"])
def reflect():
    last_entries = get_last_journal_entries()
    context = "\n\n".join(last_entries)

    system_prompt = f"""
Du bist Rebers täglicher Reflexions-Coach – klar, direkt, tiefgründig. Reber ist 21 Jahre alt, Unternehmer im Aufbau mit dem Ziel, bis 2030 ein Nettovermögen von 100 Millionen Euro aufzubauen. Er lebt nach einem disziplinierten System aus Spiritualität, Gym, Business, Reflexion und Iman.

Du analysierst vor Beginn die letzten 5 Journaleinträge:
{context}

Beginne dann mit: „Lass uns ehrlich sein – wie war dein Tag, Reber?“
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start der Reflexion"}
        ]
    )

    return jsonify({"response": response.choices[0].message["content"]}), 200

# Route: GPT-Antwort in Notion speichern
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
