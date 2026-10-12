# Log format: JSON Lines

Every sample service writes one JSON object per line to stdout:

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service", "level": "ERROR", "message": "Database connection timed out after 5s", "extra": {"request_id": "abc123"}}
```

| Field | Rule |
|---|---|
| timestamp | ISO 8601, UTC, milliseconds, trailing `Z` |
| service | payment-service, order-service or inventory-service |
| level | DEBUG, INFO, WARNING, ERROR or CRITICAL |
| message | human readable text |
| extra | optional object |
