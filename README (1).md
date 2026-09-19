# Telegram Section-Broadcast Bot

Sends one numbered section of your Word document to all subscribers,
three times a week (Mon/Wed/Fri, 09:00 Addis Ababa time by default).

## How section-splitting works

`extract_sections.py` scans your `.docx` and treats any paragraph that
**starts with an Arabic number** (1, 2, 3 ... 10 ...) as the start of a
new section. Everything after it (until the next numbered paragraph)
becomes that section's message text.

So your Word file just needs each section header on its own paragraph,
starting with the number, e.g.:

```
1. የመጀመሪያው ክፍል ርዕስ
... paragraph text ...
... more text ...

2. ሁለተኛው ክፍል ርዕስ
... paragraph text ...
```

Sections are then **sorted numerically** (1, 2, ... 10, 11) before being
saved — so even if they're out of order in the Word file, they'll still
be sent in the right sequence. The script also warns you if:
- a section number appears twice, or
- a number in the sequence seems to be missing (e.g. it finds 1, 2, 4
  but not 3) — usually a sign a heading wasn't formatted quite right.

Orange coloring/highlighting is fine to keep for readability in Word,
but the script does not depend on the color — only the number. This
is more reliable than color detection, which breaks easily if the
file is edited or re-saved by a different program.

## Setup

1. **Regenerate your bot token first** — the one in your screenshot is
   public now. Go to @BotFather → `/revoke` (or `/token`) to get a new one.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Extract your sections:
   ```
   python extract_sections.py "C:\path\to\YourBigFile.docx"
   ```
   This creates `sections.json`. Check the console output — it lists
   every section number found, so you can confirm nothing was missed
   or merged wrong before going live.

4. Create your `.env` file (copy `.env.example` → `.env`) and put your
   **new** token in it:
   ```
   BOT_TOKEN=123456:your-new-token
   ```
   `.env` is what keeps the token out of your source code — don't
   commit it or screenshot it.

5. Run the bot:
   ```
   python bot.py
   ```

## Commands (for your subscribers)

- `/start` — subscribes the user and sends your Amharic welcome message
- `/stop` — unsubscribes
- `/status` — (useful for you too) shows section count, subscriber count,
  and which section number goes out next

## Changing the schedule

At the top of `bot.py`:

```python
SEND_DAYS = (0, 2, 4)   # Mon=0 ... Sun=6 -> currently Mon/Wed/Fri
SEND_HOUR = 9
SEND_MINUTE = 0
TIMEZONE = "Africa/Addis_Ababa"
```

Edit these to whatever days/time you want.

## Data files (created automatically, next to bot.py)

- `subscribers.json` — chat IDs of everyone who has run `/start`
- `state.json` — index of the next section to send (so restarting the
  bot doesn't resend or skip sections)

Once the last section is sent, it loops back to section ፩ automatically.
If you'd rather it stop at the end instead of looping, say so and I'll
change that one line.

## Keeping it running

`python bot.py` only runs while your terminal/VS Code is open. For it
to keep sending on schedule when your PC is off, you'll eventually want
to host it somewhere (a small VPS, Railway, PythonAnywhere, etc.) — happy
to walk through that when you're ready.
