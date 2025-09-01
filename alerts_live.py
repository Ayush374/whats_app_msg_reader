# alerts_live.py
import os
import json
import re
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --------------- CONFIG -----------------
LOGS_DIR = "./logs"
ALERTS_FILE = "alerts.jsonl"
VEHICLE_FILE = "vehicles.jsonl"
CHECK_INTERVAL = 2   # seconds
# ----------------------------------------

# Track seen messages to avoid duplicates
seen_messages = set()

# Vehicle tracking state
active_vehicles = {}  # { vehicle_number: entry_time }

# Define rules
RESCUE_PATTERN = re.compile(r"\brescue needed\b", re.IGNORECASE)
MAP_PATTERN = re.compile(r"https?://(maps\.app\.goo\.gl|maps\.google\.com|goo\.gl/maps)/", re.IGNORECASE)

ESCALATION_WORDS = {"missing", "lost", "waiting", "very long", "support", "help"}
PAYMENT_WORDS = {"allowance", "travel", "petty cash"}

# Vehicle regex patterns
VEHICLE_PATTERNS = [
    re.compile(r"\b\d{4}\b"),  # standalone 4-digit number
    re.compile(r"\bKA[A-Z0-9]*\b", re.IGNORECASE),  # starts with KA
    re.compile(r"[A-Z]{2}\d{1,2}[A-Z]{0,2}\d{3,4}", re.IGNORECASE),  # generic Indian plate
]


def normalize_text(txt: str) -> str:
    txt = txt.lower()
    txt = re.sub(r"[@#]\w+", "", txt)  # remove mentions/hashtags
    txt = re.sub(r"[^\w\s]", " ", txt)  # remove punctuation
    return txt.strip()


def extract_sender(time_field: str) -> str:
    # e.g. "[11:32, 27/8/2025] Ayush Tulshan:"
    m = re.search(r"\] (.*?):", time_field)
    return m.group(1) if m else "Unknown"


def classify_alert(text: str) -> str | None:
    norm = normalize_text(text)

    # Rescue Needed
    if RESCUE_PATTERN.search(norm) or MAP_PATTERN.search(text):
        return "Rescue Needed"

    # Escalation
    if text.strip() == "[Audio]":
        return "Escalation"
    for word in ESCALATION_WORDS:
        if re.search(rf"\b{word}\b", norm):
            return "Escalation"

    # Payment Request
    for word in PAYMENT_WORDS:
        if re.search(rf"\b{word}\b", norm):
            return "Payment Request"
    if "[Image]" in text and "qr" in norm:
        return "Payment Request"

    return None


# ---------------- VEHICLE FUNCTIONS ----------------
def extract_vehicle_numbers(text: str):
    vehicles = set()
    for pattern in VEHICLE_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            vehicles.add(m.upper())
    return list(vehicles)


def handle_vehicle_event(vehicle: str, time_field: str):
    """
    Decide if it's entry or exit and save to vehicles.jsonl
    """
    if vehicle not in active_vehicles:
        # First time → Entry
        active_vehicles[vehicle] = time_field
        print(f"🚗 [ENTRY] Vehicle {vehicle} at {time_field}")
    else:
        # Seen before → Exit
        entry_time = active_vehicles[vehicle]
        exit_time = time_field
        record = {
            "vehicle": vehicle,
            "entry_time": entry_time,
            "exit_time": exit_time
        }
        with open(VEHICLE_FILE, "a", encoding="utf-8") as vf:
            vf.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"🚙 [EXIT] Vehicle {vehicle} at {time_field} (entered at {entry_time})")

        # Remove so that next time it becomes ENTRY again
        del active_vehicles[vehicle]
# ---------------------------------------------------


def process_file(filepath: str):
    group_name = os.path.basename(filepath).replace(".json", "")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            messages = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load {filepath}: {e}")
        return

    for msg in messages:
        time_field = msg.get("time", "")
        text = msg.get("text", "")
        sender = extract_sender(time_field)

        key = (group_name, time_field, text)
        if key in seen_messages:
            continue  # already processed
        seen_messages.add(key)

        # Normal alerts
        alert_type = classify_alert(text)
        if alert_type:
            alert_entry = {
                "group": group_name,
                "time": time_field,
                "sender": sender,
                "text": text,
                "alert_type": alert_type
            }
            print(f"🚨 [{alert_type}] in '{group_name}' by {sender} at {time_field} → {text}")
            with open(ALERTS_FILE, "a", encoding="utf-8") as af:
                af.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")

        # Vehicle events
        vehicles = extract_vehicle_numbers(text)
        for v in vehicles:
            handle_vehicle_event(v, time_field)


class LogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".json"):
            process_file(event.src_path)


def main():
    print(f"👀 Watching folder: {LOGS_DIR} for new messages...")
    event_handler = LogHandler()
    observer = Observer()
    observer.schedule(event_handler, LOGS_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
