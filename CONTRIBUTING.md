# Contributing to Agentverse Skills

Thank you for helping grow the library of Agentverse skills! This guide explains how to add new skills, run existing scripts locally, write integration tests, and submit a pull request.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Adding a New Skill](#adding-a-new-skill)
3. [SKILL.md Template](#skillmd-template)
4. [Script Requirements](#script-requirements)
5. [Running Locally](#running-locally)
6. [Integration Tests](#integration-tests)
7. [Code Style](#code-style)
8. [Pull Request Guidelines](#pull-request-guidelines)

---

## Project Structure

```
skills/
└── <skill-name>/
    ├── SKILL.md          # Skill definition (required)
    ├── scripts/
    │   └── <script>.py  # Self-contained CLI script (required)
    └── references/       # Deep documentation, API notes (optional)
examples/                 # Worked examples showing real outputs
docs/                     # Cross-skill reference documentation
tests/
└── test_integration.py   # Live integration tests
```

Every skill lives in its own directory under `skills/`. The directory name becomes the skill's canonical identifier (e.g., `agentverse-chat`).

---

## Adding a New Skill

### 1. Create the skill directory

```bash
mkdir -p skills/<skill-name>/scripts
mkdir -p skills/<skill-name>/references  # optional
```

Naming convention: `<platform>-<action>` using kebab-case, e.g. `agentverse-deploy`, `asi1-chat`.

### 2. Write the SKILL.md

See [SKILL.md Template](#skillmd-template) below. This is what AI coding agents read to discover and use the skill — make it precise and complete.

### 3. Write the Python script

See [Script Requirements](#script-requirements) below. The script must be self-contained (only `requests` + stdlib), have a CLI interface via `argparse`, and output JSON to stdout.

### 4. Add an entry to README.md

Add a row to the **Skills** table in `README.md` with the skill name, description, and key script.

### 5. Add integration tests (strongly encouraged)

Add test cases to `tests/test_integration.py` covering the happy path and at least one error case. See [Integration Tests](#integration-tests) for details.

### 6. Add a worked example (encouraged)

Create `examples/0N-<short-description>.md` showing a real CLI invocation and its JSON output. This helps users understand what to expect.

---

## SKILL.md Template

```markdown
---
name: <skill-name>
description: >
  One-paragraph description of what this skill does.
  Include trigger phrases (what a user might say to invoke it),
  key capabilities, and any important limitations.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "YYYY-MM-DD"
allowed-tools: Read Bash(python3 *) Bash(pip install requests)
---

# <Skill Name>

## What This Skill Does

Short paragraph expanding on the description.

## Usage

```bash
export AGENTVERSE_API_KEY="your-key"

python3 skills/<skill-name>/scripts/<script>.py [options]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--foo`  | Yes      | What foo does |
| `--bar`  | No       | What bar does (default: `baz`) |

## Output

JSON object on stdout:

```json
{
  "status": "success",
  "result": "..."
}
```

## Error Handling

On failure, prints an error message to stderr and exits with code 1.
```

Keep the SKILL.md concise and accurate. AI coding agents treat it as authoritative — if the SKILL.md says an argument exists, the script must support it.

---

## Script Requirements

Every script under `skills/*/scripts/` must follow these rules:

### Dependencies
- **Only `requests` + Python stdlib.** No other third-party packages.
- Include `pip install requests` in your README/SKILL.md setup instructions.

### CLI interface
- Use `argparse` for argument parsing.
- Include `--help` text for every argument.
- Runnable directly: `python3 skills/foo/scripts/foo.py --arg value`

### Output
- **Stdout**: Valid JSON on success.
- **Stderr**: Human-readable error messages on failure.
- **Exit code**: 0 on success, 1 on failure.

```python
import json, sys

# Success
print(json.dumps({"status": "success", "data": result}, indent=2))
sys.exit(0)

# Failure
print(f"Error: {message}", file=sys.stderr)
sys.exit(1)
```

### Environment variables
- Use `AGENTVERSE_API_KEY` for Agentverse API access.
- Use `ASI_ONE_API_KEY` for ASI:One API access.
- Print a helpful message if a required env var is missing:

```python
import os, sys

api_key = os.environ.get("AGENTVERSE_API_KEY")
if not api_key:
    print(
        "Error: AGENTVERSE_API_KEY environment variable not set.\n"
        "Get your key at: https://agentverse.ai/profile/api-keys",
        file=sys.stderr,
    )
    sys.exit(1)
```

### License header
Include the Apache 2.0 header at the top of every script:

```python
# Copyright 2026 Fetch.ai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

---

## Running Locally

```bash
# Clone
git clone https://github.com/fetchai/agentverse-skills.git
cd agentverse-skills

# Install the only dependency
pip install requests

# Set your API key
export AGENTVERSE_API_KEY="eyJ..."

# Run any script
python3 skills/agentverse-search/scripts/search_agents.py --query "image generation" --limit 5
python3 skills/agentverse-manage/scripts/manage_agents.py list
python3 skills/asi1-chat/scripts/asi1_chat.py --prompt "Hello!"
```

---

## Integration Tests

Integration tests live in `tests/test_integration.py` and make real API calls to verify the skills work end-to-end.

### Running tests locally

```bash
export AGENTVERSE_API_KEY="eyJ..."
export ASI_ONE_API_KEY="sk_..."   # optional, for ASI:One tests

# Run all tests
python3 tests/test_integration.py

# Or with pytest (verbose output)
pip install pytest
pytest tests/test_integration.py -v
```

### Writing new tests

Add a `TestCase` class to `tests/test_integration.py`:

```python
class TestMySkill(unittest.TestCase):
    def setUp(self):
        self.api_key = os.environ.get("AGENTVERSE_API_KEY", "")
        if not self.api_key:
            self.skipTest("AGENTVERSE_API_KEY not set")

    def test_happy_path(self):
        result = subprocess.run(
            ["python3", "skills/my-skill/scripts/my_script.py", "--arg", "value"],
            capture_output=True, text=True,
            env={**os.environ, "AGENTVERSE_API_KEY": self.api_key},
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "success")
```

### CI behavior

- The `test.yml` workflow runs on every push/PR: syntax checks, SKILL.md validation, Python 3.8/3.10/3.12 matrix.
- The `integration.yml` workflow runs on push to `main` (when `AGENTVERSE_INTEGRATION_TESTS_ENABLED` is set) and on manual dispatch. Integration tests are `continue-on-error: true` to avoid blocking merges on transient API failures.

---

## Code Style

- **PEP 8** — use `black` or `flake8` locally if you like, but style is not enforced in CI.
- **Python 3.8 compatibility** — this is the minimum supported version:
  - ✅ `Optional[str]` from `typing`
  - ❌ `str | None` (requires Python 3.10+)
  - ✅ `f"hello {name}"`
  - ❌ `match` statements (requires Python 3.10+)
- **Type hints** — encouraged for function signatures, not required.
- **Docstrings** — encouraged for non-trivial functions.
- **No magic numbers** — name constants at the top of the file.

---

## Pull Request Guidelines

1. **Reference issues.** If your PR fixes a bug or implements a feature tracked in an issue, include `Closes #N` in the PR description.

2. **Test your changes.** Run the affected scripts locally before opening a PR. For new skills, add integration tests.

3. **Follow naming conventions.** Skill directories: `<platform>-<action>` in kebab-case. Scripts: `<action>_<noun>.py` in snake_case.

4. **Update README.md.** If you add a skill, add a row to the Skills table. If you change a script's interface, update the SKILL.md.

5. **One concern per PR.** Bug fixes, new features, and refactors should be separate PRs when possible.

6. **Keep commits clean.** Use [conventional commits](https://www.conventionalcommits.org/) style:
   - `feat: add asi1-pro model support to asi1-chat`
   - `fix: search --protocol flag uses correct filter format`
   - `docs: update CONTRIBUTING with test instructions`

---

## Questions?

Open an issue at [github.com/fetchai/agentverse-skills/issues](https://github.com/fetchai/agentverse-skills/issues) or reach out via the [Fetch.ai Developer Discord](https://discord.gg/fetchai).
