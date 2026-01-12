# Changelog

All notable changes to the Crebain API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2024-01-15

### Added

- **Entity Management**
  - `GET /v1/entities` - List entities with cursor-based pagination
  - `POST /v1/entity/check` - Check or create entity, trigger enrichment

- **File Handling**
  - `POST /v1/files/from-urls` - Get existing files or trigger URL ingestion

- **Webhook Subscriptions**
  - `GET /v1/webhooks` - List webhook subscriptions
  - `POST /v1/webhooks` - Create webhook subscription
  - `DELETE /v1/webhooks/{id}` - Delete webhook subscription
  - Webhook signature verification (HMAC-SHA256)

- **Admin Endpoints**
  - `GET /v1/admin/keys` - List API keys
  - `POST /v1/admin/keys` - Create API key
  - `POST /v1/admin/keys/{id}/revoke` - Revoke API key

- **Core Features**
  - API key authentication with scopes (`read`, `write`)
  - Idempotency support for POST endpoints
  - Rate limiting (60 requests/minute per key)
  - Consistent error response format
  - Request ID tracking (`X-Request-Id` header)

---

## Changelog Template

Use this template for future releases:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security updates
```
