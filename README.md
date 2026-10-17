# Clash Design Anonymous Feedback Bot

A working Discord bot starter that matches the purple/black Clash Design feedback mockup.

## What it does
- `/setup_feedback` posts a branded feedback panel with a **Leave Review** button.
- Clicking the button creates a private channel visible only to the client and the bot.
- The client sends one message containing review text and optionally an image.
- They click **Publish Review**.
- The bot posts an embed in the configured public `#feedback` channel with only the review and image.
- The public post does not include the submitter's Discord name, username, avatar, tag, or mention.
- The private submission channel is deleted after publishing or cancelling.

## Important privacy note
The bot does not include Discord identity in the public embed. It cannot remove a name or identifying information that a client writes into their own review or includes inside an image. Discord's normal message history and server audit logs may also retain administrative records. Do not promise absolute anonymity beyond what the bot controls.

## Requirements
- Python 3.10 or newer
- A Discord application/bot created in the Discord Developer Portal
- Bot invited to your server with permissions described below

## Setup
1. Extract this ZIP to a folder.
2. Install Python 3.10+ if needed.
3. Open a terminal in this folder and run:
   ```bash
   python -m venv .venv
   ```
   Windows:
   ```powershell
   .venv\Scripts\activate
   ```
   macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to a new file named `.env`.
6. In `.env`, fill in:
   - `DISCORD_TOKEN`: bot token from the Discord Developer Portal
   - `GUILD_ID`: your Discord server ID
   - `PANEL_CHANNEL_ID`: channel where the Leave Review panel should appear
   - `FEEDBACK_CHANNEL_ID`: public `#feedback` channel ID
   - `PRIVATE_CATEGORY_ID`: optional category for private review channels; use `0` if you don't need one
7. In Discord Developer Portal → Bot, enable **Message Content Intent**. The bot also needs the Server Members intent for channel permissions.
8. Invite the bot with the `bot` and `applications.commands` scopes and these permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Manage Channels
   - Manage Messages (optional; only needed if you later add moderation)
9. Start it:
   ```bash
   python bot.py
   ```
10. In your server, run `/setup_feedback` as an administrator. The panel will be posted to `PANEL_CHANNEL_ID`.

## Recommended server setup
- Create a public channel named `#feedback`.
- Create a channel for the feedback panel, e.g. `#leave-a-review`.
- Optional: create a private category for review channels and put its ID in `.env`.
- Test with a second Discord account before sharing the panel widely.

## How clients submit
1. Click **Leave Review**.
2. Open the private channel created for them.
3. Send the review text; attach an image in that same message if desired.
4. Click **Publish Review**.
5. The bot publishes an anonymous review and closes the private channel.

## Troubleshooting
- Slash command missing: wait a moment, restart the bot, and verify `GUILD_ID`.
- Cannot create private channel: ensure the bot has Manage Channels and View Channels.
- Cannot post review: ensure the bot can View Channel, Send Messages, and Embed Links in `#feedback`.
- Image does not display: use a direct image attachment, not an external link pasted into the message.
- Never share `.env` or your bot token with anyone. If the token leaks, reset it in the Developer Portal.
