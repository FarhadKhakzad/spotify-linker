# ربات Spotify Linker

[![CI](https://github.com/FarhadKhakzad/spotify-linker/actions/workflows/ci.yml/badge.svg)](https://github.com/FarhadKhakzad/spotify-linker/actions/workflows/ci.yml)

> زبان‌ها: [English](README.md) · [فارسی](README.fa.md)

این پروژه پیام‌های کانال تلگرام را بررسی می‌کند و در صورت اشاره به آهنگ، لینک رسمی اسپاتیفای را پیدا کرده و پاسخ می‌دهد. توسعهٔ مخزن به‌صورت مرحله‌به‌مرحله و با تمرکز بر ابزارهای حرفه‌ای انجام می‌شود.

## قابلیت‌های اصلی

- وب‌اپلیکیشن FastAPI برای دریافت وبهوک تلگرام.
- کلاینت قدرتمند Spotify Web API برای جست‌وجوی دقیق آهنگ‌ها.
- لایهٔ پیکربندی مبتنی بر Pydantic Settings همراه با پشتیبانی از فایل‌های dotenv.
- تست‌های خودکار کامل (۱۰۰٪ پوشش) و CI با GitHub Actions.

## شروع سریع

### پیش‌نیازها

- پایتون ۳٫۱۱ یا جدیدتر
- ابزار [Poetry](https://python-poetry.org/) برای مدیریت وابستگی‌ها *(یا استفاده از `pip` و فایل `requirements.txt` برای نصب ساده)*

### نصب

```bash
poetry install
cp env.example .env  # پس از کپی، مقادیر را تکمیل کنید
```

> اگر توضیحات انگلیسی را ترجیح می‌دهید، فایل `.env.template` همان مقادیر را با توضیحات انگلیسی فراهم می‌کند.

<details>
<summary>در صورت تمایل به استفاده از pip</summary>

```bash
python -m venv .venv
.venv\Scripts\activate  # روی ویندوز
source .venv/bin/activate  # روی macOS/Linux
pip install -r requirements.txt
# برای ابزارهای توسعه: pip install -r requirements-dev.txt
cp env.example .env
# یا cp .env.template .env
```

</details>

### اجرای محیط توسعه

```bash
poetry run uvicorn spotify_linker.main:app --reload
```

<details>
<summary>در صورت عدم استفاده از Poetry</summary>

```bash
uvicorn spotify_linker.main:app --reload
```

</details>

### کنترل کیفیت

```bash
poetry run ruff check .
poetry run pylint src tests
poetry run pytest
```

<details>
<summary>بدون Poetry</summary>

```bash
# مطمئن شوید بسته‌های requirements-dev.txt نصب شده‌اند
ruff check .
pylint src tests
pytest
```

</details>

دستور `pytest` به‌صورت خودکار گزارش پوشش کد تولید می‌کند تا اطمینان بگیرید استاندارد ۱۰۰٪ حفظ شده است.

## راهنمای پیکربندی

از فایل نمونهٔ `env.example` یا `.env.template` یک نسخهٔ `.env` بسازید و متغیرهای زیر را مقداردهی کنید:

| متغیر | ضروری؟ | توضیح |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | بله | توکن ربات تلگرام (BotFather). |
| `TELEGRAM_CHANNEL_ID` | بله | شناسهٔ عددی کانال (برای کانال‌ها مقدار منفی است). |
| `SPOTIFY_CLIENT_ID` | بله | شناسهٔ برنامه در داشبورد توسعه‌دهندگان اسپاتیفای. |
| `SPOTIFY_CLIENT_SECRET` | بله | کلید محرمانهٔ اسپاتیفای برای دریافت توکن. |
| `SPOTIFY_REDIRECT_URI` | اختیاری | برای سناریوهای OAuth آینده نگهداری می‌شود. |

> ⚠️ **نکتهٔ امنیتی:** فایل `.env` یا هرگونه credential واقعی را هرگز در مخزن عمومی قرار ندهید. از مدیر رمز یا Secret Store پلتفرم میزبانی استفاده کنید.

## نقشهٔ راه

1. ✅ ایجاد اسکلت پروژه، مدیریت تنظیمات و راه‌اندازی CI.
2. ✅ پیاده‌سازی وبهوک تلگرام و لاگ‌گیری کامل.
3. ✅ کلاینت اسپاتیفای با فرایند client-credentials.
4. ✅ تبدیل پیام‌های تلگرام به کاندید آهنگ استاندارد.
5. ✅ جست‌وجوی دقیق اسپاتیفای و قالب‌بندی پاسخ.
6. ⏭ استقرار خودکار و پیکربندی HTTPS/Webhook.

## مشارکت

- لطفاً پیش از ارسال تغییرات، راهنمای کامل مشارکت را در [CONTRIBUTING.md](CONTRIBUTING.md) مطالعه کنید.
- خلاصهٔ روند: مخزن را fork کنید، روی شاخهٔ جداگانه کار انجام دهید، پیش از Pull Request حتماً `ruff`، `pytest` و گزارش پوشش را اجرا کنید.
- توضیحات Pull Request را به انگلیسی بنویسید و در صورت تمایل یادداشت فارسی نیز اضافه کنید.

## مجوز

این پروژه تحت مجوز MIT منتشر شده است. متن کامل مجوز در فایل [`LICENSE`](LICENSE) موجود است.
