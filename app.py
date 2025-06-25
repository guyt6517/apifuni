from flask import Flask, request, jsonify
import requests
import re
import os
import datetime

app = Flask(__name__)

# Discord webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1387572462962872371/8pTu1S9rIYerUx1cuOgUwi5D5awQt08nKa9UUHQqfj0Cme6qjkb87jb9CTtJ2RbZYJDc")

# Regex for validating expected message format
message_pattern = re.compile(r"^\*\*(.+?)\*\* \(ID: (\d+)\) joined the game\.$")

# File to log rejected requests
LOG_FILE = "rejected_log.txt"

def is_valid_message_format(content):
    return bool(message_pattern.fullmatch(content))

def log_rejected(ip, payload, reason):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] IP: {ip}\n")
        f.write(f"Reason: {reason}\n")
        f.write(f"Payload: {payload}\n")
        f.write("-" * 40 + "\n")

@app.route("/", methods=["POST"])
def forward_to_webhook():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        data = request.get_json(force=True)

        # Missing content field
        if not data or "content" not in data:
            log_rejected(client_ip, data, "Missing 'content' field.")
            return jsonify({"error": "Missing 'content' field."}), 400

        content = data["content"]
        if not isinstance(content, str) or not is_valid_message_format(content):
            log_rejected(client_ip, data, "Invalid message format.")
            return jsonify({"error": "Invalid message format."}), 400

        # Build payload
        payload = {"content": content}
        for optional in ("username", "avatar_url"):
            if optional in data and isinstance(data[optional], str):
                payload[optional] = data[optional]

        # Forward to Discord
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if resp.status_code == 204:
            return jsonify({"status": "Message forwarded to Discord."}), 200
        else:
            return jsonify({
                "error": "Failed to post to Discord",
                "discord_status": resp.status_code,
                "discord_response": resp.text
            }), 500

    except Exception as e:
        log_rejected(client_ip, str(request.data), f"Exception: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "POST a valid join message to forward it to Discord."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
