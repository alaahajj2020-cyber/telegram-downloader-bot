import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ========== إعدادات البوت ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8737314688:AAEzvs7I1MTptuJbNPU7p20dmwhdDxHrSFM")
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ========== رسالة الترحيب ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت التحميل!\n\n"
        "📥 أرسل لي رابط أي فيديو من:\n"
        "  • YouTube\n"
        "  • TikTok\n"
        "  • Instagram\n"
        "  • Twitter/X\n"
        "  • وأكثر من 1000 موقع آخر!\n\n"
        "🔗 فقط الصق الرابط وأنا أتكفل بالباقي 😊"
    )

# ========== معالجة الروابط ==========
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # التحقق من أن الرسالة رابط
    if not url.startswith("http"):
        await update.message.reply_text("❗ الرجاء إرسال رابط صحيح يبدأ بـ http أو https")
        return

    # حفظ الرابط في context للاستخدام لاحقاً
    context.user_data["url"] = url

    # عرض خيارات التحميل
    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو (أفضل جودة)", callback_data="video_best"),
            InlineKeyboardButton("📱 فيديو (720p)", callback_data="video_720"),
        ],
        [
            InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data="audio_mp3"),
            InlineKeyboardButton("🎵 صوت (M4A)", callback_data="audio_m4a"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🔗 تم استلام الرابط!\n\nاختر صيغة التحميل:",
        reply_markup=reply_markup
    )

# ========== تنفيذ التحميل ==========
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get("url")

    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مجدداً.")
        return

    await query.edit_message_text("⏳ جاري التحميل... يرجى الانتظار")

    try:
        file_path = await asyncio.to_thread(download_media, url, choice)

        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)

            # تيليغرام يقبل ملفات حتى 50MB
            if file_size > 50 * 1024 * 1024:
                await query.edit_message_text(
                    "⚠️ الملف كبير جداً (أكثر من 50MB).\n"
                    "تيليغرام لا يسمح بإرسال ملفات أكبر من 50MB مجاناً.\n"
                    "جرب اختيار جودة أقل."
                )
                os.remove(file_path)
                return

            await query.edit_message_text("✅ اكتمل التحميل! جاري الإرسال...")

            with open(file_path, "rb") as f:
                if choice.startswith("audio"):
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=f,
                        caption="🎵 تم التحميل بنجاح!"
                    )
                else:
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=f,
                        caption="🎬 تم التحميل بنجاح!",
                        supports_streaming=True
                    )

            os.remove(file_path)
            await query.edit_message_text("✅ تم الإرسال بنجاح!")

        else:
            await query.edit_message_text("❌ فشل التحميل. تحقق من الرابط وحاول مجدداً.")

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ:\n{str(e)[:200]}")


# ========== دالة التحميل الفعلي ==========
def download_media(url: str, choice: str) -> str:
    output_template = os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s")

    if choice == "audio_mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
        }
    elif choice == "audio_m4a":
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
        }
    elif choice == "video_720":
        ydl_opts = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
        }
    else:  # video_best
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

        # للـ MP3 يتغير الامتداد بعد التحويل
        if choice == "audio_mp3":
            file_path = os.path.splitext(file_path)[0] + ".mp3"

        return file_path


# ========== تشغيل البوت ==========
def main():
    print("🤖 البوت يعمل... اضغط Ctrl+C لإيقافه")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))

    app.run_polling()

if __name__ == "__main__":
    main()
