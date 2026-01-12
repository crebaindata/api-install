# SLAs and Limits

## SLA

Response within 24 hours.

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests per minute per API key | 60 |

When the rate limit is exceeded, the API returns HTTP `429` with error code `RATE_LIMITED`.
