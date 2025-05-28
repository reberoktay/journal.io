from flask import Flask, request, jsonify
import os
import requests
import openai

app = Flask(__name__)

# Lade Umgebungsvariablen
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# ROUTE: Journaleintrag in Notion speichern
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

# ROUTE: Letzte 5 Einträge lesen
@app.route("/read_entries", methods=["GET"])
def read_entries():
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "page_size": 5,
        "sorts": [{"property": "Datum", "direction": "descending"}]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch entries"}), 500

    entries = []
    for result in response.json().get("results", []):
        title = result["properties"]["Titel"]["title"][0]["text"]["content"] if result["properties"]["Titel"]["title"] else "Kein Titel"
        date = result["properties"]["Datum"]["date"]["start"] if "Datum" in result["properties"] else "Kein Datum"
        content = ""

        # Lese Inhalt aus dem ersten Paragraph-Block
        blocks_url = f"https://api.notion.com/v1/blocks/{result['id']}/children"
        blocks_response = requests.get(blocks_url, headers=headers)
        if blocks_response.status_code == 200:
            children = blocks_response.json().get("results", [])
            for block in children:
                if block["type"] == "paragraph":
                    texts = [t["text"]["content"] for t in block["paragraph"]["rich_text"]]
                    content = " ".join(texts)
                    break

        entries.append({
            "title": title,
            "date": date,
            "content": content
        })

    return jsonify(entries), 200

# ROUTE: GPT-Reflexion starten mit Kontext
@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        # Hole letzte 5 Einträge
        response = requests.get("http://localhost:3000/read_entries")
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch entries"}), 500
        entry_list = response.json()
    except Exception as e:
        return jsonify({"error": f"Fetch failed: {str(e)}"}), 500

    context = "\n\n".join([e["content"] for e in entry_list if e["content"]])

    system_prompt = f"""
Du bist Rebers täglicher Reflexions-Coach – klar, direkt, tiefgründig. Reber ist 21 Jahre alt, Unternehmer im Aufbau mit dem Ziel, bis 2030 ein Nettovermögen von 100 Millionen Euro aufzubauen. Er lebt nach einem disziplinierten System aus Spiritualität, Gym, Business, Reflexion und Iman.

Du analysierst vor Beginn die letzten 5 Journaleinträge:
{context}

Beginne dann mit: „Lass uns ehrlich sein – wie war dein Tag, Reber?“
"""

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start der Reflexion"}
        ]
    )

    return jsonify({"response": completion.choices[0].message["content"]}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
