import json
from datetime import datetime

LOG_FILE = "negotiation_events.jsonl"  # Use .jsonl extension for line-delimited JSON

def log_event(event_type, data, log_mode="file", log_file=LOG_FILE, db_conn=None):
    """
    Logs an event to a file (default) or future SQL DB (if log_mode is 'sql').

    :param event_type: str, event type ('deal_closed', 'order_summary', etc.)
    :param data: dict, any fields for the event
    :param log_mode: 'file' or 'sql'
    :param log_file: str, path to the file (default: negotiation_events.jsonl)
    :param db_conn: DB connection for future use (optional)
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type
    }
    entry.update(data)
    if log_mode == "file":
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    elif log_mode == "sql" and db_conn:
        # --- Future placeholder for SQL logging ---
        # You would insert the `entry` dictionary as a row in your SQL table here
        pass
    else:
        raise ValueError("Unsupported log mode or missing db connection.")
