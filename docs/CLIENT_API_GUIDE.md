# Crebain API - Client Integration Guide

This guide covers everything you need to integrate with the Crebain API.

## Table of Contents

- [Quickstart](#quickstart)
- [Authentication](#authentication)
- [Pagination](#pagination)
- [Idempotency](#idempotency)
- [Common Flows](#common-flows)
- [Webhook Verification](#webhook-verification)
- [Troubleshooting](#troubleshooting)

---

## Quickstart

### 1. Set Your API Key

All requests require the `X-API-Key` header:

```bash
export API_KEY="ck_live_your_api_key_here"
```

### 2. List Entities

```bash
curl "https://<project-ref>.supabase.co/functions/v1/api/v1/entities?limit=10" \
  -H "X-API-Key: $API_KEY"
```

Response:
```json
{
  "data": {
    "entities": [],
    "next_cursor": null
  },
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### 3. Check/Create an Entity

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/api/v1/entity/check" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: my-unique-key-123" \
  -d '{
    "external_entity_id": "customer-456",
    "name": "Acme Corporation",
    "metadata": {"industry": "Technology"}
  }'
```

Response:
```json
{
  "data": {
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "new_company": true,
    "files_available": [],
    "request_submitted": true,
    "request_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
  },
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### 4. Register a Webhook

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/api/v1/webhooks" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: webhook-setup-001" \
  -d '{
    "url": "https://your-server.com/webhooks/crebain",
    "secret": "whsec_your_secret_at_least_16_chars"
  }'
```

Response:
```json
{
  "data": {
    "id": "8f14e45f-ceea-367a-a714-8dac03087e80",
    "url": "https://your-server.com/webhooks/crebain",
    "enabled": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

---

## Authentication

### API Key Header

Include your API key in every request:

```
X-API-Key: ck_live_...
```

API keys:
- Start with `ck_live_` prefix
- Are scoped to `read`, `write`, or both
- May have expiration dates
- Can be revoked at any time

### Key Scopes

| Scope | Allowed Operations |
|-------|-------------------|
| `read` | GET endpoints (list entities, list webhooks) |
| `write` | POST/DELETE endpoints (entity check, create webhook, etc.) |

If your key lacks the required scope, you'll receive a `403 FORBIDDEN` error.

---

## Pagination

List endpoints support cursor-based pagination.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Results per page (max 200) |
| `cursor` | string | - | Cursor from previous response |

### Example

**First page:**
```bash
curl "https://<project-ref>.supabase.co/functions/v1/api/v1/entities?limit=20" \
  -H "X-API-Key: $API_KEY"
```

**Next page:**
```bash
curl "https://<project-ref>.supabase.co/functions/v1/api/v1/entities?limit=20&cursor=MjAyNC0wMS..." \
  -H "X-API-Key: $API_KEY"
```

### Response Structure

```json
{
  "data": {
    "entities": [...],
    "next_cursor": "MjAyNC0wMS0xNVQxMDozMDowMFp8NTUwZTg0MDA..."
  },
  "request_id": "..."
}
```

- `next_cursor` is present only if more results exist
- When `next_cursor` is absent, you've reached the last page

---

## Idempotency

Use the `Idempotency-Key` header to safely retry POST requests without causing duplicate operations.

### Supported Endpoints

- `POST /v1/entity/check`
- `POST /v1/files/from-urls`
- `POST /v1/webhooks`

### Usage

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/api/v1/entity/check" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: unique-request-id-12345" \
  -d '{"external_entity_id": "ext-123", "name": "Acme Corp"}'
```

### Behavior

1. **First request**: Processed normally, response cached
2. **Replay with same key + body**: Returns cached response (no duplicate processing)
3. **Same key, different body**: Returns `409 CONFLICT` error

### Best Practices

- Use UUIDs or unique transaction IDs as idempotency keys
- Keys are valid for 24 hours
- Include idempotency keys on all POST requests for safe retries

---

## Common Flows

### Flow 1: Entity Enrichment

Check an entity, wait for async processing, then retrieve files.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  POST           │     │  Webhook        │     │  GET            │
│  /entity/check  │────▶│  request.       │────▶│  /entities or   │
│                 │     │  complete       │     │  fetch files    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Step 1: Check entity**
```bash
curl -X POST ".../v1/entity/check" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: check-acme-001" \
  -d '{"external_entity_id": "acme", "name": "Acme Corp"}'
```

If `request_submitted: true`, an async job was created.

**Step 2: Wait for webhook**

Your webhook endpoint receives:
```json
{
  "event": "request.complete",
  "request_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "kind": "entity_enrich",
  "completed_at": "2024-01-15T12:30:00Z",
  "result": {"file_ids": ["uuid1", "uuid2"]}
}
```

**Step 3: Fetch results**

Use the entity ID or file IDs from the webhook to retrieve data.

### Flow 2: URL File Ingestion

Submit URLs, get existing files immediately, receive webhook when missing files are processed.

**Step 1: Submit URLs**
```bash
curl -X POST ".../v1/files/from-urls" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: ingest-batch-001" \
  -d '{
    "url_list": [
      "https://example.com/doc1.pdf",
      "https://example.com/doc2.pdf"
    ]
  }'
```

Response:
```json
{
  "data": {
    "files": [
      {
        "file_id": "...",
        "source_url": "https://example.com/doc1.pdf",
        "signed_url": "https://storage.../signed?token=..."
      }
    ],
    "missing": ["https://example.com/doc2.pdf"],
    "request_submitted": true,
    "request_id": "..."
  }
}
```

- `files`: Already available, includes signed download URLs (valid 15 min)
- `missing`: URLs queued for async ingestion
- `request_submitted`: If true, you'll receive a webhook when processing completes

**Step 2: Wait for webhook** (if `request_submitted: true`)

**Step 3: Re-fetch** to get newly ingested files with signed URLs

---

## Webhook Verification

All webhook payloads are signed using HMAC-SHA256. Always verify signatures before processing.

### Headers

| Header | Description |
|--------|-------------|
| `X-Crebain-Timestamp` | Unix timestamp (seconds) when the request was sent |
| `X-Crebain-Signature` | Signature in format `v1=<hex_digest>` |

### Signature Verification

The signature is computed over: `{timestamp}.{raw_body}`

**Node.js Example:**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(secret, timestamp, rawBody, signature) {
  const payload = `${timestamp}.${rawBody}`;
  const expected = 'v1=' + crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  // Use timing-safe comparison to prevent timing attacks
  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected),
      Buffer.from(signature)
    );
  } catch {
    return false;
  }
}

// Usage in Express
app.post('/webhooks/crebain', (req, res) => {
  const timestamp = req.headers['x-crebain-timestamp'];
  const signature = req.headers['x-crebain-signature'];
  const rawBody = req.rawBody; // Ensure you capture raw body

  if (!verifyWebhookSignature(WEBHOOK_SECRET, timestamp, rawBody, signature)) {
    return res.status(401).send('Invalid signature');
  }

  // Process webhook...
  const event = req.body;
  console.log(`Received ${event.event} for request ${event.request_id}`);

  res.status(200).send('OK');
});
```

**Python Example:**
```python
import hmac
import hashlib

def verify_webhook_signature(secret: str, timestamp: str, raw_body: str, signature: str) -> bool:
    payload = f"{timestamp}.{raw_body}"
    expected = "v1=" + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Webhook Payload Structure

```json
{
  "event": "request.complete",
  "request_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "entity_enrich",
  "completed_at": "2024-01-15T12:30:00Z",
  "result": {
    "file_ids": ["uuid1", "uuid2"]
  }
}
```

| Field | Description |
|-------|-------------|
| `event` | Event type (currently `request.complete`) |
| `request_id` | ID of the completed async request |
| `org_id` | Your organization ID |
| `kind` | Request type: `entity_enrich` or `url_ingest` |
| `completed_at` | ISO 8601 completion timestamp |
| `result` | Request-specific result data |

---

## Troubleshooting

### 401 Unauthorized

**Causes:**
- Missing `X-API-Key` header
- Invalid API key format
- API key not found in database

**Solution:**
```bash
# Verify header is set correctly
curl -v "https://.../v1/entities" -H "X-API-Key: ck_live_..."
```

### 401 API_KEY_REVOKED

**Cause:** The API key has been revoked by an administrator.

**Solution:** Request a new API key from your administrator.

### 401 API_KEY_EXPIRED

**Cause:** The API key has passed its expiration date.

**Solution:** Request a new API key with a later or no expiration.

### 403 Forbidden

**Cause:** Your API key lacks the required scope.

**Solution:** Ensure your key has the appropriate scope:
- `read` for GET requests
- `write` for POST/DELETE requests

### 409 Conflict

**Causes:**
- Idempotency key reused with different request body
- Resource already in conflicting state (e.g., key already revoked)

**Solution:**
- Use a new idempotency key for different requests
- Check resource state before retrying

### 422 Validation Error

**Cause:** Request body failed validation.

**Example Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "url_list cannot exceed 50 URLs",
    "request_id": "..."
  }
}
```

**Solution:** Fix the validation issue indicated in the message.

### 429 Rate Limited

**Cause:** Exceeded 60 requests per minute.

**Response:**
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Max 60 requests per minute.",
    "request_id": "..."
  }
}
```

**Solution:**
- Implement exponential backoff
- Reduce request frequency
- Cache responses where appropriate

**Retry Strategy:**
```javascript
async function requestWithRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (err.status === 429 && i < maxRetries - 1) {
        const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
        await new Promise(r => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }
}
```

### 500 Internal Error

**Cause:** Server-side error.

**Solution:**
- Retry with exponential backoff
- If persistent, contact support with the `request_id`

---

## Response Format

All responses follow consistent envelopes.

### Success Response

```json
{
  "data": {
    // Endpoint-specific payload
  },
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### Error Response

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

The `request_id` is also available in the `X-Request-Id` response header.
