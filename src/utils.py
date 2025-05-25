# Utility functions for the banking system
import json
import os
import uuid
from decimal import Decimal
from datetime import datetime
import config

# Custom JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def setup_directories():
    """Creates necessary data directories if they don't exist."""
    os.makedirs(config.CUSTOMERS_DIR, exist_ok=True)
    os.makedirs(config.ACCOUNTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(config.LEDGER_FILE), exist_ok=True)
    print("Directories checked/created.")

def load_json(file_path):
    """Loads data from a JSON file. Returns None if file not found."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Use Decimal for numerical strings that look like numbers
            return json.load(f, parse_float=Decimal, parse_int=Decimal)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}")
        return None

def save_json(file_path, data):
    """Saves data to a JSON file using the custom Decimal encoder."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=DecimalEncoder, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")

def generate_id(prefix):
    """Generates a truly unique ID using UUID."""
    unique_part = str(uuid.uuid4())
    return f"{prefix}-{unique_part}"

def parse_datetime(dt_str):
    """Safely parses an ISO datetime string."""
    if isinstance(dt_str, datetime):
        return dt_str  # Already a datetime object
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not parse date string '{dt_str}'. Returning None.")
        return None