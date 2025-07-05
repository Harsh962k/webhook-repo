from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client["webhookDB"]
collection = db["events"]

@app.route("/webhook", methods=["POST"])
def github_webhook():
    payload = request.json
    event = request.headers.get("X-GitHub-Event")

    if event == "push":
        author = payload["pusher"]["name"]
        branch = payload["ref"].split("/")[-1]
        timestamp = datetime.utcnow()

        entry = {
            "type": "push",
            "author": author,
            "to_branch": branch,
            "timestamp": timestamp
        }
        collection.insert_one(entry)
        return jsonify({"msg": "Push event stored"}), 200

    elif event == "pull_request":
        action = payload["action"]
        pr = payload["pull_request"]
        author = pr["user"]["login"]
        from_branch = pr["head"]["ref"]
        to_branch = pr["base"]["ref"]
        timestamp = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")

        if action == "opened":
            entry = {
                "type": "pull_request",
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }
            collection.insert_one(entry)
            return jsonify({"msg": "Pull request event stored"}), 200

        elif action == "closed" and pr.get("merged", False):
            entry = {
                "type": "merge",
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
            }
            collection.insert_one(entry)
            return jsonify({"msg": "Merge event stored"}), 200

    return jsonify({"msg": "Event not handled"}), 200

@app.route("/events", methods=["GET"])
def get_events():
    data = list(collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(20))
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
