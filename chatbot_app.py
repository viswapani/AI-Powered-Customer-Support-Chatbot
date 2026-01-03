from __future__ import annotations

import os

from flask import Flask, request, render_template_string, redirect, url_for, session

from chatbot import MedEquipChatbot

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Single chatbot instance for this process
bot = MedEquipChatbot()


HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <title>MedEquip Support Chatbot</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      .container { max-width: 800px; margin: 0 auto; }
      .chat-box { border: 1px solid #ccc; padding: 1rem; height: 400px; overflow-y: auto; background: #fafafa; }
      .msg-user { margin: 0.5rem 0; }
      .msg-assistant { margin: 0.5rem 0; }
      .msg-user strong { color: #0066cc; }
      .msg-assistant strong { color: #008000; }
      form { margin-top: 1rem; }
      input[type=\"text\"] { width: 100%; padding: 0.5rem; }
      button { margin-top: 0.5rem; padding: 0.5rem 1rem; }
      .auth-box { margin-bottom: 1rem; padding: 0.5rem; border: 1px solid #ddd; background: #f5f5f5; }
      label { display: block; margin-top: 0.25rem; }
    </style>
  </head>
  <body>
    <div class=\"container\">
      <h1>MedEquip Solutions - Customer Support Chatbot</h1>

      <div class=\"auth-box\">
        <form method=\"post\" action=\"{{ url_for('set_auth') }}\">
          <strong>Optional authentication for account-specific queries</strong><br/>
          <label>Email:</label>
          <input type=\"text\" name=\"email\" value=\"{{ auth_email or '' }}\" />
          <label>Client ID (ME-XXXXX):</label>
          <input type=\"text\" name=\"client_id\" value=\"{{ auth_client_id or '' }}\" />
          <button type=\"submit\">Set Authentication</button>
          {% if auth_status %}<div>{{ auth_status }}</div>{% endif %}
        </form>
      </div>

      <div class=\"chat-box\" id=\"chat-box\">
        {% if history %}
          {% for turn in history %}
            <div class=\"msg-user\"><strong>You:</strong> {{ turn['user'] }}</div>
            <div class=\"msg-assistant\"><strong>Assistant:</strong> {{ turn['assistant'] }}</div>
          {% endfor %}
        {% else %}
          <em>No messages yet. Ask a question about orders, warranty, support hours, etc.</em>
        {% endif %}
      </div>

      <form method=\"post\" action=\"{{ url_for('chat') }}\">
        <input type=\"text\" name=\"message\" placeholder=\"Type your question here...\" autocomplete=\"off\" />
        <button type=\"submit\">Send</button>
      </form>
    </div>
    <script>
      // Scroll chat box to bottom on load
      (function() {
        var box = document.getElementById('chat-box');
        if (box) { box.scrollTop = box.scrollHeight; }
      })();
    </script>
  </body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    history = [
        {"user": t.user, "assistant": t.assistant}
        for t in bot.history
    ]
    auth_email = session.get("auth_email")
    auth_client_id = session.get("auth_client_id")
    auth_status = session.get("auth_status")
    session["auth_status"] = None
    return render_template_string(
        HTML_TEMPLATE,
        history=history,
        auth_email=auth_email,
        auth_client_id=auth_client_id,
        auth_status=auth_status,
    )


@app.route("/chat", methods=["POST"])
def chat():
    message = request.form.get("message", "").strip()
    if message:
        reply = bot.chat(message)
        # history is already stored inside bot
    return redirect(url_for("index"))


@app.route("/set_auth", methods=["POST"])
def set_auth():
    email = request.form.get("email", "").strip()
    client_id = request.form.get("client_id", "").strip()

    session["auth_email"] = email
    session["auth_client_id"] = client_id

    if email and client_id:
        if bot.authenticate(email=email, client_id=client_id):
            session["auth_status"] = f"Authenticated as {bot.authenticated_client.name} ({bot.authenticated_client.client_id})"
        else:
            session["auth_status"] = "Authentication failed. Please check your email and Client ID."
    else:
        # Clear authentication if fields are empty
        bot.authenticated_client = None
        session["auth_status"] = "Authentication cleared."

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
