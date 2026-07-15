import os
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

# Load backend/.env next to this file; override=True so shell placeholders lose.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

AGENT_RESOURCE_NAME = (os.environ.get("AGENT_RESOURCE_NAME") or "").strip()
GOOGLE_CLOUD_PROJECT = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
GOOGLE_CLOUD_LOCATION = (os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1").strip()
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__, static_folder="../frontend", static_url_path="")

code_agent = None

try:
    from vertexai import agent_engines
    from vertexai import init as vertexai_init

    if not GOOGLE_CLOUD_PROJECT or not AGENT_RESOURCE_NAME:
        raise RuntimeError(
            "Missing GOOGLE_CLOUD_PROJECT or AGENT_RESOURCE_NAME after loading .env"
        )

    vertexai_init(
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
    )
    code_agent = agent_engines.get(AGENT_RESOURCE_NAME)

except Exception as e:
    print(f"Agent initialization failed: {e}")
    code_agent = None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# Helpers: pull user-facing text from stream events (never dump raw event JSON).


def _as_dict(value):
    """Normalize SDK objects / dicts into a plain dict when possible."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(exclude_none=True)
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {
            k: v
            for k, v in vars(value).items()
            if not k.startswith("_") and v is not None
        }
    return None


def _part_text(part):
    """Return text from a content part, skipping tool/function payloads."""
    if part is None:
        return ""
    if isinstance(part, str):
        return part

    data = _as_dict(part) or {}
    if not isinstance(data, dict):
        return getattr(part, "text", None) or ""

    # Skip tool/function payloads — not user-facing prose.
    skip_keys = (
        "function_call",
        "functionCall",
        "function_response",
        "functionResponse",
        "executable_code",
        "executableCode",
        "code_execution_result",
        "codeExecutionResult",
        "inline_data",
        "inlineData",
        "file_data",
        "fileData",
    )
    if any(data.get(k) for k in skip_keys):
        return ""

    text = data.get("text")
    if text is None:
        text = getattr(part, "text", None)
    return text if isinstance(text, str) else ""


def _content_texts(content):
    """Collect text strings from an ADK/Vertex content object."""
    if content is None:
        return []

    if isinstance(content, str):
        return [content] if content.strip() else []

    data = _as_dict(content) or {}
    parts = None
    if isinstance(data, dict):
        parts = data.get("parts")
    if parts is None:
        parts = getattr(content, "parts", None)

    if not parts:
        return []

    texts = []
    for part in parts:
        text = _part_text(part)
        if text and text.strip():
            texts.append(text)
    return texts


def _event_author(event, data):
    author = None
    if isinstance(data, dict):
        author = data.get("author") or data.get("role")
    if author is None:
        author = getattr(event, "author", None) or getattr(event, "role", None)
    return (author or "").strip().lower()


def _event_partial(event, data):
    if isinstance(data, dict) and "partial" in data:
        return bool(data.get("partial"))
    return bool(getattr(event, "partial", False))


def _has_tool_activity(data):
    """True when the event is primarily a tool call/response, not final prose."""
    if not isinstance(data, dict):
        return False

    content = data.get("content") or {}
    parts = []
    if isinstance(content, dict):
        parts = content.get("parts") or []
    elif hasattr(content, "parts"):
        parts = content.parts or []

    for part in parts:
        part_data = _as_dict(part) or {}
        if not isinstance(part_data, dict):
            continue
        if any(
            part_data.get(k)
            for k in (
                "function_call",
                "functionCall",
                "function_response",
                "functionResponse",
            )
        ):
            return True
    return False


def extract_event_text(event):
    """Return (user-facing text, is_final) from a stream event. Never json.dumps the event."""
    data = _as_dict(event)

    if isinstance(event, str):
        return event, True

    author = _event_author(event, data)
    if author in ("user", "system"):
        return "", False

    content = None
    if isinstance(data, dict):
        content = data.get("content")
    if content is None:
        content = getattr(event, "content", None)

    texts = _content_texts(content)

    if not texts and isinstance(data, dict):
        for key in ("text", "output", "message", "result"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value)
            elif value is not None and key != "text":
                texts.extend(_content_texts(value))

    if not texts:
        return "", False

    text = "\n".join(t for t in texts if t).strip()
    if not text:
        return "", False

    is_final = (not _event_partial(event, data)) and (not _has_tool_activity(data))
    return text, is_final


def collect_agent_response(events):
    """Prefer the last complete model message; merge partials if needed."""
    final_texts = []
    partial_texts = []

    for event in events:
        text, is_final = extract_event_text(event)
        if not text:
            continue
        if is_final:
            final_texts.append(text)
        else:
            partial_texts.append(text)

    if final_texts:
        return final_texts[-1].strip()

    if partial_texts:
        merged = partial_texts[0]
        for chunk in partial_texts[1:]:
            if chunk.startswith(merged):
                merged = chunk
            elif merged.endswith(chunk):
                continue
            else:
                merged += chunk
        return merged.strip()

    return ""


def get_session_id(session):
    if isinstance(session, dict):
        return session.get("id") or session.get("name") or session.get("session_id")

    return (
        getattr(session, "id", None)
        or getattr(session, "name", None)
        or getattr(session, "session_id", None)
    )


def query_agent(user_id, session_id, message):
    """Run one stream_query and return readable text."""
    events = code_agent.stream_query(
        user_id=user_id,
        session_id=session_id,
        message=message,
    )
    return collect_agent_response(events) or ""


def build_review_prompt(code):
    return (
        "Analyze this code for syntax, style, bugs, and functional issues. "
        "Give a clear assessment, key findings, and recommendations.\n\n"
        f"{code}"
    )


def build_fix_prompt(code, review):
    """
    Second-pass prompt inspired by fix_pipeline/code_fixer.py:
    produce a complete fixed version after the review.
    """
    return (
        "You are an expert code fixing specialist.\n\n"
        "Original code:\n"
        f"```\n{code}\n```\n\n"
        "Your prior analysis:\n"
        f"{review}\n\n"
        "Based on that analysis, fix ALL identified issues "
        "(bugs, logic errors, style, missing docs, brittle error handling).\n\n"
        "Respond in this exact markdown structure:\n\n"
        "## Complete Fixed Code\n"
        "Provide the full corrected source in a single fenced code block.\n\n"
        "## What Was Fixed\n"
        "Brief bullet list of each change.\n\n"
        "If the original code is already fine, say so under What Was Fixed "
        "and repeat the original code under Complete Fixed Code."
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)

    if not data or "code" not in data:
        return jsonify({"error": 'Missing "code" in request body.'}), 400

    code = data.get("code", "").strip()

    if not code:
        return jsonify({"error": "Code must not be empty."}), 400

    if code_agent is None:
        return jsonify({
            "error": "Agent not initialized.",
            "detail": (
                "Check AGENT_RESOURCE_NAME, GOOGLE_CLOUD_PROJECT, "
                "GOOGLE_CLOUD_LOCATION, and Google authentication."
            ),
        }), 500

    try:
        user_id = f"web-user-{uuid.uuid4()}"
        session = code_agent.create_session(user_id=user_id)
        session_id = get_session_id(session)

        if not session_id:
            return jsonify({
                "error": "Could not determine session ID.",
                "detail": str(session)
            }), 500

        # 1) Review (existing behavior)
        review = query_agent(user_id, session_id, build_review_prompt(code))
        if not review:
            review = "No readable review returned from agent."

        # 2) Fix pass (from fix_pipeline idea): same session, produce fixed code
        fix_section = query_agent(
            user_id, session_id, build_fix_prompt(code, review)
        )
        if not fix_section:
            fix_section = (
                "## Complete Fixed Code\n"
                "Could not generate a fixed version.\n"
            )

        result = (
            f"{review.strip()}\n\n"
            "---\n\n"
            f"{fix_section.strip()}"
        )
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({
            "error": "Agent call failed",
            "detail": str(e)
        }), 500


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
