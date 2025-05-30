# src/utils.py
# Allgemeine Hilfsfunktionen für das Smart-Phone Haifisch Bank System
# Enthält Funktionen für Dateioperationen, ID-Generierung und Datumsverarbeitung
# Stellt sicher, dass alle numerischen Werte als Decimal-Objekte behandelt werden

import json
import os
import uuid
from decimal import Decimal
from datetime import datetime
from . import config

class DecimalEncoder(json.JSONEncoder):
    """
    Benutzerdefinierter JSON-Encoder für Decimal-Werte.
    Konvertiert Decimal-Objekte in Strings, um JSON-Serialisierung zu ermöglichen.
    
    Hinweis:
        - Wird für alle JSON-Operationen im System verwendet
        - Stellt sicher, dass keine Präzision bei Dezimalzahlen verloren geht
        - Erbt von json.JSONEncoder für Standard-JSON-Typen
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def setup_directories():
    """
    Erstellt die notwendigen Datenverzeichnisse, falls sie nicht existieren.
    
    Hinweis:
        - Erstellt Verzeichnisse für Kunden, Konten und Hauptbuch
        - Verwendet die in config.py definierten Pfade
        - Ignoriert Fehler wenn Verzeichnisse bereits existieren
    """
    os.makedirs(config.CUSTOMERS_DIR, exist_ok=True)
    os.makedirs(config.ACCOUNTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(config.LEDGER_FILE), exist_ok=True)
    print("Directories checked/created.")

def load_json(file_path):
    """
    Lädt Daten aus einer JSON-Datei.
    
    Args:
        file_path (str): Pfad zur JSON-Datei
        
    Returns:
        dict/None: Geladene Daten oder None bei Fehler
        
    Hinweis:
        - Konvertiert alle numerischen Werte in Decimal-Objekte
        - Behandelt Fehler beim Dateizugriff und JSON-Parsing
        - Verwendet UTF-8 Kodierung
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Konvertiert numerische Strings in Decimal-Objekte
            return json.load(f, parse_float=Decimal, parse_int=Decimal)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {file_path}")
        return None

def save_json(file_path, data):
    """
    Speichert Daten in einer JSON-Datei.
    
    Args:
        file_path (str): Pfad zur JSON-Datei
        data (dict): Zu speichernde Daten
        
    Hinweis:
        - Erstellt Verzeichnisse falls nicht vorhanden
        - Verwendet DecimalEncoder für korrekte Serialisierung
        - Speichert mit UTF-8 Kodierung und Einrückung
        - Behandelt Fehler beim Speichern
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=DecimalEncoder, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")

def generate_id(prefix):
    """
    Generiert eine eindeutige ID mit Präfix.
    
    Args:
        prefix (str): Präfix für die ID (z.B. 'C' für Kunden, 'CH' für Konten)
        
    Returns:
        str: Eindeutige ID im Format 'prefix-uuid'
        
    Hinweis:
        - Verwendet UUID4 für garantiert eindeutige Werte
        - Präfixe:
            - C: Kunden
            - CH: Hauptkonten
            - CR: Kreditkonten
            - TR: Transaktionen
            - CLS: Kontoschließungen
    """
    unique_part = str(uuid.uuid4())
    return f"{prefix}-{unique_part}"

def parse_datetime(dt_str):
    """
    Konvertiert einen ISO-Datumsstring in ein datetime-Objekt.
    
    Args:
        dt_str (str/datetime): ISO-Datumsstring oder datetime-Objekt
        
    Returns:
        datetime/None: Konvertiertes Datum oder None bei Fehler
        
    Hinweis:
        - Akzeptiert bereits konvertierte datetime-Objekte
        - Erwartet ISO-Format (YYYY-MM-DDTHH:MM:SS)
        - Gibt Warnung bei ungültigem Format
    """
    if isinstance(dt_str, datetime):
        return dt_str  # Bereits ein datetime-Objekt
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not parse date string '{dt_str}'. Returning None.")
        return None