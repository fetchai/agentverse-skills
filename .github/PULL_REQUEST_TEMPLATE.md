## Summary

<!-- What does this PR do? Keep it brief — 1-3 sentences. -->

## Issues Fixed

<!-- List issues this PR closes. Use "Closes #N" so they auto-close on merge. -->

- Closes #

## Changes

<!-- Bullet list of what changed. Be specific about file paths and function names. -->

- 

## Testing Done

<!-- Describe how you tested this. Include the commands you ran and the output. -->

```bash
export AGENTVERSE_API_KEY="..."

# Command you ran:
python3 skills/.../scripts/....py ...

# Output:
```

## Checklist

- [ ] My script(s) run without errors locally
- [ ] JSON output is valid and matches the documented format in `SKILL.md`
- [ ] Python 3.8 compatible (no `str | None` union syntax, no `match` statements)
- [ ] `SKILL.md` is updated if the CLI interface changed
- [ ] `README.md` skills table is updated if I added a new skill
- [ ] New skills have a `scripts/` directory with at least one Python script
- [ ] License headers are included in new Python files
