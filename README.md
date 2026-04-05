# Grocery Checklist

Pantry-backed grocery tracking for OpenClaw with instant Telegram inline buttons.

- Tracks items as `needed` or `have`
- Renders a Telegram shopping list with tap-to-check buttons
- Updates instantly on tap — no round-trip through Claude
- Syncs across multiple users in real time
- Compact pantry view grouped by category

**Skill:** https://clawhub.ai/skills/grocery-checklist
**Plugin:** https://clawhub.ai/plugins/grocery-checklist

---

## Setup

### 1. Install the skill

```bash
openclaw skills install clawhub:grocery-checklist
```

### 2. Install the plugin

The plugin handles Telegram button taps instantly, bypassing Claude for sub-second response.

```bash
openclaw plugins install clawhub:grocery-checklist
```

Then add the plugin load path to `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "load": {
      "paths": ["~/.openclaw/skills/grocery-checklist"]
    }
  }
}
```

### 3. Create a dedicated Telegram bot

Create a bot via [@BotFather](https://t.me/botfather) and add it to `~/.openclaw/openclaw.json` under `channels.telegram.accounts`:

```json
{
  "channels": {
    "telegram": {
      "accounts": {
        "grocery": {
          "name": "Grocery",
          "enabled": true,
          "botToken": "YOUR_BOT_TOKEN",
          "dmPolicy": "allowlist",
          "allowFrom": [YOUR_TELEGRAM_USER_ID],
          "direct": {
            "YOUR_TELEGRAM_USER_ID": {
              "skills": ["grocery-checklist"],
              "systemPrompt": "This Telegram bot is for grocery shopping. Use the `grocery-checklist` skill. NEVER describe the grocery list or pantry in plain text. For shopping-list intents (`what do I need to buy`, `show me the shopping list`, `i'm shopping now`): call the `render_grocery_view` tool with mode=needed, then reply exactly `NO_REPLY`. For pantry intents (`show me the pantry`, `pantry view`, `what do I have`): call the `render_grocery_view` tool with mode=all, then reply exactly `NO_REPLY`. No text before or after the tool call."
            }
          }
        }
      }
    }
  }
}
```

### 4. Restart the gateway

```bash
openclaw gateway restart
```

---

## Usage

| Say this | What happens |
|---|---|
| `I ran out of salt` | Adds salt to the shopping list |
| `I bought eggs` | Marks eggs as in stock |
| `Show me the shopping list` | Renders the Telegram checklist |
| `Show me the pantry` | Renders a compact pantry view by category |
| `I'm going shopping now` | Renders the shopping list immediately |
| Tap an item button | Instantly checks it off (or unchecks) |
| Tap **Pantry View** | Switches to the pantry view |

---

## State

Stored at `~/.openclaw/data/grocery-checklist/state.json`.
