import os
import asyncio
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

TOKEN = os.environ["BOT_TOKEN"]
MAX_SIZE = 45 * 1024 * 1024

ALLOWED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
    "instagram.com",
    "www.instagram.com",
}


def valid_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and any(
                host == domain or host.endswith("." + domain)
                for domain in ALLOWED_DOMAINS
            )
        )
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎬 Video", callback_data="video"),
            InlineKeyboardButton("🎵 MP3", callback_data="audio"),
        ],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ]

    await update.message.reply_text(
        "🇪🇹 Welcome to Premium Downloader Bot!\n\n"
        "YouTube, TikTok ወይም Instagram ሊንክ ላክ።\n"
        "ከዚያ Video ወይም MP3 ምረጥ።",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data in ("video", "audio"):
        context.user_data["mode"] = query.data
        await query.message.reply_text(
            "🔗 አሁን የቪዲዮውን ሊንክ ላክ።"
        )
    else:
        await query.message.reply_text(
            "YouTube, TikTok ወይም Instagram ሊንክ ላክ።"
        )


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()

    if not valid_url(url):
        await update.message.reply_text(
            "❌ ከYouTube, TikTok ወይም Instagram ትክክለኛ HTTPS ሊንክ ላክ።"
        )
        return

    mode = context.user_data.get("mode", "video")
    msg = await update.message.reply_text("⏳ በማውረድ ላይ ነው...")

    try:
        with tempfile.TemporaryDirectory() as folder:
            opts = {
                "outtmpl": f"{folder}/%(title).60s.%(ext)s",
                "noplaylist": True,
                "max_filesize": MAX_SIZE,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
            }

            if mode == "audio":
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }]
            else:
                opts["format"] = (
                    "best[height<=720][ext=mp4]/"
                    "best[height<=720]/best"
                ]

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(opts).download([url]),
            )

            files = [
                p for p in Path(folder).iterdir()
                if p.is_file()
            ]

            if not files:
                raise RuntimeError("File not found")

            path = max(files, key=lambda p: p.stat().st_size)

            if path.stat().st_size > MAX_SIZE:
                raise RuntimeError("File too large")

            with path.open("rb") as media:
                if mode == "audio":
                    await update.message.reply_audio(
                        audio=media,
                        filename="audio.mp3",
                    )
                else:
                    await update.message.reply_document(
                        document=media,
                        filename=path.name,
                    )

        await msg.edit_text("✅ ማውረዱ ተጠናቋል!")

    except Exception:
        await msg.edit_text(
            "❌ ማውረድ አልተሳካም።\n"
            "ሊንኩን አረጋግጥ ወይም ሌላ ሊንክ ሞክር።"
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, download)
    )

    print("Premium Downloader Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
