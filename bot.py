"""
Telegram bot that sends one section (from sections.json) to all subscribers,
three times a week, in order.

Setup:
    1. pip install -r requirements.txt
    2. python extract_sections.py "YourBigFile.docx"   -> creates sections.json
    3. Create a .env file next to this script containing:
           BOT_TOKEN=your-real-token-here
    4. python bot.py

Files this script creates/uses next to itself:
    sections.json    - produced by extract_sections.py (read-only here)
    subscribers.json - list of chat_ids who ran /start
    state.json        - which section index goes out next, and which was
                         last sent (used to catch up new subscribers)
"""

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

# sections.json is static content pushed with your code, so it stays next
# to bot.py. subscribers.json and state.json change while the bot runs and
# must survive redeploys, so they live in DATA_DIR instead -- on Railway,
# mount your persistent Volume at this same path (see README).
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SECTIONS_FILE = BASE_DIR / "sections.json"
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"
STATE_FILE = DATA_DIR / "state.json"

# ---- Schedule config -------------------------------------------------
# Every day at 8:00 AM, Addis Ababa time.
SEND_DAYS = (0, 1, 2, 3, 4, 5, 6)  # Mon=0 ... Sun=6 -- all seven days
SEND_HOUR = 8
SEND_MINUTE = 0
TIMEZONE = "Africa/Addis_Ababa"

WELCOME_TEXT = (
    "ይህ በአባ ይትባረክ ወልደሚካኤል የተላለፈ የልዑል እግዚአብሔርና የሚራዉ መልክት የሚተላለፍበት ገጽ ነው። "
)

load_dotenv(BASE_DIR / ".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")


# ---- small JSON helpers ------------------------------------------------
def _load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def _save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_subscribers():
    return set(_load_json(SUBSCRIBERS_FILE, []))


def save_subscribers(subs):
    _save_json(SUBSCRIBERS_FILE, sorted(subs))


def load_state():
    return _load_json(STATE_FILE, {"next_index": 0, "last_sent_index": None})


def save_state(state):
    _save_json(STATE_FILE, state)


def load_sections():
    if not SECTIONS_FILE.exists():
        return []
    return _load_json(SECTIONS_FILE, [])


# ---- command handlers ---------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    is_new = chat_id not in subs
    if is_new:
        subs.add(chat_id)
        save_subscribers(subs)
        logger.info("New subscriber: %s", chat_id)

    await update.message.reply_text(WELCOME_TEXT)

    # Catch the new subscriber up with whatever section was most recently
    # sent, so they don't have to wait until tomorrow's scheduled send.
    if is_new:
        sections = load_sections()
        state = load_state()
        last_idx = state.get("last_sent_index")
        if sections and last_idx is not None:
            section = sections[last_idx % len(sections)]
            try:
                await context.bot.send_message(chat_id=chat_id, text=section["content"])
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to send catch-up section to %s: %s", chat_id, exc)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    if chat_id in subs:
        subs.discard(chat_id)
        save_subscribers(subs)
    await update.message.reply_text("ከአባልነት ወጥተዋል። ደግመው ለመቀላቀል /start ይጫኑ።")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin/debug helper: shows how many sections and subscribers exist,
    and which section will go out next."""
    sections = load_sections()
    subs = load_subscribers()
    state = load_state()
    idx = state["next_index"] % max(len(sections), 1)
    next_num = sections[idx]["number"] if sections else "N/A"
    await update.message.reply_text(
        f"ክፍሎች: {len(sections)}\nደንበኞች: {len(subs)}\nቀጣይ የሚላከው ክፍል ቁጥር: {next_num}"
    )


# ---- scheduled job --------------------------------------------------------
async def send_next_section(context: ContextTypes.DEFAULT_TYPE):
    sections = load_sections()
    if not sections:
        logger.warning("send_next_section: sections.json is empty or missing.")
        return

    subs = load_subscribers()
    if not subs:
        logger.info("send_next_section: no subscribers yet, skipping.")
        return

    state = load_state()
    idx = state["next_index"] % len(sections)
    section = sections[idx]

    for chat_id in list(subs):
        try:
            await context.bot.send_message(chat_id=chat_id, text=section["content"])
        except Exception as exc:  # noqa: BLE001 - keep bot alive if one send fails
            logger.error("Failed to send to %s: %s", chat_id, exc)

    # advance to next section, wrapping back to the start when the book ends
    state["last_sent_index"] = idx
    state["next_index"] = (idx + 1) % len(sections)
    save_state(state)
    logger.info("Sent section %s to %d subscribers.", section["number"], len(subs))


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN not found. Create a .env file next to bot.py containing:\n"
            "BOT_TOKEN=your-real-token-here"
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))

    # schedule the 3x/week send
    for day in SEND_DAYS:
        app.job_queue.run_daily(
            send_next_section,
            time=datetime.time(
                hour=SEND_HOUR,
                minute=SEND_MINUTE,
                tzinfo=ZoneInfo(TIMEZONE),
            ),
            days=(day,),
        )

    # Python 3.14 removed the old "auto-create an event loop for the main
    # thread" behavior that python-telegram-bot's run_polling() still
    # relies on internally. Creating and registering one ourselves first
    # works around it. Harmless no-op on older Python versions.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    print("Bot starting... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
