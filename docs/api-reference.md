# Agentverse API Reference

## Base URL

```
https://agentverse.ai
```

## Authentication

All requests require:
```
Authorization: Bearer {AGENTVERSE_API_KEY}
```

---

## Hosting API

Manage hosted agents running on Agentverse infrastructure.

### List Agents
```http
GET /v1/hosting/agents
```

Response:
```json
{
  "items": [
    {
      "address": "agent1q...",
      "name": "my-agent",
      "running": true,
      "compiled": true,
      "revision": 5
    }
  ]
}
```

### Get Agent Details
```http
GET /v1/hosting/agents/{address}
```

### Create Agent
```http
POST /v1/hosting/agents
Content-Type: application/json

{
  "name": "my-new-agent"
}
```

Response:
```json
{
  "address": "agent1q...",
  "name": "my-new-agent",
  "running": false
}
```

### Delete Agent
```http
DELETE /v1/hosting/agents/{address}
```

### Upload Code
```http
PUT /v1/hosting/agents/{address}/code
Content-Type: application/json

{
  "code": "[{\"language\":\"python\",\"name\":\"agent.py\",\"value\":\"...\"}]"
}
```

⚠️ The `code` field is a **JSON string** containing a list of file objects.

### Get Code
```http
GET /v1/hosting/agents/{address}/code
```

### Start Agent
```http
POST /v1/hosting/agents/{address}/start
```

### Stop Agent
```http
POST /v1/hosting/agents/{address}/stop
```

### Get Latest Logs
```http
GET /v1/hosting/agents/{address}/logs/latest
```

Response:
```json
[
  {
    "log_timestamp": "2026-04-20T15:30:00.000Z",
    "log_entry": "INFO: Agent started successfully",
    "log_type": "info"
  }
]
```

---

## Almanac API

Search and query the decentralized agent registry.

### Search Agents
```http
POST /v1/search/agents
Content-Type: application/json
Authorization: Bearer <token>
```

Request body:
```json
{
  "search_text": "query string",
  "limit": 10,
  "offset": 0,
  "sort": "relevancy",
  "direction": "desc",
  "semantic_search": false,
  "filters": {
    "protocol_digest": ["proto:..."]
  }
}
```

> **Note**: The older `GET /v1/almanac/search` endpoint returns 404 and should not be used.

### Get Agent Registration
```http
GET /v1/almanac/agents/{address}
```

Response includes:
- `protocols`: List of supported protocol digests
- `endpoints`: Where the agent receives messages
- `expiry`: Registration expiration
- `metadata`: Agent-provided metadata

---

## Rate Limits

- Hosting API: ~60 requests/minute
- Almanac API: ~120 requests/minute
- If rate limited (HTTP 429), wait 30 seconds and retry

---

## Error Responses

```json
{
  "detail": "Error description",
  "status_code": 401
}
```

Common errors:
- `401`: Invalid or expired API key
- `403`: Insufficient permissions
- `404`: Agent not found
- `422`: Invalid request body
- `429`: Rate limited
- `500`: Server error (retry)

---

## ASI:One API

### Base URL
```
https://api.asi1.ai/v1
```

### Chat Completions
```http
POST /v1/chat/completions
Authorization: Bearer {ASI_ONE_API_KEY}
Content-Type: application/json

{
  "model": "asi1-mini",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

Models:
- `asi1` — Full model (higher quality, slower)
- `asi1-mini` — Mini model (faster, cheaper)
