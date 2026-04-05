"""Deliver results to Discord/Slack/generic webhooks."""
import json
import urllib.request
from datetime import datetime, timezone

def send_webhook(url: str, task_name: str, status: str,
                 message: str = "", duration: float = 0,
                 cost_usd: float = 0):
    if "discord.com" in url:
        _send_discord(url, task_name, status, message, duration, cost_usd)
    elif "hooks.slack.com" in url:
        _send_slack(url, task_name, status, message, duration, cost_usd)
    else:
        _send_generic(url, task_name, status, message, duration, cost_usd)

def _send_discord(url, name, status, msg, dur, cost):
    color = {"success": 0x00FF00, "failed": 0xFF0000,
             "timeout": 0xFFAA00}.get(status, 0x808080)
    payload = {"embeds": [{
        "title": f"{'✓' if status == 'success' else '✗'} {name}",
        "color": color,
        "fields": [
            {"name": "Status", "value": status, "inline": True},
            {"name": "Duration", "value": f"{dur:.1f}s", "inline": True},
            {"name": "Cost", "value": f"${cost:.4f}", "inline": True},
        ],
        "description": msg[:2000] if msg else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]}
    _post_json(url, payload)

def _send_slack(url, name, status, msg, dur, cost):
    emoji = ":white_check_mark:" if status == "success" else ":x:"
    payload = {"blocks": [
        {"type": "header", "text": {
            "type": "plain_text", "text": f"{emoji} {name}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Status:* {status}"},
            {"type": "mrkdwn", "text": f"*Duration:* {dur:.1f}s"},
            {"type": "mrkdwn", "text": f"*Cost:* ${cost:.4f}"},
        ]},
    ]}
    if msg:
        payload["blocks"].append({"type": "section", "text": {
            "type": "mrkdwn", "text": msg[:2000]}})
    _post_json(url, payload)

def _send_generic(url, name, status, msg, dur, cost):
    _post_json(url, {
        "task": name, "status": status, "message": msg,
        "duration_seconds": dur, "cost_usd": cost,
        "timestamp": datetime.now(timezone.utc).isoformat()})

def _post_json(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        from claude_scheduler.console import console
        console.print(f"[red]Webhook failed: {e}[/red]")
