import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from dotenv import load_dotenv

from app.utils import check_breaches, load_json, save_json

load_dotenv()

WATCHLIST_FILE = "data/watchlist.json"
CHECK_HISTORY_FILE = "data/watchlist_checks.json"

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL", EMAIL_ADDRESS)

def send_email_alert(query, new_sources):
    body = f"⚠️ New breach(es) detected for: {query}\n\n"
    for source in new_sources:
        body += f"- {source['name']} ({source['date']})\n"

    msg = MIMEText(body)
    msg["Subject"] = f"[Breach Alert] {query} - {len(new_sources)} new breaches"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def check_watchlist():
    watchlist = load_json(WATCHLIST_FILE, [])
    history = load_json(CHECK_HISTORY_FILE, {})
    updated = False

    for query in watchlist:
        result = check_breaches(query)
        if result.get("success"):
            sources = result["sources"]
            cleaned = [s for s in sources if s.get("name") and s.get("date")]
            prev_sources = history.get(query, [])
            prev_names = {s["name"] for s in prev_sources}
            new_sources = [s for s in cleaned if s["name"] not in prev_names]

            if new_sources:
                send_email_alert(query, new_sources)
                history[query] = cleaned
                updated = True
        else:
            print(f"Error checking {query}: {result.get('error')}")

    if updated:
        save_json(CHECK_HISTORY_FILE, history)

if __name__ == "__main__":
    print(f"🔄 Running watchlist check at {datetime.now().isoformat()}")
    check_watchlist()
