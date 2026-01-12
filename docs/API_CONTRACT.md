# Crebain API Contract

This document defines the stability guarantees, versioning policy, and behavioral contract for the Crebain API.

## Table of Contents

- [Versioning](#versioning)
- [Stability Guarantees](#stability-guarantees)
- [Error Model](#error-model)
- [Response Envelope](#response-envelope)
- [Breaking vs Non-Breaking Changes](#breaking-vs-non-breaking-changes)
- [Deprecation Policy](#deprecation-policy)

---

## Versioning

### URL Path Versioning

The API version is specified in the URL path:

```
https://<project-ref>.supabase.co/functions/v1/api/v1/entities
                                                  ^^
                                              API version
```

### Current Version

**v1** - Stable, production-ready

### Version Lifecycle

| Status | Description |
|--------|-------------|
| **Stable** | Production-ready, breaking changes follow deprecation policy |
| **Deprecated** | Still functional, will be removed in future |
| **Sunset** | No longer available |

---

## Stability Guarantees

The following are guaranteed stable within a major version:

### Guaranteed Stable

- Endpoint paths (`/v1/entities`, `/v1/entity/check`, etc.)
- HTTP methods for each endpoint
- Required request parameters and their types
- Response envelope structure (`data`, `error`, `request_id`)
- Error code values
- Authentication mechanism (`X-API-Key` header)
- Idempotency behavior for supported endpoints

### May Change (Non-Breaking)

- New optional request parameters
- New fields in response objects
- New error codes (clients should handle unknown codes gracefully)
- New endpoints
- New optional headers

---

## Error Model

### Error Response Structure

All errors follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "request_id": "uuid"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Machine-readable error code (stable) |
| `message` | string | Human-readable description (may change) |
| `request_id` | string | Unique request identifier for debugging |

### Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `INVALID_REQUEST` | Malformed JSON or invalid request format |
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 401 | `API_KEY_REVOKED` | API key has been revoked |
| 401 | `API_KEY_EXPIRED` | API key has expired |
| 403 | `FORBIDDEN` | Valid key but insufficient permissions (scope) |
| 404 | `NOT_FOUND` | Requested resource does not exist |
| 409 | `CONFLICT` | Idempotency conflict or resource state conflict |
| 422 | `VALIDATION_ERROR` | Request body failed validation |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL` | Server-side error |

### Client Handling Guidance

**Retryable Errors:**
- `429 RATE_LIMITED` - Retry with exponential backoff
- `500 INTERNAL` - Retry with exponential backoff (max 3 attempts)

**Non-Retryable Errors:**
- `400 INVALID_REQUEST` - Fix request format
- `401 UNAUTHORIZED` - Check API key
- `403 FORBIDDEN` - Check key scopes
- `409 CONFLICT` - Use different idempotency key or check resource state
- `422 VALIDATION_ERROR` - Fix request body

---

## Response Envelope

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
    "message": "Description",
    "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  }
}
```

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-Id` | Unique request identifier (matches `request_id` in body) |
| `Content-Type` | Always `application/json` |

---

## Breaking vs Non-Breaking Changes

### Breaking Changes

The following require a new API version:

- Removing an endpoint
- Removing a required request parameter
- Removing a response field that clients depend on
- Changing the type of an existing field
- Changing the meaning of an existing field
- Changing authentication requirements
- Changing error codes for existing error conditions

### Non-Breaking Changes

The following can be made without version increment:

- Adding new endpoints
- Adding optional request parameters
- Adding new fields to responses
- Adding new error codes
- Adding new enum values
- Improving error messages
- Performance improvements
- Bug fixes that align behavior with documentation

---

## Deprecation Policy

When a breaking change is necessary:

1. **Announcement**: Deprecation announced in [CHANGELOG.md](./CHANGELOG.md)
2. **Dual Support**: Both old and new behavior supported during transition
3. **Migration Guide**: Documentation provided for migration
4. **Sunset**: Old behavior removed after transition period

Clients should:
- Subscribe to changelog updates
- Handle unknown fields gracefully (ignore, don't fail)
- Handle unknown error codes gracefully (treat as generic error)

---

## Endpoint Reference

### Public Endpoints (API Key Auth)

| Method | Path | Scopes | Idempotent |
|--------|------|--------|------------|
| GET | `/v1/entities` | read | N/A |
| POST | `/v1/entity/check` | write | Yes |
| POST | `/v1/files/from-urls` | write | Yes |
| GET | `/v1/webhooks` | read | N/A |
| POST | `/v1/webhooks` | write | Yes |
| DELETE | `/v1/webhooks/{id}` | write | No |

### Admin Endpoints (Admin Key Auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/admin/keys` | List API keys for an org |
| POST | `/v1/admin/keys` | Create API key |
| POST | `/v1/admin/keys/{id}/revoke` | Revoke API key |

Admin endpoints require the `X-Admin-Key` header instead of `X-API-Key`.

---

## OpenAPI Specification

The complete API specification is available in [openapi.yaml](../openapi.yaml).

The OpenAPI spec is the authoritative source for:
- Request/response schemas
- Parameter definitions
- Example payloads
