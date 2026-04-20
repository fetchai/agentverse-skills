# Authentication

## Agentverse API Key

### Getting a Key

1. Go to [agentverse.ai](https://agentverse.ai)
2. Sign in (or create an account)
3. Navigate to **Profile → API Keys**
4. Click "Create API Key"
5. Copy the JWT token

### Using the Key

Set as environment variable:
```bash
export AGENTVERSE_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

In HTTP requests:
```bash
curl -H "Authorization: Bearer $AGENTVERSE_API_KEY" https://agentverse.ai/v1/hosting/agents
```

### Key Format

- Type: JWT (JSON Web Token)
- Scope: `av` (Agentverse)
- Expiry: Long-lived (check `exp` claim in JWT payload)
- Permissions: Full access to your hosted agents, almanac search

### Verifying Your Key Works

```bash
curl -s -H "Authorization: Bearer $AGENTVERSE_API_KEY" \
  https://agentverse.ai/v1/hosting/agents | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'items' in data:
    print(f'✓ Authenticated. {len(data[\"items\"])} hosted agents.')
else:
    print(f'✗ Error: {data}')
"
```

---

## ASI:One API Key

### Getting a Key

1. Go to [asi1.ai](https://asi1.ai)
2. Sign up / sign in
3. Navigate to API section
4. Create a new API key

### Using the Key

```bash
export ASI_ONE_API_KEY="sk_..."
```

In HTTP requests:
```bash
curl -H "Authorization: Bearer $ASI_ONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"asi1-mini","messages":[{"role":"user","content":"Hello"}]}' \
  https://api.asi1.ai/v1/chat/completions
```

### Key Format

- Type: API key (string, `sk_` prefix)
- Permissions: Chat completions access

---

## Security Best Practices

1. **Never commit keys to git** — use environment variables
2. **Use `.env` files locally** — add `.env` to `.gitignore`
3. **Rotate keys periodically** — especially if exposed
4. **Minimal scope** — don't share keys that have broader access than needed
5. **Check expiry** — JWT tokens expire; refresh before they do
