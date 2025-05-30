# src/time_processing_service.py
# Zeitverwaltungsmodul für das Smart-Phone Haifisch Bank System
# Steuert die Simulation der Zeit und periodische Aufgaben

from datetime import datetime
import os
from . import config
from .utils import load_json, save_json, parse_datetime
from . import credit_service
from . import account_service

def get_system_date():
    """
    Lädt das aktuelle Systemdatum.
    
    Returns:
        datetime: Aktuelles Systemdatum
        
    Hinweis:
        - Liest das Datum aus der Systemdatei
        - Initialisiert mit aktuellem Datum falls nicht vorhanden
        - Stellt sicher dass ein datetime-Objekt zurückgegeben wird
    """
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
    """
    Speichert das neue Systemdatum.
    
    Args:
        new_date (datetime/str): Neues Datum als datetime-Objekt oder ISO-String
        
    Raises:
        TypeError: Wenn new_date weder datetime noch String ist
        
    Hinweis:
        - Konvertiert datetime in ISO-String
        - Speichert das Datum in der Systemdatei
    """
    if isinstance(new_date, str):
        new_date_str = new_date
    elif isinstance(new_date, datetime):
        new_date_str = new_date.isoformat()
    else:
        raise TypeError("new_date must be a datetime object or ISO format string")

    save_json(config.SYSTEM_DATE_FILE, {"current_date": new_date_str})

def process_time_event(time_event_data):
    """
    Verarbeitet ein Zeiteignis, aktualisiert die Systemzeit und löst periodische Funktionen aus.
    
    Args:
        time_event_data (dict): Zeiteignisdaten mit:
            - date: Neues Datum als ISO-String
            
    Hinweis:
        - Aktualisiert zuerst das Systemdatum
        - Führt periodische Aufgaben in dieser Reihenfolge aus:
            1. Tägliche Strafzinsberechnung
            2. Monatliche Kredittilgungen (am 1. des Monats)
            3. Vierteljährliche Kontogebühren (am 1. des Monats)
            4. Prüfung auf Abschreibungen (am 1. des Monats)
    """
    # Import here to avoid circular imports

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
    # Reihenfolge geändert: Monatliche Zahlungen ZUERST, damit der Status für Strafzinsen korrekt ist.

    # Monthly tasks (check if the new date is the start of a month or specific day)
    if new_date.day == 1:
        credit_service.process_monthly_credit_payments(new_date)

    # Daily tasks (jetzt nach monatlichen Zahlungen, um blockierten Status zu erfassen)
    credit_service.calculate_daily_penalties(new_date)

    # Quarterly tasks
    if new_date.day == 1:
        account_service.process_quarterly_fees(new_date)

    # Write-off checks
    if new_date.day == 1:
        credit_service.write_off_bad_credits(new_date)

    print(f">>> Time Event Processing Complete for {new_date.isoformat()} <<<")
