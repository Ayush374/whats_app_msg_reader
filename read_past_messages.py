
"""
Simple WhatsApp Web Message Reader - 48 Hours
Reads messages from the last 48 hours with reliable scrolling and storage.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import pandas as pd
import os
import re
from datetime import datetime, timedelta
import sys

# Configuration
GROUP_NAMES = [
    "Testing automation",
    "SD Tulshan Family",
    "Adarsh b'day party",
    "Tulshan Family",
    "Jubiliant POC",
    "backchodi"
]

USER_DATA_DIR = "./User_Data"
OUT_DIR = "./logs"
SCROLL_PAUSE_TIME = 2
MAX_SCROLL_ATTEMPTS = 75  # Increased for 48 hours

# Create output directory
os.makedirs(OUT_DIR, exist_ok=True)

def print_status(message):
    """Print status with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def sanitize_filename(name: str) -> str:
    """Convert group name to safe filename"""
    return re.sub(r'[^\w\s-]', '', name).strip()[:50].replace(' ', '_')

def parse_timestamp(timestamp_str):
    """Parse WhatsApp timestamp to datetime"""
    if not timestamp_str:
        return None
    
    # Extract timestamp from format like "[14:30, 6/9/2025]"
    match = re.search(r'\[(\d{1,2}:\d{2}),?\s*(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{1,2}/\d{2})\]', timestamp_str)
    if not match:
        return None
    
    time_part = match.group(1)
    date_part = match.group(2)
    
    # Handle different date formats
    try:
        if len(date_part.split('/')[-1]) == 2:
            # Add 2000 to 2-digit years
            date_parts = date_part.split('/')
            date_part = f"{date_parts[0]}/{date_parts[1]}/20{date_parts[2]}"
        
        datetime_str = f"{date_part} {time_part}"
        return datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
    except:
        try:
            datetime_str = f"{date_part} {time_part}"
            return datetime.strptime(datetime_str, "%m/%d/%Y %H:%M")
        except:
            return None

def is_within_48_hours(msg_datetime):
    """Check if message is within last 48 hours"""
    if not msg_datetime:
        return True  # Include if we can't parse timestamp
    
    now = datetime.now()
    forty_eight_hours_ago = now - timedelta(hours=48)
    return msg_datetime >= forty_eight_hours_ago

def setup_driver():
    """Setup Chrome driver with WhatsApp Web"""
    options = Options()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com/")
    
    print_status("Waiting for WhatsApp Web to load...")
    print_status("Please scan QR code if needed...")
    
    # Wait for WhatsApp to load
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab]'))
    )
    
    print_status("WhatsApp Web loaded successfully!")
    return driver

def search_and_open_chat(driver, group_name):
    """Search for and open a chat/group"""
    try:
        print_status(f"Opening chat: {group_name}")
        
        # Find search box
        search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab]')
        search_box.click()
        time.sleep(0.5)
        
        # Properly clear the search box (WhatsApp uses contenteditable)
        # Method 1: Select all and delete
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(0.2)
        
        # Method 2: JavaScript clear (backup)
        driver.execute_script("arguments[0].textContent = '';", search_box)
        time.sleep(0.2)
        
        # Method 3: Clear any remaining content
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.3)
        
        # Now type the group name
        search_box.send_keys(group_name)
        time.sleep(2)
        
        # Click on the chat
        try:
            chat_element = driver.find_element(By.XPATH, f'//span[@title="{group_name}"]')
            chat_element.click()
        except:
            # Try clicking first search result
            try:
                first_result = driver.find_element(By.XPATH, '//div[@role="listitem"]')
                first_result.click()
            except:
                print_status(f"Could not find chat: {group_name}")
                return False
        
        time.sleep(2)
        print_status(f"Successfully opened: {group_name}")
        return True
        
    except Exception as e:
        print_status(f"Error opening {group_name}: {str(e)}")
        return False

def scroll_to_load_messages(driver):
    """Scroll up to load older messages"""
    print_status("Scrolling to load messages from last 48 hours...")
    
    # Find the message container
    try:
        message_container = driver.find_element(By.XPATH, '//div[contains(@class, "copyable-area")]')
    except:
        try:
            message_container = driver.find_element(By.XPATH, '//div[@data-testid="conversation-panel-body"]')
        except:
            message_container = driver.find_element(By.TAG_NAME, 'body')
    
    scroll_attempts = 0
    last_message_count = 0
    
    while scroll_attempts < MAX_SCROLL_ATTEMPTS:
        # Scroll up
        try:
            # Try multiple scroll methods
            driver.execute_script("arguments[0].scrollTop = 0", message_container)
            time.sleep(0.5)
            
            # Also try scrolling with Page Up
            message_container.send_keys(Keys.PAGE_UP)
            time.sleep(0.5)
            
            # Mouse wheel scroll up
            ActionChains(driver).move_to_element(message_container).scroll_by_amount(0, -500).perform()
            
        except:
            # Fallback scroll method
            driver.execute_script("window.scrollTo(0, 0)")
        
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Check if we loaded more messages
        current_messages = driver.find_elements(By.XPATH, '//div[contains(@class,"message-")]')
        current_count = len(current_messages)
        
        if current_count > last_message_count:
            last_message_count = current_count
            scroll_attempts = 0  # Reset counter if we're loading new messages
            print_status(f"Loaded {current_count} messages so far...")
        else:
            scroll_attempts += 1
        
        # Check if we have messages from 48+ hours ago
        if current_count > 20:  # Only check after we have some messages
            timestamps = driver.find_elements(By.XPATH, '//div[@data-pre-plain-text]')
            if timestamps:
                oldest_timestamp = timestamps[0].get_attribute('data-pre-plain-text')
                oldest_time = parse_timestamp(oldest_timestamp)
                if oldest_time and not is_within_48_hours(oldest_time):
                    print_status("Found messages older than 48 hours, stopping scroll")
                    break
    
    print_status(f"Finished scrolling. Found {last_message_count} total messages")

def extract_messages(driver, group_name):
    """Extract messages from current chat with enhanced detection"""
    print_status(f"Extracting messages from {group_name}...")
    
    messages = []
    
    # Find all message elements with multiple selectors
    message_elements = []
    message_selectors = [
        '//div[contains(@class,"message-in") or contains(@class,"message-out")]',
        '//div[contains(@class,"_1-lx")]',  # Alternative message selector
        '//div[@data-pre-plain-text]/parent::*',  # Elements with timestamp data
        '//div[contains(@class,"focusable-list-item")]'  # Another WhatsApp message class
    ]
    
    for selector in message_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if len(elements) > len(message_elements):
                message_elements = elements
                print_status(f"Using selector: {selector} - found {len(elements)} elements")
        except:
            continue
    
    print_status(f"Found {len(message_elements)} message elements")
    
    # Also try to find all timestamp elements to ensure we're getting everything
    timestamp_elements = driver.find_elements(By.XPATH, '//div[@data-pre-plain-text]')
    print_status(f"Found {len(timestamp_elements)} timestamp elements")
    
    processed_timestamps = set()  # Avoid duplicates
    
    for i, msg_element in enumerate(message_elements):
        try:
            # Get timestamp with enhanced detection
            timestamp_raw = ""
            msg_time = None
            
            # Try multiple methods to get timestamp
            timestamp_methods = [
                lambda: msg_element.find_element(By.XPATH, './/div[@data-pre-plain-text]'),
                lambda: msg_element.find_element(By.XPATH, 'ancestor::div[@data-pre-plain-text]'),
                lambda: msg_element.find_element(By.XPATH, 'descendant::div[@data-pre-plain-text]'),
                lambda: msg_element.find_element(By.XPATH, 'following-sibling::div[@data-pre-plain-text]'),
                lambda: msg_element.find_element(By.XPATH, 'preceding-sibling::div[@data-pre-plain-text]')
            ]
            
            for method in timestamp_methods:
                try:
                    timestamp_element = method()
                    timestamp_raw = timestamp_element.get_attribute('data-pre-plain-text')
                    if timestamp_raw and timestamp_raw not in processed_timestamps:
                        msg_time = parse_timestamp(timestamp_raw)
                        processed_timestamps.add(timestamp_raw)
                        break
                except:
                    continue
            
            if not timestamp_raw:
                timestamp_raw = f"[Unknown time - {i}]"
            
            # Enhanced 48-hour filtering
            if msg_time and not is_within_48_hours(msg_time):
                continue
            
            # Get message text with enhanced detection
            message_text = ""
            text_selectors = [
                './/span[contains(@class,"selectable-text")]',
                './/span[@dir="ltr"]',
                './/div[contains(@class,"selectable-text")]',
                './/span[not(@class)]',  # Span without specific class
            ]
            
            for text_selector in text_selectors:
                try:
                    text_elements = msg_element.find_elements(By.XPATH, text_selector)
                    if text_elements:
                        text_parts = []
                        for text_elem in text_elements:
                            text_content = text_elem.text.strip()
                            if text_content and text_content not in text_parts:
                                text_parts.append(text_content)
                        message_text = " ".join(text_parts)
                        if message_text:
                            break
                except:
                    continue
            
            # Fallback to element text
            if not message_text:
                try:
                    message_text = msg_element.text.strip()
                except:
                    message_text = "[Could not extract message text]"
            
            # Enhanced media detection
            media_type = ""
            media_checks = [
                ('.//img[contains(@src, "blob:")]', "[Image]"),
                ('.//video', "[Video]"),
                ('.//audio', "[Audio]"),
                ('.//span[contains(@aria-label, "Document")]', "[Document]"),
                ('.//div[contains(@aria-label, "Photo")]', "[Image]"),
                ('.//div[contains(@aria-label, "Video")]', "[Video]"),
                ('.//div[contains(@aria-label, "Audio")]', "[Audio]"),
                ('.//span[contains(text(), "document")]', "[Document]"),
                ('.//span[contains(@class, "emoji")]', "[Emoji]")
            ]
            
            for xpath, media_label in media_checks:
                try:
                    if msg_element.find_elements(By.XPATH, xpath):
                        media_type = media_label
                        break
                except:
                    continue
            
            # Combine media type and text
            full_text = f"{media_type} {message_text}".strip() if media_type else message_text
            
            # Only save if we have meaningful content
            if (full_text and full_text != "[Could not extract message text]" and 
                timestamp_raw and len(full_text) > 0):
                
                message_data = {
                    'timestamp': timestamp_raw,
                    'datetime': msg_time.isoformat() if msg_time else None,
                    'text': full_text,
                    'media_type': media_type,
                    'group': group_name
                }
                messages.append(message_data)
        
        except Exception as e:
            print_status(f"Error processing message {i}: {str(e)}")
            continue
    
    # Filter messages to ensure 48-hour window
    filtered_messages = []
    for msg in messages:
        if msg['datetime']:
            try:
                msg_dt = datetime.fromisoformat(msg['datetime'])
                if is_within_48_hours(msg_dt):
                    filtered_messages.append(msg)
            except:
                filtered_messages.append(msg)  # Include if can't parse
        else:
            filtered_messages.append(msg)  # Include if no datetime
    
    print_status(f"Extracted {len(filtered_messages)} messages from last 48 hours (filtered from {len(messages)} total)")
    return filtered_messages

def save_messages(messages, group_name):
    """Save messages to JSON and Excel files"""
    if not messages:
        print_status(f"No messages to save for {group_name}")
        return
    
    safe_name = sanitize_filename(group_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON file
    json_filename = f"{safe_name}_messages_{timestamp}.json"
    json_path = os.path.join(OUT_DIR, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    
    # Excel file
    excel_filename = f"{safe_name}_messages_{timestamp}.xlsx"
    excel_path = os.path.join(OUT_DIR, excel_filename)
    
    try:
        df = pd.DataFrame(messages)
        df.to_excel(excel_path, index=False)
        print_status(f"Saved {len(messages)} messages to {json_filename} and {excel_filename}")
    except Exception as e:
        print_status(f"Could not save Excel file: {str(e)}")
        print_status(f"JSON file saved: {json_filename}")

def main():
    """Main function to run the WhatsApp message reader"""
    print_status("Starting WhatsApp Message Reader (48 hours)")
    print_status("=" * 50)
    
    # Setup driver
    try:
        driver = setup_driver()
    except Exception as e:
        print_status(f"Failed to setup driver: {str(e)}")
        return
    
    try:
        all_messages = []
        
        for group_name in GROUP_NAMES:
            try:
                print_status(f"\n--- Processing {group_name} ---")
                
                # Open chat
                if not search_and_open_chat(driver, group_name):
                    continue
                
                # Choose scrolling method
                print_status(f"\nChoose scrolling method for {group_name}:")
                print_status("1. Auto-scroll (improved algorithm)")
                print_status("2. Manual scroll (you do it, script extracts)")
                choice = input("Enter choice (1 or 2, or press Enter for auto): ").strip()
                
                if choice == "2":
                    manual_scroll_prompt(driver, group_name)
                else:
                    # Automated scrolling
                    scroll_to_load_messages(driver)
                
                # Extract messages
                messages = extract_messages(driver, group_name)
                
                # Save messages
                save_messages(messages, group_name)
                
                # Add to combined list
                all_messages.extend(messages)
                
                print_status(f"Completed {group_name}")
                time.sleep(2)  # Brief pause between groups
                
            except Exception as e:
                print_status(f"Error processing {group_name}: {str(e)}")
                continue
        
        # Save combined file
        if all_messages:
            print_status(f"\n--- Saving Combined File ---")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_filename = f"all_messages_48h_{timestamp}.json"
            combined_path = os.path.join(OUT_DIR, combined_filename)
            
            with open(combined_path, 'w', encoding='utf-8') as f:
                json.dump(all_messages, f, indent=2, ensure_ascii=False)
            
            print_status(f"Saved combined file with {len(all_messages)} total messages")
        
        print_status("\n" + "=" * 50)
        print_status("WhatsApp Message Reader completed successfully!")
        print_status(f"Check the '{OUT_DIR}' folder for output files")
        
    except KeyboardInterrupt:
        print_status("\nStopped by user")
    except Exception as e:
        print_status(f"Unexpected error: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()