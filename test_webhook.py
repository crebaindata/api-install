"""
Minimal webhook example for Crebain API.

Usage:
    1. Install dependencies: pip install flask crebain-client
    2. Run this server: python test_webhook.py
    3. Expose with ngrok: ngrok http 5000
    4. Register webhook with the ngrok URL

For local testing without a public URL, use the --register flag
with your ngrok URL after starting ngrok.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from crebain_client import CrebainClient, verify_signature

# Configuration - set these via environment variables
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
CREBAIN_API_KEY = os.getenv("CREBAIN_API_KEY", "")
CREBAIN_BASE_URL = os.getenv("CREBAIN_BASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Handle incoming webhook from Crebain API."""

    # Get signature headers
    timestamp = request.headers.get("X-Crebain-Timestamp")
    signature = request.headers.get("X-Crebain-Signature")
    raw_body = request.get_data()

    logger.info("=" * 50)
    logger.info("Received webhook")
    logger.info("  Timestamp: %s", timestamp)
    logger.info("  Signature: %s", signature[:50] + "..." if signature else None)

    # Verify signature
    if not verify_signature(WEBHOOK_SECRET, timestamp, raw_body, signature):
        logger.error("Invalid signature!")
        return jsonify({"error": "Invalid signature"}), 401

    logger.info("  Signature: VALID")

    # Parse and log the event
    event = request.json
    event_type = event.get("event")
    request_id = event.get("request_id")
    org_id = event.get("org_id")
    kind = event.get("kind")

    logger.info("  Event: %s", event_type)
    logger.info("  Request ID: %s", request_id)
    logger.info("  Org ID: %s", org_id)
    logger.info("  Kind: %s", kind)

    if event_type == "request.complete":
        result = event.get("result", {})
        logger.info("  Result: %s", json.dumps(result, indent=2)[:500])

        # Here you would typically:
        # 1. Update your database
        # 2. Notify your users
        # 3. Trigger downstream processing

    logger.info("=" * 50)
    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


def register_webhook(webhook_url: str):
    """Register a webhook with the Crebain API."""
    client = CrebainClient(api_key=CREBAIN_API_KEY, base_url=CREBAIN_BASE_URL, supabase_anon_key=SUPABASE_ANON_KEY)

    try:
        webhook = client.create_webhook(
            url=webhook_url,
            secret=WEBHOOK_SECRET,
        )
        logger.info("Webhook registered successfully!")
        logger.info("  Webhook ID: %s", webhook.id)
        logger.info("  URL: %s", webhook.url)
        return webhook
    except Exception as e:
        logger.error("Failed to register webhook: %s", e)
        raise


def list_webhooks():
    """List all registered webhooks."""
    client = CrebainClient(api_key=CREBAIN_API_KEY, base_url=CREBAIN_BASE_URL, supabase_anon_key=SUPABASE_ANON_KEY)

    webhooks = client.list_webhooks()
    logger.info("Registered webhooks:")
    for wh in webhooks:
        logger.info("  - %s: %s (enabled: %s)", wh.id, wh.url, wh.enabled)
    return webhooks


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--register" and len(sys.argv) > 2:
            # Register webhook: python test_webhook.py --register https://your-ngrok-url.ngrok.io/webhook
            webhook_url = sys.argv[2]
            register_webhook(webhook_url)

        elif command == "--list":
            # List webhooks: python test_webhook.py --list
            list_webhooks()

        else:
            print("Usage:")
            print("  python test_webhook.py              # Start webhook server")
            print("  python test_webhook.py --register <url>  # Register webhook")
            print("  python test_webhook.py --list       # List webhooks")
    else:
        # Start the Flask server
        port = int(os.getenv("PORT", "5001"))
        logger.info("Starting webhook server on http://localhost:%d", port)
        logger.info("Webhook endpoint: http://localhost:%d/webhook", port)
        logger.info("")
        logger.info("To expose publicly, run: ngrok http %d", port)
        logger.info("Then register: python test_webhook.py --register https://xxx.ngrok.io/webhook")
        app.run(host="0.0.0.0", port=port, debug=True)
