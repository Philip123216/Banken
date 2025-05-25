# src/config.py
import os
from decimal import Decimal, ROUND_HALF_UP

# --- Bestimme den Projekt-Stammordner ---
# __file__ ist der Pfad zu config.py (z.B. .../Bank_Modularisiert/src/config.py)
# os.path.dirname(__file__) ist der Pfad zum src-Ordner (z.B. .../Bank_Modularisiert/src)
# os.path.dirname(os.path.dirname(__file__)) ist der Pfad zum Projektstamm (z.B. .../Bank_Modularisiert)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Directory Configuration ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data") # Absoluter Pfad zum data-Ordner
CUSTOMERS_DIR = os.path.join(DATA_DIR, "customers")
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts")
LEDGER_FILE = os.path.join(DATA_DIR, "bank_ledger", "ledger.json")
SYSTEM_DATE_FILE = os.path.join(DATA_DIR, "system_date.json")

# --- Financial Constants ---
CHF_QUANTIZE = Decimal("0.01")
ANNUAL_FEE = Decimal("100.00")
QUARTERLY_FEE = (ANNUAL_FEE / 4).quantize(CHF_QUANTIZE, ROUND_HALF_UP)
CREDIT_FEE = Decimal("250.00")
MIN_CREDIT = Decimal("1000.00")
MAX_CREDIT = Decimal("15000.00")
CREDIT_INTEREST_RATE_PA = Decimal("0.15")
CREDIT_MONTHLY_RATE = CREDIT_INTEREST_RATE_PA / 12
PENALTY_INTEREST_RATE_PA = Decimal("0.30")
PENALTY_DAILY_RATE = PENALTY_INTEREST_RATE_PA / 365
CREDIT_TERM_MONTHS = 12
WRITE_OFF_MONTHS = 6
