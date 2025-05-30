# src/config.py
# Konfigurationsdatei für das Smart-Phone Haifisch Bank System
# Enthält alle globalen Einstellungen, Pfade und Finanzkonstanten
# Zentrale Stelle für alle Systemparameter und Verzeichnispfade

import os
from decimal import Decimal, ROUND_HALF_UP

# --- Projektstruktur und Verzeichnispfade ---
# Bestimmt den absoluten Pfad zum Projektstammverzeichnis
# __file__ ist der Pfad zu config.py (z.B. .../Bank_Modularisiert/src/config.py)
# os.path.dirname(__file__) ist der Pfad zum src-Ordner (z.B. .../Bank_Modularisiert/src)
# os.path.dirname(os.path.dirname(__file__)) ist der Pfad zum Projektstamm (z.B. .../Bank_Modularisiert)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Verzeichniskonfiguration ---
# Definiert die Pfade für alle Datenverzeichnisse
# Alle Pfade werden relativ zum Projektstammverzeichnis erstellt
DATA_DIR = os.path.join(PROJECT_ROOT, "data")  # Hauptdatenverzeichnis für alle Systemdaten
CUSTOMERS_DIR = os.path.join(DATA_DIR, "customers")  # Kundendaten (JSON-Dateien pro Kunde)
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")  # Kontodaten (JSON-Dateien pro Konto)
LEDGER_FILE = os.path.join(DATA_DIR, "bank_ledger", "ledger.json")  # Bank-Ledger (doppelte Buchführung)
SYSTEM_DATE_FILE = os.path.join(DATA_DIR, "system_date.json")  # Systemdatum für Zeit-Simulation
TRANSACTIONS_DIR = os.path.join(DATA_DIR, "transactions")  # Transaktionsdaten (JSON-Dateien pro Transaktion)

# --- Finanzkonstanten ---
# Grundlegende Finanzparameter für das Banksystem
# Alle Beträge werden als Decimal-Objekte gespeichert für präzise Berechnungen
CHF_QUANTIZE = Decimal("0.01")  # Rundungsgenauigkeit für CHF-Beträge (2 Dezimalstellen)
ANNUAL_FEE = Decimal("100.00")  # Jährliche Kontoführungsgebühr pro Konto
QUARTERLY_FEE = (ANNUAL_FEE / 4).quantize(CHF_QUANTIZE, ROUND_HALF_UP)  # Vierteljährliche Gebühr (25% der Jahresgebühr)
CREDIT_FEE = Decimal("250.00")  # Einmalige Gebühr für Kreditvergabe (Bearbeitungsgebühr)
MIN_CREDIT = Decimal("1000.00")  # Minimaler Kreditbetrag (untere Kreditgrenze)
MAX_CREDIT = Decimal("15000.00")  # Maximaler Kreditbetrag (obere Kreditgrenze)
CREDIT_INTEREST_RATE_PA = Decimal("0.15")  # Jährlicher Kreditzinssatz (15% p.a.)
CREDIT_MONTHLY_RATE = CREDIT_INTEREST_RATE_PA / 12  # Monatlicher Kreditzinssatz (1.25% pro Monat)
PENALTY_INTEREST_RATE_PA = Decimal("0.30")  # Jährlicher Strafzinssatz (30% p.a. bei Verzug)
PENALTY_DAILY_RATE = PENALTY_INTEREST_RATE_PA / 365  # Täglicher Strafzinssatz (ca. 0.082% pro Tag)
CREDIT_TERM_MONTHS = 12  # Standard-Kreditlaufzeit in Monaten (1 Jahr)
WRITE_OFF_MONTHS = 6  # Zeitraum bis zur Abschreibung eines Kredits (6 Monate Verzug)
MAX_MISSED_PAYMENTS = 3 # Anzahl verpasster Zahlungen, bevor Kredit abgeschrieben wird (kann zu write_off führen)
