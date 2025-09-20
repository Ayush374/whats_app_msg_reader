# # alerts_live.py
# import os
# import json
# import re
# import time
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

# # --------------- CONFIG -----------------
# LOGS_DIR = "./logs"
# ALERTS_FILE = "alerts.jsonl"
# VEHICLE_FILE = "vehicles.jsonl"
# CHECK_INTERVAL = 2   # seconds
# # ----------------------------------------

# # Track seen messages to avoid duplicates
# seen_messages = set()

# # Vehicle tracking state
# active_vehicles = {}  # { vehicle_number: entry_time }

# # Define rules
# RESCUE_PATTERN = re.compile(r"\brescue needed\b", re.IGNORECASE)
# MAP_PATTERN = re.compile(r"https?://(maps\.app\.goo\.gl|maps\.google\.com|goo\.gl/maps)/", re.IGNORECASE)

# ESCALATION_WORDS = {"missing", "lost", "waiting", "very long", "support", "help"}
# PAYMENT_WORDS = {"allowance", "travel", "petty cash"}

# # Vehicle regex patterns
# VEHICLE_PATTERNS = [
#     re.compile(r"\b\d{4}\b"),  # standalone 4-digit number
#     re.compile(r"\bKA[A-Z0-9]*\b", re.IGNORECASE),  # starts with KA
#     re.compile(r"[A-Z]{2}\d{1,2}[A-Z]{0,2}\d{3,4}", re.IGNORECASE),  # generic Indian plate
# ]


# def normalize_text(txt: str) -> str:
#     txt = txt.lower()
#     txt = re.sub(r"[@#]\w+", "", txt)  # remove mentions/hashtags
#     txt = re.sub(r"[^\w\s]", " ", txt)  # remove punctuation
#     return txt.strip()


# def extract_sender(time_field: str) -> str:
#     # e.g. "[11:32, 27/8/2025] Ayush Tulshan:"
#     m = re.search(r"\] (.*?):", time_field)
#     return m.group(1) if m else "Unknown"


# def classify_alert(text: str) -> str | None:
#     norm = normalize_text(text)

#     # Rescue Needed
#     if RESCUE_PATTERN.search(norm) or MAP_PATTERN.search(text):
#         return "Rescue Needed"

#     # Escalation
#     if text.strip() == "[Audio]":
#         return "Escalation"
#     for word in ESCALATION_WORDS:
#         if re.search(rf"\b{word}\b", norm):
#             return "Escalation"

#     # Payment Request
#     for word in PAYMENT_WORDS:
#         if re.search(rf"\b{word}\b", norm):
#             return "Payment Request"
#     if "[Image]" in text and "qr" in norm:
#         return "Payment Request"

#     return None


# # ---------------- VEHICLE FUNCTIONS ----------------
# def extract_vehicle_numbers(text: str):
#     vehicles = set()
#     for pattern in VEHICLE_PATTERNS:
#         matches = pattern.findall(text)
#         for m in matches:
#             vehicles.add(m.upper())
#     return list(vehicles)


# def handle_vehicle_event(vehicle: str, time_field: str):
#     """
#     Decide if it's entry or exit and save to vehicles.jsonl
#     """
#     if vehicle not in active_vehicles:
#         # First time → Entry
#         active_vehicles[vehicle] = time_field
#         print(f"🚗 [ENTRY] Vehicle {vehicle} at {time_field}")
#     else:
#         # Seen before → Exit
#         entry_time = active_vehicles[vehicle]
#         exit_time = time_field
#         record = {
#             "vehicle": vehicle,
#             "entry_time": entry_time,
#             "exit_time": exit_time
#         }
#         with open(VEHICLE_FILE, "a", encoding="utf-8") as vf:
#             vf.write(json.dumps(record, ensure_ascii=False) + "\n")
#         print(f"🚙 [EXIT] Vehicle {vehicle} at {time_field} (entered at {entry_time})")

#         # Remove so that next time it becomes ENTRY again
#         del active_vehicles[vehicle]
# # ---------------------------------------------------


# def process_file(filepath: str):
#     group_name = os.path.basename(filepath).replace(".json", "")
#     try:
#         with open(filepath, "r", encoding="utf-8") as f:
#             messages = json.load(f)
#     except Exception as e:
#         print(f"⚠️ Failed to load {filepath}: {e}")
#         return

#     for msg in messages:
#         time_field = msg.get("time", "")
#         text = msg.get("text", "")
#         sender = extract_sender(time_field)

#         key = (group_name, time_field, text)
#         if key in seen_messages:
#             continue  # already processed
#         seen_messages.add(key)

#         # Normal alerts
#         alert_type = classify_alert(text)
#         if alert_type:
#             alert_entry = {
#                 "group": group_name,
#                 "time": time_field,
#                 "sender": sender,
#                 "text": text,
#                 "alert_type": alert_type
#             }
#             print(f"🚨 [{alert_type}] in '{group_name}' by {sender} at {time_field} → {text}")
#             with open(ALERTS_FILE, "a", encoding="utf-8") as af:
#                 af.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")

#         # Vehicle events
#         vehicles = extract_vehicle_numbers(text)
#         for v in vehicles:
#             handle_vehicle_event(v, time_field)


# class LogHandler(FileSystemEventHandler):
#     def on_modified(self, event):
#         if event.is_directory:
#             return
#         if event.src_path.endswith(".json"):
#             process_file(event.src_path)


# def main():
#     print(f"👀 Watching folder: {LOGS_DIR} for new messages...")
#     event_handler = LogHandler()
#     observer = Observer()
#     observer.schedule(event_handler, LOGS_DIR, recursive=False)
#     observer.start()

#     try:
#         while True:
#             time.sleep(CHECK_INTERVAL)
#     except KeyboardInterrupt:
#         print("🛑 Stopped by user.")
#         observer.stop()
#     observer.join()


# if __name__ == "__main__":
#     main()

# alerts_live.py



import os
import json
import re
import time
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --------------- CONFIG -----------------
LOGS_DIR = "./logs"
ALERTS_FILE = "alerts.jsonl"
VEHICLE_FILE = "vehicles.jsonl"
CHECK_INTERVAL = 2   # seconds (loop sleep)
STALE_HOURS = 24     # hours before raising no-exit alert
# ----------------------------------------

# Track seen messages to avoid duplicates
seen_messages = set()

# Vehicle tracking state
# map vehicle_number -> (entry_time_str, entry_datetime)
active_vehicles = {}  # { vehicle_number: (entry_time_str, entry_dt) }

# Vehicles for which we've already raised the 24-hour alert
alerted_vehicles = set()

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


def parse_time_field(time_field: str) -> datetime | None:
    """
    Best-effort parse of the time string. Example formats handled:
      "[11:32, 27/8/2025] Name:"  -> "%H:%M, %d/%m/%Y"
    Falls back to None on failure (caller may use datetime.now()).
    """
    # try extract what's inside square brackets first
    m = re.search(r"\[(.*?)\]", time_field)
    timestr = m.group(1).strip() if m else time_field.strip()

    # candidate formats (add more here if you see different input)
    formats = [
        "%H:%M, %d/%m/%Y",
        "%H:%M, %d/%m/%y",
        "%d/%m/%Y, %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestr, fmt)
        except Exception:
            continue

    # try some lightweight tolerant parsing (swap day/month if needed)
    # split by comma and attempt join variations
    if "," in timestr:
        parts = [p.strip() for p in timestr.split(",")]
        if len(parts) >= 2:
            a, b = parts[0], parts[1]
            # attempt "time day/month/year"
            for fmt in ("%H:%M %d/%m/%Y", "%H:%M %d/%m/%y"):
                try:
                    return datetime.strptime(f"{a} {b}", fmt)
                except Exception:
                    pass

    # if all fails, return None (caller should handle fallback)
    return None


def handle_vehicle_event(vehicle: str, time_field: str):
    """
    Decide if it's entry or exit and save to vehicles.jsonl
    """
    entry_dt = parse_time_field(time_field)

    # preserve the original time string for records
    entry_time_str = time_field

    if vehicle not in active_vehicles:
        # First time → Entry
        # store tuple (entry_time_str, entry_dt)
        if entry_dt is None:
            entry_dt = datetime.now()
            # you may want to log a warning if parsing fails
            print(f"⚠️ Could not parse time '{time_field}' — using now() for vehicle {vehicle}")
        active_vehicles[vehicle] = (entry_time_str, entry_dt)
        # If vehicle was previously alerted for stale, clear so future entry can be tracked anew
        alerted_vehicles.discard(vehicle)
        print(f"🚗 [ENTRY] Vehicle {vehicle} at {entry_time_str}")
    else:
        # Seen before → Exit
        stored_entry_str, stored_entry_dt = active_vehicles[vehicle]
        exit_time_str = time_field
        exit_dt = entry_dt if entry_dt is not None else datetime.now()

        record = {
            "vehicle": vehicle,
            "entry_time": stored_entry_str,
            "exit_time": exit_time_str
        }
        try:
            with open(VEHICLE_FILE, "a", encoding="utf-8") as vf:
                vf.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ Failed writing vehicle record: {e}")

        print(f"🚙 [EXIT] Vehicle {vehicle} at {exit_time_str} (entered at {stored_entry_str})")

        # cleanup active and alert tracking
        if vehicle in alerted_vehicles:
            alerted_vehicles.discard(vehicle)
        del active_vehicles[vehicle]


def check_stale_vehicles():
    """
    Check active_vehicles and raise an alert if any have been inside longer than STALE_HOURS.
    Avoid duplicate alerts using alerted_vehicles set.
    """
    now = datetime.now()
    threshold = timedelta(hours=STALE_HOURS)
    for vehicle, (entry_str, entry_dt) in list(active_vehicles.items()):
        # If entry_dt somehow None, skip or consider it stale after some policy; here we treat it as non-stale.
        if not entry_dt:
            continue
        if vehicle in alerted_vehicles:
            continue
        if now - entry_dt > threshold:
            alert_entry = {
                "group": "vehicle_watch",
                "time": now.strftime("%H:%M, %d/%m/%Y"),
                "sender": "system",
                "text": f"Vehicle {vehicle} entered at {entry_str} but has no recorded exit after {STALE_HOURS} hours.",
                "alert_type": "No Exit 24h"
            }
            print(f"🔔 [No Exit {STALE_HOURS}h] Vehicle {vehicle} (entered {entry_str})")
            try:
                with open(ALERTS_FILE, "a", encoding="utf-8") as af:
                    af.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"⚠️ Failed writing stale vehicle alert: {e}")
            alerted_vehicles.add(vehicle)


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
            try:
                with open(ALERTS_FILE, "a", encoding="utf-8") as af:
                    af.write(json.dumps(alert_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"⚠️ Failed writing alert: {e}")

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
            # periodically check for stale vehicles
            check_stale_vehicles()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
