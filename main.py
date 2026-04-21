#!/usr/bin/env python3
"""
Seller AI — 24/7 AI Business Manager
Manages your Amazon & Myntra t-shirt business automatically.
"""
import sys
import time
import threading
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import config
from database.db import init_db
from scheduler.jobs import create_scheduler
from notifications.telegram import notify
from utils.logger import get_logger

console = Console()
logger = get_logger("main")


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🛍️  Seller AI — 24/7 Business Manager[/bold cyan]\n"
        "[dim]Amazon & Myntra T-Shirt Business Automation[/dim]",
        border_style="cyan"
    ))


def check_config():
    missing = config.validate()
    if missing:
        table = Table(title="⚠️  Missing Configuration", border_style="yellow")
        table.add_column("Variable", style="red")
        table.add_column("How to set it", style="dim")
        for var in missing:
            table.add_row(var, f"Add to your .env file")
        console.print(table)
        if "ANTHROPIC_API_KEY" in missing or "AMAZON_CLIENT_ID" in missing:
            console.print("[red]Critical credentials missing. Please set them in .env and restart.[/red]")
            sys.exit(1)


def run_dashboard():
    from dashboard.app import app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.DASHBOARD_PORT,
        log_level="error",
    )


def main():
    print_banner()
    check_config()

    console.print("[cyan]Initializing database...[/cyan]")
    init_db()
    console.print("[green]✓ Database ready[/green]")

    console.print("[cyan]Starting AI agents...[/cyan]")
    scheduler = create_scheduler()
    scheduler.start()
    console.print("[green]✓ All agents scheduled and running[/green]")

    console.print(f"[cyan]Starting dashboard on port {config.DASHBOARD_PORT}...[/cyan]")
    dash_thread = threading.Thread(target=run_dashboard, daemon=True)
    dash_thread.start()
    console.print(f"[green]✓ Dashboard live at http://localhost:{config.DASHBOARD_PORT}[/green]")

    notify(
        "🚀 *Seller AI Started*\n\n"
        "All agents are now running 24/7:\n"
        "• 📦 Order Monitor (every 15 min)\n"
        "• 🗃️ Inventory Sync (every hour)\n"
        "• 💬 Customer Support (every 10 min)\n"
        "• 💰 Pricing Optimizer (every 2 hours)\n"
        "• ↩️ Returns Manager (every 30 min)\n"
        "• 📊 Daily Report (8:00 AM IST)\n"
        "• 🛡️ Account Health (9 AM & 6 PM IST)"
    )

    console.print("\n[bold green]✅ Seller AI is running! Press Ctrl+C to stop.[/bold green]\n")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Shutting down agents...[/yellow]")
        scheduler.shutdown()
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    main()
