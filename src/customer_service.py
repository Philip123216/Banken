# src/customer_service.py
# Kundenverwaltungsmodul für das Smart-Phone Haifisch Bank System
# Enthält Funktionen zur Erstellung, Aktualisierung und Abfrage von Kundenprofilen

from datetime import datetime
import os
import json
from . import config
from .utils import generate_id, save_json, load_json

def create_customer(name, address, birth_date_str):
    """
    Erstellt ein neues Kundenprofil und speichert es im System.
    
    Args:
        name (str): Vollständiger Name des Kunden
        address (str): Adresse des Kunden
        birth_date_str (str): Geburtsdatum im Format YYYY-MM-DD
        
    Returns:
        dict: Erstellte Kundendaten mit generierter ID
    """
    customer_id = generate_id("C")
    now_iso = datetime.now().isoformat()
    customer_data = {
        "customer_id": customer_id,
        "name": name,
        "address": address,
        "birth_date": birth_date_str,  # Format: YYYY-MM-DD
        "created_at": now_iso,
        "status": "active"  # Mögliche Status: 'active', 'inactive', 'blocked'
    }
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    save_json(file_path, customer_data)
    print(f"Customer created: {customer_id}")
    return customer_data

def update_customer(customer_id, updates):
    """
    Aktualisiert die Daten eines bestehenden Kunden.
    
    Args:
        customer_id (str): ID des zu aktualisierenden Kunden
        updates (dict): Dictionary mit zu aktualisierenden Feldern
            Erlaubte Felder: 'name', 'address', 'status'
            
    Returns:
        dict/None: Aktualisierte Kundendaten oder None bei Fehler
    """
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    customer_data = load_json(file_path)
    if not customer_data:
        print(f"Error: Customer {customer_id} not found.")
        return None

    allowed_updates = ["name", "address", "status"]  # Geburtsdatum wird normalerweise nicht geändert
    for key, value in updates.items():
        if key in allowed_updates:
            customer_data[key] = value
        else:
            print(f"Warning: Update key '{key}' not allowed or not found.")

    save_json(file_path, customer_data)
    print(f"Customer {customer_id} updated.")
    return customer_data

def get_customer(customer_id):
    """
    Ruft die Daten eines Kunden ab.
    
    Args:
        customer_id (str): ID des gesuchten Kunden
        
    Returns:
        dict/None: Kundendaten oder None wenn nicht gefunden
    """
    file_path = os.path.join(config.CUSTOMERS_DIR, f"{customer_id}.json")
    return load_json(file_path)