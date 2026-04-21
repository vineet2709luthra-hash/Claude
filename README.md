# 🛍️ Seller AI — 24/7 AI Business Manager

An AI system that runs your Amazon & Myntra t-shirt business **automatically**, 24 hours a day. Powered by Claude AI.

---

## What It Does

| Agent | What It Handles | Frequency |
|-------|----------------|-----------|
| 📦 **Order Agent** | Detects new orders, flags issues, alerts you | Every 15 min |
| 🗃️ **Inventory Agent** | Syncs stock levels, warns when low | Every hour |
| 💬 **Support Agent** | Reads & auto-replies to customer messages | Every 10 min |
| 💰 **Pricing Agent** | Adjusts prices based on stock & competition | Every 2 hours |
| ↩️ **Returns Agent** | Auto-approves/rejects return requests | Every 30 min |
| 📊 **Analytics Agent** | Sends daily business report to Telegram | 8:00 AM daily |
| 🛡️ **Account Agent** | Monitors account health & policy compliance | 9 AM & 6 PM |

All alerts and reports are sent to your **Telegram** in real time.

---

## Setup (Step by Step)

### Step 1 — Install Python
Make sure you have Python 3.11+. Check with:
```bash
python --version
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Set up your credentials
```bash
cp .env.example .env
```
Open `.env` and fill in:
- **ANTHROPIC_API_KEY** → Get from https://console.anthropic.com
- **AMAZON_*** → From Amazon Seller Central Developer Console
- **MYNTRA_*** → From Myntra Seller Portal API section
- **TELEGRAM_*** → Create a bot via @BotFather on Telegram

### Step 4 — Set up Telegram Bot (for alerts)
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`, follow the steps, copy the **token**
3. Paste it as `TELEGRAM_BOT_TOKEN` in your `.env`
4. Search for **@userinfobot** on Telegram, it will tell you your Chat ID
5. Paste it as `TELEGRAM_CHAT_ID` in your `.env`

### Step 5 — Run the system
```bash
python main.py
```

### Step 6 — View the dashboard
Open your browser: **http://localhost:8000**

---

## Getting Amazon SP-API Credentials

1. Go to **Seller Central → Apps & Services → Develop Apps**
2. Click **Register now** to become a developer
3. Create a new app → save your **Client ID** and **Client Secret**
4. Authorize the app to get your **Refresh Token**
5. Your **Seller ID** is under Account Info → Business Info (Merchant Token)
6. **Marketplace ID** for India: `A21TJRUUN4KGV`

---

## Getting Myntra Seller API Credentials

1. Log in to **Myntra Seller Portal** (seller.myntra.com)
2. Go to **Settings → API Access** or contact your Myntra account manager
3. Request API access and you'll receive your **API Key** and **Secret**

---

## Project Structure

```
├── main.py                  # Entry point — start everything here
├── config.py                # All settings from .env
├── agents/                  # AI agents (the "employees")
│   ├── order_agent.py
│   ├── inventory_agent.py
│   ├── support_agent.py
│   ├── pricing_agent.py
│   ├── returns_agent.py
│   ├── analytics_agent.py
│   └── account_agent.py
├── integrations/
│   ├── amazon/              # Amazon SP-API calls
│   └── myntra/              # Myntra Seller API calls
├── database/                # SQLite database (orders, inventory, logs)
├── notifications/           # Telegram alerts
├── scheduler/               # 24/7 job scheduler
├── dashboard/               # Web dashboard (FastAPI)
└── .env.example             # Copy to .env and fill in your keys
```

---

## Running 24/7 on a Server

To run non-stop on a Linux server/VPS:
```bash
# Install screen or tmux
sudo apt install screen

# Start in a persistent session
screen -S seller-ai
python main.py
# Press Ctrl+A then D to detach
```

Or use systemd / Docker for production deployments.
