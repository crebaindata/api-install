# Crebain Python SDK

A lightweight, typed Python client for the Crebain API.

## Installation

```bash
pip install crebain-client
```

Or install from source:

```bash
cd sdk
pip install -e ".[dev]"
```

## Quickstart

```python
from crebain_client import CrebainClient

# Initialize the client
client = CrebainClient(
    api_key="ck_live_your_api_key_here",
    base_url="https://your-project.supabase.co/functions/v1/api"
)

# List entities
page = client.list_entities(limit=10)
for entity in page.entities:
    print(f"{entity.id}: {entity.name}")

# Check/create an entity
result = client.check_entity(
    external_entity_id="customer-123",
    name="Acme Corporation",
    metadata={"industry": "Technology"},
    idempotency_key="unique-request-id"
)
print(f"Entity ID: {result.entity_id}")
print(f"New company: {result.new_company}")
print(f"Request submitted: {result.request_submitted}")

# Download available files
for file in result.files_available:
    print(f"{file.filename} -> {file.signed_url}")
```

For a complete working example with file downloads, error handling, and request tracing, see [`test.py`](../test.py) in the repository root.

## Features

- **Typed responses** - All responses are typed dataclasses
- **Automatic pagination** - Use `iter_entities()` to iterate through all entities
- **Idempotency support** - Pass `idempotency_key` to safely retry requests
- **Webhook verification** - Verify incoming webhook signatures
- **Error handling** - Typed exceptions with `request_id` for debugging

## API Reference

### Client Methods

#### `list_entities(limit=50, cursor=None)`

List entities with pagination.

```python
page = client.list_entities(limit=20)
print(page.entities)
print(page.next_cursor)  # Use for next page
```

#### `iter_entities(limit=200)`

Iterate through all entities with automatic pagination.

```python
for entity in client.iter_entities():
    print(entity.name)
```

#### `check_entity(...)`

Check or create an entity and trigger enrichment.

```python
result = client.check_entity(
    external_entity_id="ext-123",
    name="Company Name",
    metadata={"key": "value"},
    force=False,                    # Force re-enrichment
    adverse_news_only=False,        # Only check adverse news
    idempotency_key="unique-key"    # For safe retries
)
```

#### `files_from_urls(url_list, entity_id=None, force=False, idempotency_key=None)`

Get files from URLs or trigger ingestion.

```python
result = client.files_from_urls(
    url_list=["https://example.com/doc.pdf"],
    idempotency_key="ingest-123"
)

for file in result.files:
    print(f"Available: {file.filename} -> {file.signed_url}")

for url in result.missing:
    print(f"Queued: {url}")
```

### Downloading Files

Files returned from `check_entity()` and `files_from_urls()` include temporary signed URLs (valid for ~15 minutes):

```python
import requests

result = client.check_entity(
    external_entity_id="customer-123",
    name="Acme Corp"
)

for file in result.files_available:
    if file.signed_url:
        # Download the file
        response = requests.get(file.signed_url)
        with open(file.filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {file.filename} ({file.bytes} bytes)")
```

#### FileItem Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `file_id` | `str` | Unique file identifier (UUID) |
| `filename` | `str` | Original filename |
| `mime_type` | `str \| None` | MIME type (e.g., `text/html`, `application/pdf`) |
| `bytes` | `int \| None` | File size in bytes |
| `signed_url` | `str \| None` | Temporary download URL (valid ~15 min) |
| `source_url` | `str \| None` | Original source URL (if ingested from URL) |
| `created_at` | `str` | ISO 8601 timestamp |

#### `create_webhook(url, secret, idempotency_key=None)`

Create a webhook subscription.

```python
webhook = client.create_webhook(
    url="https://myserver.com/webhook",
    secret="whsec_my_secret_at_least_16_chars"
)
print(f"Webhook ID: {webhook.id}")
```

#### `list_webhooks()`

List all webhook subscriptions.

```python
webhooks = client.list_webhooks()
for wh in webhooks:
    print(f"{wh.id}: {wh.url}")
```

#### `delete_webhook(webhook_id)`

Delete a webhook subscription.

```python
client.delete_webhook("webhook-uuid")
```

## Error Handling

All API errors include a `request_id` for debugging:

```python
from crebain_client import (
    CrebainClient,
    ApiError,
    UnauthorizedError,
    RateLimitedError,
    ValidationError,
)

client = CrebainClient(api_key="...", base_url="...")

try:
    result = client.check_entity(name="Test")
except RateLimitedError as e:
    print(f"Rate limited! Request ID: {e.request_id}")
    print(f"Message: {e.message}")
    # Implement backoff and retry
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except UnauthorizedError as e:
    print(f"Auth failed: {e.message}")
except ApiError as e:
    print(f"API error [{e.code}]: {e.message}")
    print(f"Request ID: {e.request_id}")
```

### Error Classes

| Exception | HTTP Status | Error Codes |
|-----------|-------------|-------------|
| `UnauthorizedError` | 401 | UNAUTHORIZED, API_KEY_REVOKED, API_KEY_EXPIRED |
| `ForbiddenError` | 403 | FORBIDDEN |
| `NotFoundError` | 404 | NOT_FOUND |
| `ConflictError` | 409 | CONFLICT |
| `ValidationError` | 422 | VALIDATION_ERROR |
| `RateLimitedError` | 429 | RATE_LIMITED |
| `InternalError` | 500 | INTERNAL |

## Pagination

Use cursor-based pagination for large datasets:

```python
# Manual pagination
cursor = None
while True:
    page = client.list_entities(limit=100, cursor=cursor)
    for entity in page.entities:
        process(entity)

    if not page.next_cursor:
        break
    cursor = page.next_cursor

# Or use the iterator (recommended)
for entity in client.iter_entities(limit=100):
    process(entity)
```

## Idempotency

Use idempotency keys for safe retries:

```python
# Same key = same result (no duplicate processing)
idempotency_key = f"check-{customer_id}-{timestamp}"

result = client.check_entity(
    external_entity_id=customer_id,
    idempotency_key=idempotency_key
)

# Retry with same key returns cached response
result = client.check_entity(
    external_entity_id=customer_id,
    idempotency_key=idempotency_key  # Same key
)
```

## Webhook Verification

Verify incoming webhook signatures:

```python
from crebain_client import verify_signature

# In your webhook handler (e.g., Flask)
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    timestamp = request.headers.get('X-Crebain-Timestamp')
    signature = request.headers.get('X-Crebain-Signature')
    raw_body = request.get_data()

    if not verify_signature(WEBHOOK_SECRET, timestamp, raw_body, signature):
        return 'Invalid signature', 401

    event = request.json
    if event['event'] == 'request.complete':
        request_id = event['request_id']
        result = event['result']
        # Process completion...

    return 'OK', 200
```

## Updating the OpenAPI Spec

To sync the pinned OpenAPI spec:

```bash
# From URL
python scripts/fetch_openapi.py --url https://your-api.com/openapi.yaml

# From local file
python scripts/fetch_openapi.py --path ../openapi.yaml

# Then run tests
pytest
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=crebain_client

# Type checking
mypy src/crebain_client
```

## License

MIT
