import logging
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================================================
# توکن ربات (شما)
# =========================================================
TOKEN = "8892121107:AAEzUqfJGUc8Ncg6X-McmDerKTyl0ETblRc"

# =========================================================
# هدرهای درخواست (برای شبیه‌سازی مرورگر)
# =========================================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

# آدرس‌های سایت TGJU
URLS = {
    "dollar": "https://www.tgju.org/profile/price_dollar_rl",
    "euro": "https://www.tgju.org/profile/price_eur",
    "gold": "https://www.tgju.org/profile/geram18",
}

# =========================================================
# تنظیمات لاگ (برای مشاهده خطاها)
# =========================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================================================
# تبدیل اعداد فارسی/عربی به انگلیسی
# =========================================================
def normalize_digits(text: str) -> str:
    translation_table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return text.translate(translation_table)

# =========================================================
# استخراج عدد از متن (با پشتیبانی از کاما و نقطه)
# =========================================================
def parse_number(text: str):
    text = normalize_digits(text)
    text = text.replace(",", "").replace("٬", "").replace(" ", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    value = match.group(0)
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return None

# =========================================================
# دریافت قیمت از صفحه TGJU
# =========================================================
def get_price_from_page(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # جستجوی عبارت "نرخ فعلی"
        for element in soup.find_all(string=re.compile("نرخ فعلی|Last")):
            parent_text = element.parent.get_text(" ", strip=True)
            parent_text = normalize_digits(parent_text)
            match = re.search(r"(?:نرخ فعلی|Last)\s*[:：]?\s*([\d,٬]+(?:\.\d+)?)", parent_text)
            if match:
                price = parse_number(match.group(1))
                if price is not None:
                    return price

        # روش پشتیبان: جستجوی کل صفحه
        full_text = normalize_digits(soup.get_text(" ", strip=True))
        match = re.search(r"نرخ فعلی\s*[:：]\s*([\d,٬]+(?:\.\d+)?)", full_text)
        if match:
            price = parse_number(match.group(1))
            if price is not None:
                return price

        raise ValueError("قیمت در صفحه پیدا نشد.")
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت از {url}: {e}")
        return None

# =========================================================
# دریافت همه قیمت‌ها
# =========================================================
def get_all_prices():
    prices = {}
    for key, url in URLS.items():
        prices[key] = get_price_from_page(url)
    return prices

# =========================================================
# فرمت کردن اعداد با کاما
# =========================================================
def format_price(value):
    if value is None:
        return "❌ ناموجود"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"

# =========================================================
# ساخت دکمه‌های شیشه‌ای (منوی اصلی)
# =========================================================
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💵 دلار", callback_data="dollar")],
        [InlineKeyboardButton("💶 یورو", callback_data="euro")],
        [InlineKeyboardButton("🥇 طلای ۱۸ عیار", callback_data="gold")],
        [InlineKeyboardButton("🔄 بروزرسانی همه", callback_data="all")],
    ]
    return InlineKeyboardMarkup(keyboard)

# =========================================================
# ساخت پیام قیمت‌ها
# =========================================================
def create_price_message(prices):
    now = datetime.now().strftime("%H:%M:%S")
    dollar = format_price(prices.get("dollar"))
    euro = format_price(prices.get("euro"))
    gold = format_price(prices.get("gold"))
    return (
        "📊 <b>قیمت لحظه‌ای بازار</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>دلار آزاد:</b>\n"
        f" {dollar} ریال\n\n"
        f"💶 <b>یورو:</b>\n"
        f" {euro} ریال\n\n"
        f"🥇 <b>طلای ۱۸ عیار:</b>\n"
        f" {gold} ریال\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 زمان بروزرسانی: {now}\n"
        "📌 منبع: TGJU"
    )

# =========================================================
# هندلر /start
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام!\n\n"
        "به ربات قیمت‌یابی خوش آمدی.\n"
        "یکی از گزینه‌های زیر را انتخاب کن:",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )

# =========================================================
# نمایش قیمت‌ها
# =========================================================
async def show_prices(query, price_type=None):
    prices = get_all_prices()

    if price_type is None:  # نمایش همه
        text = create_price_message(prices)
    else:
        names = {"dollar": "💵 دلار آزاد", "euro": "💶 یورو", "gold": "🥇 طلای ۱۸ عیار"}
        unit = {"dollar": "ریال", "euro": "ریال", "gold": "ریال / گرم"}
        name = names.get(price_type, "نامشخص")
        price = format_price(prices.get(price_type))
        unit_text = unit.get(price_type, "")
        text = (
            f"<b>{name}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 قیمت فعلی:\n"
            f"<b>{price}</b> {unit_text}\n\n"
            f"🕐 بروزرسانی: {datetime.now().strftime('%H:%M:%S')}\n"
            "📌 منبع: TGJU"
        )

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

# =========================================================
# هندلر دکمه‌ها
# =========================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "all":
        await show_prices(query)
    elif data in ("dollar", "euro", "gold"):
        await show_prices(query, data)

# =========================================================
# هندلر خطاهای ناشناخته
# =========================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطا: {context.error}")

# =========================================================
# تابع اصلی
# =========================================================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print("🤖 ربات قیمت‌یابی روشن شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# =========================================================
# اجرا
# =========================================================
if __name__ == "__main__":
    main()
