#!/usr/bin/env python3
import html
import logging
import os
import re
import sys
from typing import List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
  Application,
  ApplicationBuilder,
  CallbackQueryHandler,
  CommandHandler,
  ContextTypes,
  MessageHandler,
  filters,
)

LOGGER = logging.getLogger("bot")

# Matches lines like: 100082.connect.garena.com/:username:password
PAIR_PATTERN = re.compile(
  r"(?i)100082\.connect\.garena\.com\s*/\s*:\s*([^:\s]+)\s*:\s*([^\s]+)"
)

# Optional: base URL of your copy page, e.g. https://your-vercel.vercel.app
COPY_BASE_URL = os.getenv("COPY_BASE_URL", "")


def extract_pairs(text: str) -> List[Tuple[str, str]]:
  pairs: List[Tuple[str, str]] = []
  for m in PAIR_PATTERN.finditer(text or ""):
    username = m.group(1).strip()
    password = m.group(2).strip()
    if username and password:
      pairs.append((username, password))
  return pairs


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  msg = (
    "Send lines like:\n"
    "100082.connect.garena.com/:username:password\n\n"
    "I will reply with each username:password and buttons."
  )
  await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


def build_kb(text: str) -> InlineKeyboardMarkup:
  buttons = [
    [InlineKeyboardButton("Copy", callback_data="copy"),
     InlineKeyboardButton("Delete", callback_data="delete")]
  ]
  if COPY_BASE_URL:
    from urllib.parse import quote
    # If your copy page is at the root (e.g. Vercel index.html), this works:
    url = f"{COPY_BASE_URL}/?t={quote(text)}"
    buttons.append([InlineKeyboardButton("Open Copy Link", url=url)])
  return InlineKeyboardMarkup(buttons)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  message = update.effective_message
  text = message.text or ""
  pairs = extract_pairs(text)
  if not pairs:
    return
  for username, password in pairs:
    pair = f"{username}:{password}"
    content = f"<code>{html.escape(pair)}</code>"
    await message.reply_text(
      content,
      parse_mode=ParseMode.HTML,
      reply_markup=build_kb(pair),
      disable_web_page_preview=True,
    )


async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  query = update.callback_query
  if not query:
    return
  await query.answer()

  data = query.data or ""
  chat_id = query.message.chat.id if query.message else None
  message_id = query.message.message_id if query.message else None
  text = query.message.text if query.message else None

  if data == "copy" and chat_id and text:
    # Re-send same content (no buttons) so you can long-press to copy
    await context.bot.send_message(
      chat_id=chat_id,
      text=text,
      parse_mode=ParseMode.HTML,
      disable_web_page_preview=True,
    )
    return

  if data == "delete" and chat_id and message_id:
    try:
      await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as exc:
      LOGGER.warning("Failed to delete message: %s", exc)
    return


def main() -> None:
  logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

  token = os.getenv("TELEGRAM_BOT_TOKEN")
  if not token:
    print("ERROR: TELEGRAM_BOT_TOKEN env var is not set.", file=sys.stderr)
    sys.exit(2)

  app: Application = ApplicationBuilder().token(token).build()

  app.add_handler(CommandHandler("start", cmd_start))
  app.add_handler(CallbackQueryHandler(on_cb))
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

  # Synchronous; manages its own event loop (fixes the Termux error)
  app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()