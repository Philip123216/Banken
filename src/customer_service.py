# src/customer_service.py
from datetime import datetime
import os
import json
from . import config
from .utils import generate_id, save_json, load_json

def create_customer(name, address, birth_date_str):
    """Creates a new customer profile and saves it."""
    customer_id = generate_id("C")
    now_iso = datetime.now().isoformat()
    customer_data = {
        "customer_id": customer_id,
        "name": name,
        "address": address,
        "birth_date": birth_date_str,  # Expecting YYYY-MM-DD string
        "created_at": now_iso,
        "status": "active"
    }
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    save_json(file_path, customer_data)
    print(f"Customer created: {customer_id}")
    return customer_data

def update_customer(customer_id, updates):
    """Updates customer details. 'updates' is a dict of fields to change."""
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    customer_data = load_json(file_path)
    if not customer_data:
        print(f"Error: Customer {customer_id} not found.")
        return None

    allowed_updates = ["name", "address", "status"]  # Birth date usually not changed
    for key, value in updates.items():
        if key in allowed_updates:
            customer_data[key] = value
        else:
            print(f"Warning: Update key '{key}' not allowed or not found.")

    save_json(file_path, customer_data)
    print(f"Customer {customer_id} updated.")
    return customer_data

def get_customer(customer_id):
    """Retrieves customer information."""
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    return load_json(file_path)