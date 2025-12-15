from flask import Flask, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from threading import Thread, Lock
import time
import os
import hashlib
import re

# ======================
# 🔧 CONFIG
# ======================
LIVE_URL = "https://www.facebook.com/settatrakenkit/videos/869498375464135"
KEYWORDS = ["f1", "f2", "f3", "f4"]

# เก็บผลลัพธ์
results = {k: [] for k in KEYWORDS}
seen = set()

# lock กันข้อมูลชน
data_lock = Lock()

# ======================
# 🌐 FLASK
# ======================
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", keywords=KEYWORDS)

@app.route("/data")
def data():
    with data_lock:
        return jsonify(results)

# ======================
# 🤖 SELENIUM
# ======================
def selenium_worker():
    options = Options()
    options.page_load_strategy = "eager"

    profile_path = os.path.join(os.getcwd(), "facebook_profile")
    options.add_argument(f"user-data-dir={profile_path}")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=0")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    print("🔵 เปิด Facebook Live...")
    driver.get(LIVE_URL)

    print("⏳ รอ Live โหลด 30 วินาที...")
    time.sleep(30)

    print("✅ Selenium เริ่มดักคอมเมนต์")

    while True:
        try:
            driver.execute_script("window.scrollBy(0,500)")
            time.sleep(1)

            spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")

            for i in range(len(spans) - 1):
                try:
                    name = spans[i].text.strip()
                    msg = spans[i + 1].text.strip().lower()

                    if not name or not msg:
                        continue

                    uid = hashlib.md5(f"{name}|{msg}".encode()).hexdigest()
                    if uid in seen:
                        continue
                    seen.add(uid)

                    for k in KEYWORDS:
                        # match แบบทน: f1, f1 2ชิ้น, F1
                        if re.search(rf"\b{k}\b", msg):
                            with data_lock:
                                if name not in results[k]:
                                    results[k].append(name)
                            print(f"🎯 {k.upper()} ← {name} : {msg}")

                except StaleElementReferenceException:
                    # Facebook Live re-render → ข้ามรอบนี้
                    continue
                except Exception as e:
                    print("❌ COMMENT ERROR:", e)

            time.sleep(2)

        except Exception as e:
            print("❌ LOOP ERROR:", e)
            time.sleep(3)

# ======================
# 🚀 START
# ======================
if __name__ == "__main__":
    Thread(target=selenium_worker, daemon=True).start()
    print("🚀 Flask + Selenium พร้อมแล้ว")
    app.run(host="0.0.0.0", port=5000, debug=False)
