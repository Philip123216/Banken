# src/account_service.py
# Kontoverwaltungsmodul für das Smart-Phone Haifisch Bank System
# Enthält Funktionen zur Erstellung, Verwaltung und Schließung von Konten
# Sowie die Verarbeitung von Kontogebühren und Transaktionen

from datetime import datetime
from decimal import Decimal
import os
from dateutil.relativedelta import relativedelta
from . import config
from .utils import generate_id, save_json, load_json, parse_datetime
from .customer_service import get_customer
from .ledger_service import update_bank_ledger


def create_account(customer_id):
    """
    Erstellt ein reguläres Konto und ein zugehöriges (inaktives) Kreditkonto für einen Kunden.
    
    Args:
        customer_id (str): ID des Kunden
        
    Returns:
        tuple: (account_data, credit_account_data) oder (None, None) bei Fehler
        
    Hinweis:
        - Reguläres Konto erhält Präfix 'CH'
        - Kreditkonto erhält Präfix 'CR'
        - Beide Konten werden mit Status 'active' bzw. 'inactive' erstellt
    """
    # Import hier um zirkuläre Imports zu vermeiden
    from .time_processing_service import get_system_date

    customer_data = get_customer(customer_id)
    if not customer_data:
        print(f"Error: Cannot create account, customer {customer_id} not found.")
        return None, None

    if get_customer_account(customer_id):
        print(f"Error: Customer {customer_id} already has an account.")
        return None, None

    # Reguläres Konto erstellen
    account_id = generate_id("CH")  # CH-Präfix für IBAN-ähnliche ID
    now_iso = datetime.now().isoformat()
    system_date_iso = get_system_date().isoformat()  # Systemdatum für Gebührenberechnung

    account_data = {
        "account_id": account_id,
        "customer_id": customer_id,
        "balance": Decimal("0.00"),
        "status": "active",  # Mögliche Status: 'active', 'blocked', 'closed'
        "created_at": now_iso,
        "last_fee_date": system_date_iso,  # Initialisierung des Gebührendatums
        "transactions": []  # Transaktionshistorie
    }
    account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_id}.json")
    save_json(account_file_path, account_data)
    print(f"Regular account created: {account_id}")

    # Zugehöriges Kreditkonto erstellen (initialisiert aber inaktiv)
    credit_account_id = f"CR{account_id}"
    credit_account_data = {
        "account_id": credit_account_id,
        "customer_id": customer_id,
        "balance": Decimal("0.00"),  # Ausstehender Kreditbetrag
        "status": "inactive",  # Mögliche Status: 'inactive', 'active', 'paid_off', 'blocked', 'written_off'
        "created_at": now_iso,
        "credit_start_date": None,  # Wird bei Kreditvergabe gesetzt
        "credit_end_date": None,    # Wird bei Kreditvergabe gesetzt
        "original_amount": Decimal("0.00"),  # Ursprünglicher Kreditbetrag
        "monthly_payment": Decimal("0.00"),  # Monatliche Rate
        "monthly_rate": config.CREDIT_MONTHLY_RATE,  # Monatlicher Zinssatz
        "remaining_payments": 0,  # Verbleibende Zahlungen
        "amortization_schedule": [],  # Tilgungsplan
        "transactions": [],  # Transaktionshistorie
        "missed_payments_count": 0,  # Zählt aufeinanderfolgende versäumte Zahlungen
        "last_payment_attempt_date": None,  # Datum des letzten Zahlungsversuchs
        "penalty_accrued": Decimal("0.00")  # Aufgelaufene Strafen während Blockierung
    }
    credit_account_file_path = os.path.join(config.ACCOUNTS_DIR, f"{credit_account_id}.json")
    save_json(credit_account_file_path, credit_account_data)
    print(f"Associated credit account created: {credit_account_id}")

    return account_data, credit_account_data

def get_account(account_id):
    """
    Ruft Kontoinformationen ab (reguläres oder Kreditkonto).
    
    Args:
        account_id (str): ID des Kontos
        
    Returns:
        dict/None: Kontodaten oder None wenn nicht gefunden
        
    Hinweis:
        Stellt sicher, dass der Kontostand als Decimal-Objekt zurückgegeben wird
    """
    file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_id}.json")
    account_data = load_json(file_path)
    
    if account_data:
        # Felder, die Decimal sein sollten, explizit konvertieren, falls sie als String geladen wurden
        decimal_fields = ['balance', 'original_amount', 'monthly_payment', 'penalty_accrued']
        for field in decimal_fields:
            if field in account_data and isinstance(account_data[field], str):
                try:
                    account_data[field] = Decimal(account_data[field])
                except Exception as e:
                    print(f"Warning: Could not convert field '{field}' with value '{account_data[field]}' to Decimal for account {account_id}. Error: {e}")
                    # Optional: Setze auf None oder einen Standard-Decimal-Wert, falls Konvertierung fehlschlägt
                    account_data[field] = None # Oder Decimal('0.00') je nach Anforderung
            elif field in account_data and not isinstance(account_data[field], Decimal) and account_data[field] is not None:
                 # Fall: Es ist weder String noch Decimal (z.B. int oder float), versuche Konvertierung
                try:
                    account_data[field] = Decimal(str(account_data[field]))
                except Exception as e:
                    print(f"Warning: Could not convert non-string, non-decimal field '{field}' with value '{account_data[field]}' to Decimal for account {account_id}. Error: {e}")
                    account_data[field] = None

    return account_data

def get_customer_account(customer_id):
    """
    Findet das reguläre Konto eines Kunden.
    
    Args:
        customer_id (str): ID des Kunden
        
    Returns:
        dict/None: Kontodaten oder None wenn nicht gefunden
    """
    all_files = os.listdir(config.ACCOUNTS_DIR)
    account_files = [f for f in all_files if f.endswith('.json') and not f.startswith('CR')]

    for acc_file in account_files:
        acc_data = load_json(os.path.join(config.ACCOUNTS_DIR, acc_file))
        if acc_data and acc_data.get('customer_id') == customer_id:
            return acc_data
    return None

def save_account(account_data):
    """
    Speichert Kontodaten in der entsprechenden Datei.
    
    Args:
        account_data (dict): Zu speichernde Kontodaten
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    if not account_data or 'account_id' not in account_data:
        print("Error: Invalid account data for saving.")
        return False

    file_path = os.path.join(config.ACCOUNTS_DIR, f"{account_data['account_id']}.json")
    save_json(file_path, account_data)
    return True

def add_transaction_to_account(account_data_param, transaction_data):
    """
    Fügt einen Transaktionsdatensatz zur Kontohistorie hinzu.
    
    Args:
        account_data_param (dict): Kontodaten-Objekt
        transaction_data (dict): Transaktionsdaten
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    if not account_data_param:
        print(f"Error: Invalid account_data provided to add_transaction_to_account.")
        return False

    if 'transactions' not in account_data_param:
        account_data_param['transactions'] = []

    account_data_param['transactions'].append(transaction_data)
    return save_account(account_data_param)

def process_quarterly_fees(current_date):
    """
    Verarbeitet die vierteljährlichen Kontogebühren.
    Prüft für jedes aktive Konto, ob seit der letzten Gebühr ein Quartal vergangen ist.
    """
    print(f"\n--- Processing Quarterly Fees for {current_date.isoformat()} ---")
    charged_count = 0
    
    for filename in os.listdir(config.ACCOUNTS_DIR):
        if not filename.startswith('CH-') or not filename.endswith('.json'):
            continue
            
        account_id = filename[:-5]
        account_path = os.path.join(config.ACCOUNTS_DIR, filename)
        account = load_json(account_path) # load_json sollte Decimal zurückgeben
        
        if not account or account.get('status') != 'active':
            continue

        last_fee_date_str = account.get('last_fee_date')
        if not last_fee_date_str:
            # Fallback oder Fehlerbehandlung: Setze auf created_at oder aktuelles Datum - 3 Monate
            # Für neue Konten ist last_fee_date = created_at, Gebühr erst nach 3 Monaten fällig
            last_fee_date = parse_datetime(account.get('created_at'))
            if not last_fee_date:
                 print(f"Warning: Could not determine last_fee_date or created_at for {account_id}. Skipping fee.")
                 continue
        else:
            last_fee_date = parse_datetime(last_fee_date_str)

        if not last_fee_date:
            print(f"Warning: Could not parse last_fee_date for {account_id}. Skipping fee.")
            continue
            
        # Nächstes Fälligkeitsdatum für die Gebühr (letzte Gebühr + 3 Monate)
        # Wichtig: relativedelta muss importiert sein: from dateutil.relativedelta import relativedelta
        next_fee_due_date = last_fee_date + relativedelta(months=3)

        # Ist das current_date am oder nach dem Fälligkeitsdatum?
        # Die Überprüfung des spezifischen Quartalsmonats (z.B. 3,6,9,12) geschieht durch den Aufrufer (time_processing_service)
        # Hier prüfen wir primär, ob die Zeitspanne von 3 Monaten seit der letzten Gebühr erreicht ist.
        if current_date >= next_fee_due_date:
            fee_amount = config.QUARTERLY_FEE
            balance = account.get('balance', Decimal('0.00')) # Sicherstellen, dass es Decimal ist
            if not isinstance(balance, Decimal): # Zusätzliche Absicherung
                balance = Decimal(str(balance))

            transaction_status = "completed"
            reason = ""
            new_balance = balance # Standardmäßig ändert sich der Saldo nicht (falls Gebühr fehlschlägt)

            if balance >= fee_amount:
                new_balance = balance - fee_amount
                account['balance'] = new_balance
                account['last_fee_date'] = current_date.isoformat() # Wichtig: Datum aktualisieren!
                print(f"Quarterly fee of {fee_amount} charged to {account_id}. New balance: {account['balance']}")
                charged_count += 1
            else:
                transaction_status = "rejected" 
                reason = "Insufficient funds for quarterly fee"
                print(f"Warning: Insufficient funds for quarterly fee on {account_id}. Fee not charged.")
            
            # Gebührentransaktion erstellen und speichern
            fee_tx = {
                "transaction_id": generate_id("QF"),
                "type": "quarterly_fee",
                "account": account_id,
                "amount": fee_amount,
                "timestamp": current_date.isoformat(),
                "status": transaction_status,
                "balance_before": balance,
                "balance_after": new_balance, 
                "reason": reason
            }
            # add_transaction_to_account speichert das account-Objekt danach
            if not add_transaction_to_account(account, fee_tx):
                 print(f"Error: Could not add quarterly fee transaction to account {account_id}")
            # Das account Objekt wurde durch add_transaction_to_account bereits gespeichert (da es save_account aufruft)
            # Es ist nicht nötig, save_json(account_path, account) hier erneut aufzurufen,
            # es sei denn, add_transaction_to_account gibt das modifizierte Konto zurück und speichert nicht selbst.
            # Annahme: add_transaction_to_account(account_obj, tx) modifiziert account_obj und ruft save_account(account_obj) auf.
    
    if charged_count == 0:
        print("No accounts due for quarterly fees this period based on their last_fee_date.")
    print("--- Quarterly Fee Processing Complete ---")

def close_account(account_id):
    """
    Schließt ein Kundenkonto, wenn der Kontostand null ist und kein aktiver Kredit besteht.
    
    Args:
        account_id (str): ID des zu schließenden Kontos
        
    Returns:
        bool: True bei erfolgreicher Schließung, False bei Fehler
        
    Hinweis:
        - Prüft, ob das Konto bereits geschlossen ist
        - Prüft, ob der Kontostand null ist
        - Prüft, ob ein aktiver Kredit besteht
    """
    account_data = get_account(account_id)
    if not account_data:
        print(f"Error: Account {account_id} not found.")
        return False

    # Prüfen, ob das Konto bereits geschlossen ist
    if account_data['status'] == 'closed':
        print(f"Account {account_id} is already closed.")
        return True

    # Check if account has zero balance
    if account_data['balance'] != Decimal('0.00'):
        print(f"Error: Cannot close account {account_id} with non-zero balance: {account_data['balance']}")
        return False

    # Check if there's an active credit account
    credit_account_id = f"CR{account_id}"
    credit_account = get_account(credit_account_id)
    if credit_account and credit_account['status'] in ['active', 'blocked']:
        print(f"Error: Cannot close account {account_id} with active credit account.")
        return False

    # Create closing transaction
    close_tx = {
        "transaction_id": generate_id("CLS"),
        "type": "account_closure",
        "account": account_id,
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
        "balance_before": account_data['balance'],
        "balance_after": account_data['balance']
    }

    # Update account status
    account_data['status'] = 'closed'
    account_data['closed_at'] = datetime.now().isoformat()

    # If there's a credit account, close it too if it's not already closed
    if credit_account and credit_account['status'] not in ['closed', 'written_off']:
        credit_account['status'] = 'closed'
        credit_account['closed_at'] = datetime.now().isoformat()
        
        # Create credit account closure transaction
        credit_close_tx = {
            "transaction_id": generate_id("CLS"),
            "type": "credit_account_closure",
            "account": credit_account_id,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "balance_before": credit_account['balance'],
            "balance_after": credit_account['balance']
        }
        
        # Add credit closure transaction
        add_transaction_to_account(credit_account, credit_close_tx)
        save_account(credit_account)
        print(f"Associated credit account {credit_account_id} closed.")

    # Add transaction and save
    add_transaction_to_account(account_data, close_tx)
    print(f"Account {account_id} closed successfully.")
    return True
