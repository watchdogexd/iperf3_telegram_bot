import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from iperf3 import run_iperf3
from config import BOT_TOKEN, ALLOWED_USER_IDS, PROXY_URL

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def iperf3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("You have no permission to execute the command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage:\n/iperf3 <server> [port] [time] [thread] [-R]\n"
            "e.g. /iperf3 1.1.1.1 5201 10 1 -R"
        )
        return

    server = context.args[0]
    nums = [int(arg) for arg in context.args[1:] if arg.isdigit()]
    reverse = "-R" in context.args[1:]

    port = nums[0] if len(nums) > 0 else None
    duration = nums[1] if len(nums) > 1 else None
    thread = nums[2] if len(nums) > 2 else None

    msg = await update.message.reply_text("⏱ currently running iperf3，please wait…")

    result = await run_iperf3(server, port, duration, thread, reverse)

    # Telegram message limit to 4096
    if len(result) > 4000:
        result = result[-4000:]

    await msg.edit_text(f"```\n{result}\n```", parse_mode="Markdown")

# prevent crash from network/proxy issues
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Exception: {context.error}")

# run application
def main():
    builder = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
    )

    if PROXY_URL:
        builder = builder.proxy(PROXY_URL)

    app = builder.build()
    app.add_handler(CommandHandler("iperf3", iperf3_handler))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()