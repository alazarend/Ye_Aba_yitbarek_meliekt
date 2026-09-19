from telegram import update
from telegram.ext import applicationbuilder,commandhandler, contextTypes
TOKEN="8472047358:AAFQQJz09nnOo7eSdaE1MV6Xo5lmVW26-yYf"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
      "ይህ በአባ ይትባረክ ወልደሥላሴ የተላለፈ የልዑል እግዚአብሔርና የሠራዊቱ መልእክት የሚተላለፍበት ገጽ ነው፡፡ "
          )



   if __name__ == "__main__":
    print("starting bot...")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

