# Time-related functions for the banking system
from datetime import datetime
import os
import config
from utils import load_json, save_json, parse_datetime

def get_system_date():
    """Loads the current system date."""
    data = load_json(config.SYSTEM_DATE_FILE)
    if data and 'current_date' in data:
        # Ensure it's a datetime object
        return datetime.fromisoformat(data['current_date'])
    # Default to today if file doesn't exist or is invalid
    print("System date file not found or invalid, using current real time.")
    now = datetime.now()
    set_system_date(now)  # Initialize the file
    return now

def set_system_date(new_date):
    """Saves the current system date."""
    if isinstance(new_date, str):
        new_date_str = new_date
    elif isinstance(new_date, datetime):
        new_date_str = new_date.isoformat()
    else:
        raise TypeError("new_date must be a datetime object or ISO format string")

    save_json(config.SYSTEM_DATE_FILE, {"current_date": new_date_str})

def process_time_event(time_event_data):
    """Processes a time event, advances the system clock, and triggers periodic functions."""
    # Import here to avoid circular imports
    import credit_service
    import account_service

    new_date_str = time_event_data.get('date')
    if not new_date_str:
        print("Error: Time event missing 'date'.")
        return

    try:
        new_date = parse_datetime(new_date_str)
        if not new_date: raise ValueError("Invalid date format")
    except ValueError as e:
        print(f"Error processing time event: Invalid date format '{new_date_str}'. {e}")
        return

    current_system_date = get_system_date()
    print(
        f"\n>>> Processing Time Event: Advancing system date from {current_system_date.isoformat()} to {new_date.isoformat()} <<<")

    # Update system date *first* so periodic functions use the new date
    set_system_date(new_date)

    # --- Trigger Periodic Functions ---
    # Daily tasks first
    credit_service.calculate_daily_penalties(new_date)

    # Monthly tasks (check if the new date is the start of a month or specific day)
    if new_date.day == 1:
        credit_service.process_monthly_credit_payments(new_date)

    # Quarterly tasks
    if new_date.day == 1:
        account_service.process_quarterly_fees(new_date)

    # Write-off checks
    if new_date.day == 1:
        credit_service.write_off_bad_credits(new_date)

    print(f">>> Time Event Processing Complete for {new_date.isoformat()} <<<")
