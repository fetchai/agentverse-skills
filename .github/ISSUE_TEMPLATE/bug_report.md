---
name: Bug Report
about: Report a broken script, incorrect output, or API compatibility issue
title: "[Bug] "
labels: bug
assignees: ""
---

## Skill / Script Affected

<!-- e.g. `agentverse-chat` / `agentverse_chat.py` -->

## What Happened

<!-- Clear description of the bug. What did you expect? What did you see instead? -->

**Expected:**

**Actual:**

## Steps to Reproduce

```bash
export AGENTVERSE_API_KEY="..."   # (redact your real key)

python3 skills/.../scripts/....py \
  --arg value

# Error output:
```

## Environment

- Python version: <!-- python3 --version -->
- OS: <!-- e.g. macOS 14, Ubuntu 22.04 -->
- `requests` version: <!-- pip show requests | grep Version -->
- Commit / branch: <!-- git rev-parse HEAD -->

## Additional Context

<!-- API error response body, stack traces, screenshots, etc. -->
