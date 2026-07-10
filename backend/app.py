import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

AGENT_RESOURCE_NAME = os.environ.get("AGENT_RESOURCE_NAME")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__, static_folder="../frontend", static_url_path="")

agent = None

try:
    from vertexai import agent_engines
    from vertexai import init as vertexai_init

    if GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION:
        vertexai_init(
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
        )

    if AGENT_RESOURCE_NAME:
        agent = agent_engines.get(AGENT_RESOURCE_NAME)

except Exception as e:
    print(f"Agent initialization failed: {e}")
    agent = None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)


def extract_text(value):
    try:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            parts = []

            if "content" in value:
                content = value["content"]

                if isinstance(content, dict) and "parts" in content:
                    for part in content["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            parts.append(part["text"])

                elif isinstance(content, str):
                    parts.append(content)

            for key in ("text", "message", "output", "result"):
                if key in value:
                    parts.append(extract_text(value[key]))

            if parts:
                return "\n".join([p for p in parts if p])

            return json.dumps(value)

        if isinstance(value, (list, tuple)):
            return "\n".join(extract_text(item) for item in value)

        if hasattr(value, "text"):
            return value.text

        if hasattr(value, "content"):
            return extract_text(value.content)

        return str(value)

    except Exception:
        return str(value)


def get_session_id(session):
    if isinstance(session, dict):
        return session.get("id") or session.get("name") or session.get("session_id")

    return (
        getattr(session, "id", None)
        or getattr(session, "name", None)
        or getattr(session, "session_id", None)
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)

    if not data or "code" not in data:
        return jsonify({"error": 'Missing "code" in request body.'}), 400

    code = data.get("code", "").strip()

    if not code:
        return jsonify({"error": "Code must not be empty."}), 400

    if not agent:
        return jsonify({
            "error": "Agent not initialized.",
            "detail": "Check AGENT_RESOURCE_NAME, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and Google authentication."
        }), 500

    prompt = (
        "Analyze this code for syntax, style, bugs, and functional issues. "
        "Give clear recommendations:\n\n"
        f"{code}"
    )

    try:
        user_id = f"web-user-{uuid.uuid4()}"

        session = agent.create_session(user_id=user_id)
        session_id = get_session_id(session)

        if not session_id:
            return jsonify({
                "error": "Could not determine session ID.",
                "detail": str(session)
            }), 500

        events = agent.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=prompt,
        )

        chunks = []

        for event in events:
            text = extract_text(event)
            if text:
                chunks.append(text)

        result = "\n".join(chunks).strip()

        if not result:
            result = "No readable response returned from agent."

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({
            "error": "Agent call failed",
            "detail": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)