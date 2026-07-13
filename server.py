"""
Sentinel local server — serves the HTML app and proxies AI calls to Anthropic
so the API key stays safely on the server (never exposed to the browser).

Setup:
    pip install flask anthropic

Run:
    export ANTHROPIC_API_KEY=your_key_here      (Windows PowerShell: $env:ANTHROPIC_API_KEY="your_key_here")
    python server.py

Then open:
    http://localhost:5000

Do NOT use "Open with Live Server" for this file — Live Server only serves static
files and cannot hide your API key or proxy requests. Run this script instead.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from google import genai

app = Flask(__name__, static_folder=".")

HTML_FILE = "ai-code-review-platform.html"

# Gemini Client
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)


@app.route("/")
def index():
    return send_from_directory(".", HTML_FILE)


@app.route("/api/messages", methods=["POST"])
def proxy_messages():
    try:
        body = request.get_json(force=True)

        # Frontend nundi vachina messages ni oka prompt ga convert chestam
        prompt = ""

        if body.get("system"):
            prompt += body["system"] + "\n\n"

        for msg in body.get("messages", []):
            role = msg.get("role", "user").upper()

            content = msg.get("content", "")

            if isinstance(content, list):
                text = ""
                for item in content:
                    if item.get("type") == "text":
                        text += item.get("text", "")
                content = text

            prompt += f"{role}: {content}\n\n"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "content": [
                {
                    "type": "text",
                    "text": response.text
                }
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "content": [],
            "error": str(e)
        }), 500


if __name__ == "__main__":

    if not os.environ.get("GEMINI_API_KEY"):
        print("\n⚠️ GEMINI_API_KEY is NOT set!\n")
        print('PowerShell:')
        print('$env:GEMINI_API_KEY="YOUR_API_KEY"\n')

    app.run(debug=True, port=5000)