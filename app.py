from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["webhooks"]
collection = db["events"]

@app.route('/')
def index():
    events = list(collection.find().sort("timestamp", -1).limit(10))
    return render_template("index.html", events=events)

@app.route('/webhook', methods=['POST'])
def github_webhook():
    payload = request.json
    event_type = request.headers.get("X-GitHub-Event")
    timestamp = datetime.utcnow()

    data = {
        "timestamp": timestamp,
        "event_type": event_type
    }

    if event_type == "push":
        data["author"] = payload["pusher"]["name"]
        data["to_branch"] = payload["ref"].split("/")[-1]

    elif event_type == "pull_request":
        action = payload["action"]
        is_merged = payload["pull_request"].get("merged", False)

        if is_merged and action == "closed":
            data["author"] = payload["pull_request"]["merged_by"]["login"]
            data["from_branch"] = payload["pull_request"]["head"]["ref"]
            data["to_branch"] = payload["pull_request"]["base"]["ref"]
            data["event_type"] = "merge"
        else:
            data["author"] = payload["pull_request"]["user"]["login"]
            data["from_branch"] = payload["pull_request"]["head"]["ref"]
            data["to_branch"] = payload["pull_request"]["base"]["ref"]

    else:
        return jsonify({"msg": "Unhandled event"}), 400

    collection.insert_one(data)
    return jsonify({"msg": "Event stored"}), 200

@app.route('/api/events')
def get_events():
    events = list(collection.find().sort("timestamp", -1).limit(10))
    for e in events:
        e["_id"] = str(e["_id"])
        e["timestamp"] = e["timestamp"].strftime("%d %b %Y - %I:%M %p UTC")
    return jsonify(events)

if __name__ == "__main__":
    app.run(debug=True)
