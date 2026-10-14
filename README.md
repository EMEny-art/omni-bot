# Omni Bot

Discord bot with moderation, economy, tickets, verification, level system, and quiz.

## Features
- Moderation tools (`/admin_panel`)
- Ticket system (`/ticket_setup`)
- Verification panel (`/verify_setup`)
- Economy system (`/work`, `/daily`, `/balance`, `/shop`, `/buy`)
- Levels and XP (`on_message`)
- Quiz reward system (`/quiz`)
- Anti-link moderation and anti-raid detection

## Setup
1. Create a `.env` file based on `.env.example`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the bot:
   ```bash
   python bot.py
   ```

## Important
Update the Discord IDs and role IDs in `bot.py` before running the bot in production.
