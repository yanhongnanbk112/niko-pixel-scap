import os
import json
import csv
import re
from datetime import datetime

# --- IMPORT ---
from curl_cffi import requests as cffi 
import requests 
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

load_dotenv()
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- CẤU HÌNH ---
HISTORY_FILE = 'price_history.json'
LOG_FILE = 'price_log.csv'
TARGET_URL = "https://sonpixel.vn/danh-muc-san-pham/dien-thoai/google-pixel/pixel-9-series/pixel-9/"
IMG_FILE = 'price_chart.png'

# --- DANH SÁCH SELECTOR DỰ PHÒNG ---
# Nếu cái đầu không được, nó sẽ thử cái thứ 2, thứ 3...
PRODUCT_SELECTORS = [
    '.product-small',                # Theme Flatsome hiện tại (SonPixel đang dùng)
    '.type-product',                 # Chuẩn WooCommerce (Dự phòng nếu đổi theme)
    '.product-item',                 # Một số theme phổ biến khác
    'div[class*="product"]'          # Quét tất cả thẻ div có chữ "product" (Tuyệt chiêu cuối)
]

def send_telegram_alert(message):
    """Gửi cảnh báo lỗi khẩn cấp"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    print(f"🚨 Gửi cảnh báo Telegram: {message}")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        # Thêm emoji 🆘 để dễ nhận biết
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': f"🆘 BOT CRITICAL:\n{message}", 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def send_telegram_photo(caption):
    # (Giữ nguyên code cũ)
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(IMG_FILE, 'rb') as photo:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
            files = {'photo': photo}
            requests.post(url, data=payload, files=files, timeout=20)
    except Exception as e: print(f"Lỗi gửi ảnh: {e}")

def send_telegram_text(message):
    # (Giữ nguyên code cũ)
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def clean_price(price_str):
    if not price_str: return 0
    digits = re.sub(r'\D', '', price_str)
    return int(digits) if digits else 0

def log_to_csv(title, price):
    # (Giữ nguyên code cũ)
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(['Date', 'Product', 'Price'])
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([now, title, price])

def draw_chart():
    # (Giữ nguyên code cũ)
    try:
        if not os.path.exists(LOG_FILE): return False
        df = pd.read_csv(LOG_FILE)
        df['Date'] = pd.to_datetime(df['Date'])
        plt.figure(figsize=(10, 5))
        for product_name in df['Product'].unique():
            subset = df[df['Product'] == product_name].sort_values('Date')
            if len(subset) > 0:
                plt.plot(subset['Date'], subset['Price'], marker='o', label=product_name)
        plt.title('Biến động giá Pixel 9')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize='small')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        plt.gcf().autofmt_xdate()
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        plt.tight_layout()
        plt.savefig(IMG_FILE)
        plt.close()
        return True
    except: return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=2)

def main():
    print(f"🚀 Đang chạy SonPixel Scraper (Robust Mode)...")
    
    # 1. VƯỢT TƯỜNG LỬA
    browsers = ["chrome110", "edge101", "safari15_5"]
    response = None
    
    for browser in browsers:
        try:
            response = cffi.get(
                TARGET_URL, 
                impersonate=browser, 
                headers={"Referer": "https://www.google.com/"},
                timeout=30
            )
            if response.status_code == 200:
                break 
        except: pass

    if not response or response.status_code != 200:
        print("❌ LỖI MẠNG/403.")
        send_telegram_alert("Bot không thể truy cập vào SonPixel (Lỗi mạng hoặc bị chặn IP).")
        return

    # 2. XỬ LÝ HTML THÔNG MINH (Smart Selectors)
    soup = BeautifulSoup(response.content, 'html.parser')
    products = []
    
    # --- CHIẾN THUẬT LỐP DỰ PHÒNG ---
    used_selector = ""
    for selector in PRODUCT_SELECTORS:
        found_items = soup.select(selector)
        if len(found_items) > 0:
            products = found_items
            used_selector = selector
            print(f"✅ Đã tìm thấy dữ liệu bằng selector: '{selector}'")
            break
    
    # --- CHIẾN THUẬT CHIM HOÀNG YẾN (Báo động khi mất dấu) ---
    if len(products) == 0:
        print("❌ KHÔNG TÌM THẤY SẢN PHẨM NÀO!")
        # Lưu file HTML lỗi lại để debug (nếu chạy local)
        with open("error_page.html", "wb") as f: f.write(response.content)
        
        send_telegram_alert(
            "⚠️ Layout web đã thay đổi!\n"
            "Bot không tìm thấy sản phẩm nào cả.\n"
            "Hãy kiểm tra lại class CSS trên SonPixel."
        )
        return

    history = load_history()
    report_lines = []
    seen_titles = set()

    for product in products:
        try:
            # Tìm tiêu đề (Thử nhiều class tiêu đề khác nhau)
            title_el = product.select_one('.woocommerce-loop-product__title, .product-title, h3')
            if not title_el: continue
            title = title_el.get_text().strip()

            if title in seen_titles: continue 
            seen_titles.add(title)

            if "Pixel 9" not in title or "Pro" in title or "Lock" in title: continue

            # Tìm giá (Thử nhiều class giá khác nhau)
            price_el = product.select_one('.price .woocommerce-Price-amount bdi, .price, .amount')
            price = clean_price(price_el.get_text() if price_el else "0")

            # --- CHIẾN THUẬT KIỂM TRA TỈNH TÁO ---
            # Giá Pixel 9 không thể nào dưới 2 triệu hoặc trên 50 triệu được
            if price < 2000000 or price > 50000000:
                print(f"   ⚠️ Bỏ qua giá ảo: {title} - {price}")
                continue

            print(f"   ✅ {title}: {price:,} đ")
            log_to_csv(title, price)
            report_lines.append(f"📱 **{title}**: {price:,} đ")
            history[title] = price
            
        except Exception as e: 
            print(f"⚠️ Lỗi parse 1 item: {e}")
            continue

    save_history(history)

    # 3. GỬI BÁO CÁO
    if report_lines:
        print("🚀 Đang gửi báo cáo...")
        has_chart = draw_chart()
        caption = (
            f"📊 **BÁO CÁO GIÁ SONPIXEL**\n"
            "--------------------------------\n" 
            + "\n".join(report_lines) 
            + f"\n--------------------------------\n👉 [Xem ngay]({TARGET_URL})"
        )
        if has_chart: send_telegram_photo(caption)
        else: send_telegram_text(caption)
    else:
        # Trường hợp tìm thấy HTML nhưng lọc từ khóa "Pixel 9" xong không còn gì
        # Vẫn nên cảnh báo nhẹ
        print("⚠️ Không có Pixel 9 nào.")
        send_telegram_text("🤖 Bot đã quét xong nhưng không thấy dòng 'Pixel 9' nào (Có thể shop hết hàng hoặc đổi tên).")

    print("✅ Hoàn tất.")

if __name__ == "__main__":
    main()