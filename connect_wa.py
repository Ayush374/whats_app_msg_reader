













from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import pandas as pd
import os
import re
import sys

# ------------ CONFIG ------------
GROUP_NAMES = [
    "Testing automation",
    "SD Tulshan Family",
    "Adarsh b'day party",
    "Tulshan Family"
]
USER_DATA_DIR = "./User_Data"
OUT_DIR = "./logs"      # per-group JSON files
POLL_SECS = 5           # pause between cycles
SEARCH_SETTLE = 1.2     # time to let results populate after typing
# --------------------------------

os.makedirs(OUT_DIR, exist_ok=True)

def sanitize_filename(name: str, max_len: int = 100) -> str:
    s = re.sub(r"[^\w\s.-]", "_", name).strip()
    s = re.sub(r"\s+", "_", s)
    return (s[:max_len] or "chat")

options = Options()
options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
driver = webdriver.Chrome(options=options)
driver.get("https://web.whatsapp.com/")

print("📲 Waiting for WhatsApp Web to load and login...")
WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true" and @data-tab]'))
)

seen_messages_by_group = {name: set() for name in GROUP_NAMES}
messages_log_by_group = {name: [] for name in GROUP_NAMES}

def get_search_box():
    return driver.find_element(By.XPATH, '//div[@contenteditable="true" and @data-tab]')

def clear_search():
    """Reliably clear WA search box (contenteditable)."""
    sb = get_search_box()
    sb.click()
    # JS clear
    driver.execute_script("arguments[0].textContent = '';", sb)
    time.sleep(0.05)
    # Key chord clear (handles ghost text)
    sb.send_keys(Keys.CONTROL, 'a')
    sb.send_keys(Keys.BACKSPACE)
    # Verify empty (retry once)
    txt = sb.get_attribute("textContent") or ""
    if txt.strip():
        driver.execute_script("arguments[0].textContent = '';", sb)
        sb.send_keys(Keys.CONTROL, 'a')
        sb.send_keys(Keys.BACKSPACE)
    time.sleep(0.1)

def open_group(group_name: str) -> bool:
    """Open a chat/group by searching its title; returns True when opened."""
    try:
        print(f"🔍 Searching for group: {group_name}")
        clear_search()
        sb = get_search_box()
        sb.click()
        sb.send_keys(group_name)
        time.sleep(SEARCH_SETTLE)

        # Try exact match first
        try:
            el = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, f'//span[@title="{group_name}"]'))
            )
            el.click()
        except Exception:
            # Try contains (case-sensitive per DOM)
            try:
                el = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, f'//span[contains(@title, "{group_name}")]'))
                )
                el.click()
            except Exception:
                # Last resort: click first result row
                try:
                    row = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, '//div[@role="grid"]//div[@tabindex="0" and @role="row"]'))
                    )
                    row.click()
                except Exception as e:
                    print(f"   ❌ No search result clickable for '{group_name}': {e}")
                    clear_search()
                    return False

        # Confirm header title changed
        try:
            title_el = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, '//header//span[@title]'))
            )
            opened = (title_el.get_attribute("title") or "").strip()
            if not opened:
                print("   ⚠️ Opened chat title empty; assuming failure.")
                clear_search()
                return False
            print(f"✅ Group '{opened}' opened.")
        finally:
            # Always clear so next search starts fresh
            clear_search()

        return True

    except Exception as e:
        print(f"❌ Failed to find/open '{group_name}': {e}")
        try:
            clear_search()
        except Exception:
            pass
        return False

def extract_messages_for_current_chat(group_name: str):
    """Extract messages from the currently open chat and update that group's log (your original logic)."""
    print(f"🔄 Checking for new messages in '{group_name}'...")
    messages = driver.find_elements(By.XPATH, '//div[contains(@class,"message-in") or contains(@class,"message-out")]')
    print(f"📨 Found {len(messages)} total messages in DOM.")

    seen_set = seen_messages_by_group[group_name]
    log_list = messages_log_by_group[group_name]

    for msg in messages:
        try:
            media_type = None
            caption_text = None

            # Media checks (same as your original)
            try:
                msg.find_element(By.XPATH, './/img[contains(@src, "blob:")]')
                media_type = "[Image]"
            except:
                pass

            try:
                if not media_type:
                    msg.find_element(By.XPATH, './/video')
                    media_type = "[Video]"
            except:
                pass

            try:
                if not media_type:
                    msg.find_element(By.XPATH, './/audio')
                    media_type = "[Audio]"
            except:
                pass

            try:
                if not media_type:
                    msg.find_element(By.XPATH, './/span[contains(@aria-label, "Document")]')
                    media_type = "[Document]"
            except:
                pass

            # Text/caption
            try:
                text_element = msg.find_element(By.XPATH, './/span[contains(@class,"selectable-text")]')
                caption_text = text_element.text.strip()
            except:
                caption_text = ""

            text = f"{media_type} {caption_text}".strip() if media_type else caption_text.strip()
            if not text:
                text = "[Unknown or Unsupported Message]"

            # Timestamp
            try:
                timestamp_element = msg.find_element(By.XPATH, './/div[contains(@data-pre-plain-text, "[")]')
                timestamp = timestamp_element.get_attribute("data-pre-plain-text").strip()
            except:
                timestamp = time.strftime("[%H:%M, %d/%m/%Y]")

            key = (timestamp, text)
            if key not in seen_set:
                print(f"🆕 New message in '{group_name}': {timestamp} {text}")
                seen_set.add(key)
                log_list.append({'time': timestamp, 'text': text})

        except Exception as e:
            print(f"⚠️ Skipping a message due to error: {e}")

def write_group_files(group_name: str):
    data = messages_log_by_group[group_name]
    safe = sanitize_filename(group_name)
    json_path = os.path.join(OUT_DIR, f"{safe}.json")
    xlsx_path = os.path.join(OUT_DIR, f"{safe}.xlsx")

    if data:
        print(f"💾 Writing {len(data)} messages for '{group_name}' → {json_path}")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        pd.DataFrame(data).to_excel(xlsx_path, index=False)
    else:
        print(f"📭 No messages collected yet for '{group_name}'.")

try:
    while True:
        print("🌀 ===== New cycle over all groups =====")
        for name in GROUP_NAMES:
            if open_group(name):
                extract_messages_for_current_chat(name)
                write_group_files(name)
                time.sleep(0.8)  # small gap between groups
        time.sleep(POLL_SECS)

except KeyboardInterrupt:
    print("🛑 Script manually stopped.")
    driver.quit()
    sys.exit(0)
