import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================================================
# توکن ربات (همون روش ساده)
# =========================================================
TOKEN = "8892121107:AAEzUqfJGUc8Ncg6X-McmDerKTyl0ETblRc"

# =========================================================
# هدرهای درخواست (اصلاح شده)
# =========================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

# =========================================================
# آدرس‌های TGJU (اصلاح شده)
# =========================================================
URLS = {
    "dollar": "https://www.tgju.org/profile/price_dollar_rl",
    "euro": "https://www.tgju.org/profile/price_eur",
    "gold": "https://www.tgju.org/profile/geram18",
}

# =========================================================
# لاگ (برای دیدن خطاها)
# =========================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
# تبدیل اعداد فارسی به انگلیسی
# =========================================================
def normalize_digits(text: str) -> str:
    translation_table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return text.translate(translation_table)

def parse_number(text: str):
    text = normalize_digits(text).replace(",", "").replace("٬", "").replace(" ", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0)) if "." in match.group(0) else int(match.group(0))
    except ValueError:
        return None

def get_price_from_page(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup.find_all(string=re.compile("نرخ فعلی|Last")):
            parent_text = normalize_digits(element.parent.get_text(" ", strip=True))
            match = re.search(r"(?:نرخ فعلی|Last)\s*[:：]?\s*([\d,٬]+(?:\.\d+)?)", parent_text)
            if match:
                price = parse_number(match.group(1))
                if price is not None:
                    return price
        full_text = normalize_digits(soup.get_text(" ", strip=True))
        match = re.search(r"نرخ فعلی\s*[:：]\s*([\d,٬]+(?:\.\d+)?)", full_text)
        if match:
            price = parse_number(match.group(1))
            if price is not None:
                return price
        raise ValueError("قیمت پیدا نشد.")
    except Exception as e:
        logger.error(f"خطا: {e}")
        return None

def get_all_prices():
    prices = {}
    for key, url in URLS.items():
        prices[key] = get_price_from_page(url)
    return prices

def format_price(value):
    if value is None:
        return "❌ ناموجود"
    return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💵 دلار", callback_data="dollar")],
        [InlineKeyboardButton("💶 یورو", callback_data="euro")],
        [InlineKeyboardButton("🥇 طلای ۱۸ عیار", callback_data="gold")],
        [InlineKeyboardButton("🔄 بروزرسانی همه", callback_data="all")],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_price_message(prices):
    now = datetime.now().strftime("%H:%M:%S")
    return (
        "📊 <b>قیمت لحظه‌ای بازار</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>دلار آزاد:</b>\n {format_price(prices.get('dollar'))} ریال\n\n"
        f"💶 <b>یورو:</b>\n {format_price(prices.get('euro'))} ریال\n\n"
        f"🥇 <b>طلای ۱۸ عیار:</b>\n {format_price(prices.get('gold'))} ریال\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 زمان بروزرسانی: {now}\n📌 منبع: TGJU"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! به ربات قیمت‌یابی خوش آمدی.\nیکی از گزینه‌های زیر را انتخاب کن:",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )

async def show_prices(query, price_type=None):
    prices = get_all_prices()
    if price_type is None:
        text = create_price_message(prices)
    else:
        names = {"dollar": "💵 دلار", "euro": "💶 یورو", "gold": "🥇 طلا"}
        unit = {"dollar": "ریال", "euro": "ریال", "gold": "ریال/گرم"}
        text = (
            f"<b>{names[price_type]}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 قیمت: <b>{format_price(prices.get(price_type))}</b> {unit[price_type]}\n\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
    await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "all":
        await show_prices(query)
    else:
        await show_prices(query, query.data)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطا: {context.error}")

def main():
    print("ربات قیمت‌یابی روشن شد ✅")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
