# Grocery Checklist

Pantry-backed grocery tracking for OpenClaw.

What it does:
- keeps a persistent grocery state
- tracks whether an item is `needed` or `have`
- renders a Telegram checklist with inline buttons
- updates the list when the user says they ran out of something or bought it

Typical flow:
- `I ran out of salt`
- `What do I need to buy?`
- tap `Bought salt` in Telegram
- later: `I ran out of salt` again

Wrapper:

```bash
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh show
```

State file:

```text
~/.openclaw/data/grocery-checklist/state.json
```
