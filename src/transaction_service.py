# src/transaction_service.py
# Transaktionsverarbeitungsmodul für das Smart-Phone Haifisch Bank System
# Verarbeitet verschiedene Transaktionstypen wie Überweisungen, Kredite und Kontoschließungen

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import os
from .config import CHF_QUANTIZE
from .utils import load_json, generate_id, parse_datetime
from .account_service import get_account, add_transaction_to_account, save_account, create_account, close_account
from .customer_service import create_customer
from .credit_service import request_credit, process_manual_credit_repayment
from .ledger_service import update_bank_ledger
from .time_processing_service import process_time_event
import json

def process_transfer_out(transaction_data):
    """
    Verarbeitet eine ausgehende Überweisung von einem Kundenkonto.
    
    Args:
        transaction_data (dict): Transaktionsdaten mit:
            - from_account: Quellkonto
            - amount: Überweisungsbetrag
            - to_iban: Ziel-IBAN
            - timestamp: Zeitstempel
            
    Returns:
        dict: Transaktionsdatensatz mit Status und Kontoständen
        
    Hinweis:
        - Prüft Kontostatus und Deckung
        - Aktualisiert Hauptbuch
        - Speichert Transaktionshistorie
    """
    account_id = transaction_data.get('from_account')
    amount_str = transaction_data.get('amount', '0')
    amount = Decimal(amount_str).quantize(CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("TR")

    account_data = get_account(account_id)

    # --- Create base transaction record (for history) ---
    tx_record = {
        "transaction_id": transaction_id,
        "type": "transfer_out",
        "from_account": account_id,
        "to_iban": transaction_data.get('to_iban'),
        "amount": amount,
        "timestamp": timestamp,
        "status": "rejected",  # Default to rejected
        "balance_before": None,
        "balance_after": None,
        "reason": ""
    }

    if not account_data:
        print(f"Transaction Rejected: Account {account_id} not found.")
        tx_record["reason"] = "Account not found"
        # Cannot save to account if not found, maybe log elsewhere?
        # For now, we just return the rejected record
        return tx_record  # Return immediately

    if account_data['status'] != 'active':
        print(f"Transaction Rejected: Account {account_id} is not active (status: {account_data['status']}).")
        tx_record["reason"] = f"Account not active ({account_data['status']})"
        tx_record["balance_before"] = account_data['balance']
        tx_record["balance_after"] = account_data['balance']  # Balance doesn't change
        add_transaction_to_account(account_data, tx_record)
        return tx_record

    balance_before = account_data['balance']
    tx_record["balance_before"] = balance_before

    if balance_before < amount:
        print(f"Transaction Rejected: Insufficient funds in account {account_id}.")
        tx_record["reason"] = "Insufficient funds"
        tx_record["balance_after"] = balance_before  # Balance doesn't change
        add_transaction_to_account(account_data, tx_record)
        return tx_record
    else:
        # Process successful transfer
        account_data['balance'] -= amount
        tx_record["status"] = "completed"
        tx_record["balance_after"] = account_data['balance']
        print(f"Transfer Out: {amount} from {account_id}. New balance: {account_data['balance']:.2f}")

        # Update Ledger
        update_bank_ledger([
            ('customer_liabilities', -amount),
            ('central_bank_assets', -amount)
        ])

        # Save transaction and account state
        add_transaction_to_account(account_data, tx_record)  # Saves the account implicitly

        return tx_record

def process_incoming_payment(transaction_data):
    """
    Verarbeitet eine eingehende Zahlung auf ein Kundenkonto.
    
    Args:
        transaction_data (dict): Transaktionsdaten mit:
            - to_account: Zielkonto
            - amount: Zahlungsbetrag
            - from_iban: Quell-IBAN
            - timestamp: Zeitstempel
            
    Returns:
        dict: Transaktionsdatensatz mit Status und Kontoständen
        
    Hinweis:
        - Prüft Kontostatus
        - Reaktiviert gesperrte Konten bei positiver Deckung
        - Aktualisiert Hauptbuch
        - Speichert Transaktionshistorie
    """
    account_id = transaction_data.get('to_account')
    amount_str = transaction_data.get('amount', '0')
    amount = Decimal(amount_str).quantize(CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("TR")

    account_data = get_account(account_id)

    tx_record = {
        "transaction_id": transaction_id,
        "type": "transfer_in",
        "to_account": account_id,
        "from_iban": transaction_data.get('from_iban'),
        "amount": amount,
        "timestamp": timestamp,
        "status": "rejected",
        "balance_before": None,
        "balance_after": None,
        "reason": ""
    }

    if not account_data:
        print(f"Transaction Rejected: Account {account_id} not found for incoming payment.")
        tx_record["reason"] = "Account not found"
        return tx_record

    if account_data['status'] == 'closed':
        print(f"Transaction Rejected: Account {account_id} is closed.")
        tx_record["reason"] = "Account closed"
        tx_record["balance_before"] = account_data['balance']
        tx_record["balance_after"] = account_data['balance']
        add_transaction_to_account(account_data, tx_record)
        return tx_record

    balance_before = account_data['balance']
    tx_record["balance_before"] = balance_before

    account_data['balance'] += amount
    tx_record["status"] = "completed"
    tx_record["balance_after"] = account_data['balance']

    if account_data['status'] == 'blocked':
        if account_data['balance'] >= 0:
            account_data['status'] = 'active'
            print(f"Account {account_id} status changed to 'active' due to deposit.")
            
            # Prüfen, ob Strafzinsen vom assoziierten Kreditkonto bezahlt werden können
            credit_account_id = f"CR{account_id}"
            credit_account = get_account(credit_account_id)
            
            if credit_account and credit_account.get('status') == 'blocked' and credit_account.get('penalty_accrued', Decimal('0.00')) > Decimal('0.00'):
                accrued_penalties = Decimal(str(credit_account.get('penalty_accrued')))
                
                # Transaktionsdaten für Strafzinszahlung vorbereiten
                penalty_tx_id = generate_id("PENPAY")
                
                # Wie viel kann von den Strafzinsen mit dem aktuellen Guthaben (nach Einzahlung) bezahlt werden?
                # Das Hauptkonto muss die Strafzinsen decken können.
                # Saldo des Hauptkontos *nach* der aktuellen Einzahlung verwenden.
                available_for_penalty = account_data['balance'] 
                penalty_payment_amount = min(available_for_penalty, accrued_penalties)

                if penalty_payment_amount > Decimal('0.00'):
                    print(f"Attempting to pay {penalty_payment_amount} of accrued penalties for {credit_account_id} from {account_id}.")
                    
                    # Strafzinsen vom Hauptkonto abziehen
                    balance_before_penalty_payment = account_data['balance']
                    account_data['balance'] -= penalty_payment_amount
                    balance_after_penalty_payment = account_data['balance']
                    
                    # Akkumulierte Strafzinsen im Kreditkonto reduzieren
                    credit_account['penalty_accrued'] = accrued_penalties - penalty_payment_amount
                    
                    # Transaktion für bezahlte Strafzinsen (für Hauptkonto)
                    penalty_payment_tx_main = {
                        "transaction_id": penalty_tx_id,
                        "type": "penalty_payment",
                        "from_account": account_id,
                        "to_account": "BANK_INCOME", # Gibt an, wohin das Geld fließt (intern)
                        "credit_account_association": credit_account_id, # Verknüpfung
                        "amount": penalty_payment_amount,
                        "timestamp": timestamp,
                        "status": "completed",
                        "balance_before": balance_before_penalty_payment,
                        "balance_after": balance_after_penalty_payment,
                        "reason": "Payment of accrued penalties"
                    }
                    add_transaction_to_account(account_data, penalty_payment_tx_main)

                    # Transaktion für bezahlte Strafzinsen (für Kreditkonto zur Info)
                    penalty_payment_tx_credit = {**penalty_payment_tx_main, "type": "penalty_paid_info"} # anderer Typ zur Unterscheidung
                    add_transaction_to_account(credit_account, penalty_payment_tx_credit)
                    
                    # Ledger aktualisieren
                    update_bank_ledger([
                        ('customer_liabilities', -penalty_payment_amount), # Geld verlässt Kundenkonto
                        ('income', +penalty_payment_amount)       # Strafzinsen sind Ertrag für die Bank
                    ])
                    save_account(credit_account) # Kreditkonto mit reduzierten Strafen speichern
                    print(f"Successfully paid {penalty_payment_amount} for penalties of {credit_account_id}. Remaining accrued: {credit_account['penalty_accrued']:.2f}")
                    
                    # Wenn alle Strafzinsen bezahlt wurden UND das Hauptkonto jetzt >=0 ist, Kreditkonto entsperren
                    if credit_account['penalty_accrued'] <= Decimal('0.00') and account_data['balance'] >= Decimal('0.00'):
                        credit_account['status'] = 'active'
                        credit_account['penalty_accrued'] = Decimal('0.00') # Sicherstellen, dass es 0 ist
                        print(f"Credit account {credit_account_id} status changed to 'active' as penalties are cleared and main account is solvent.")
                        save_account(credit_account)
                else:
                    print(f"Not enough balance in {account_id} ({account_data['balance']}) to pay any of the accrued penalties ({accrued_penalties}) for {credit_account_id}.")

    update_bank_ledger([
        ('customer_liabilities', +amount),
        ('central_bank_assets', +amount)
    ])

    add_transaction_to_account(account_data, tx_record)
    return tx_record

def process_account_closure(transaction_data):
    """
    Verarbeitet eine Kontoschließungsanfrage.
    
    Args:
        transaction_data (dict): Transaktionsdaten mit:
            - account_id: Zu schließendes Konto
            - timestamp: Zeitstempel
            
    Returns:
        dict: Transaktionsdatensatz mit Status und Grund
        
    Hinweis:
        - Prüft ob Konto existiert und geschlossen werden kann
        - Stellt sicher dass Kontostand 0 ist
        - Prüft ob aktive Kredite existieren
        - Speichert Transaktionshistorie
    """
    account_id = transaction_data.get('account_id')
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("CLS")

    # Create base transaction record
    tx_record = {
        "transaction_id": transaction_id,
        "type": "account_closure_request",
        "account": account_id,
        "timestamp": timestamp,
        "status": "rejected",
        "reason": ""
    }

    # Get account data
    account_data = get_account(account_id)
    if not account_data:
        print(f"Account Closure Failed: Account {account_id} not found.")
        tx_record["reason"] = "Account not found"
        return tx_record

    # Check if account is already closed
    if account_data['status'] == 'closed':
        print(f"Account {account_id} is already closed.")
        tx_record["status"] = "completed"
        tx_record["reason"] = "Account already closed"
        add_transaction_to_account(account_data, tx_record)
        return tx_record

    # Check if account has zero balance
    if account_data['balance'] != Decimal('0.00'):
        print(f"Account Closure Failed: Account {account_id} has non-zero balance: {account_data['balance']}")
        tx_record["reason"] = f"Non-zero balance: {account_data['balance']}"
        add_transaction_to_account(account_data, tx_record)
        return tx_record

    # Check for active credit account
    credit_account_id = f"CR{account_id}"
    credit_account = get_account(credit_account_id)
    if credit_account and credit_account['status'] in ['active', 'blocked']:
        print(f"Account Closure Failed: Account {account_id} has active credit account.")
        tx_record["reason"] = "Active credit account exists"
        add_transaction_to_account(account_data, tx_record)
        return tx_record

    # Attempt to close the account
    if close_account(account_id):
        tx_record["status"] = "completed"
        print(f"Account {account_id} closed successfully.")
    else:
        tx_record["reason"] = "Account closure failed"
        print(f"Account Closure Failed: Could not close account {account_id}")

    add_transaction_to_account(account_data, tx_record)
    return tx_record

def process_transaction_file(file_path):
    """
    Verarbeitet eine Transaktionsdatei.
    
    Args:
        file_path (str): Pfad zur JSON-Datei mit Transaktionen
        
    Hinweis:
        - Liest Transaktionen aus JSON-Datei
        - Verarbeitet jede Transaktion einzeln
        - Behandelt Fehler beim Dateizugriff und JSON-Parsing
    """
    print(f"\nProcessing transaction file: {file_path}")
    try:
        with open(file_path, 'r') as f:
            print(f"Successfully opened file: {file_path}")
            transactions = json.load(f)
            print(f"Loaded {len(transactions)} transactions from file")
            for tx in transactions:
                print(f"\nProcessing transaction: {tx}")
                process_transaction(tx)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Unexpected error processing file {file_path}: {e}")

def process_transaction(tx_data):
    """
    Verarbeitet eine einzelne Transaktion basierend auf ihrem Typ.
    
    Args:
        tx_data (dict): Transaktionsdaten mit:
            - type: Transaktionstyp
            - Weitere feldspezifische Daten
            
    Unterstützte Transaktionstypen:
        - time_event: Zeitfortschritt
        - create_customer: Kundenanlage
        - create_account: Kontoerstellung
        - transfer_out: Ausgehende Überweisung
        - transfer_in: Eingehende Zahlung
        - credit_disbursement: Kreditauszahlung (oft nach credit_request)
        - credit_fee: Kreditgebühr
        - credit_request: Kreditanfrage (kann zu credit_disbursement führen)
        - credit_repayment: Kredittilgung (manuell oder automatisch)
        - credit_penalty: Strafgebühr für Kredit
        - interest_accrual: Zinsanrechnung (z.B. bei überfälligen Krediten)
        - quarterly_fee: Quartalsgebühr für Konto
        - credit_write_off: Kreditabschreibung
        - account_closure: Kontoschließung
    """
    tx_type = tx_data.get('type')
    print(f"Processing transaction type: {tx_type}, ID: {tx_data.get('transaction_id', 'N/A')}")

    if tx_type == "time_event":
        process_time_event(tx_data)
    elif tx_type == "create_customer":
        # Args: name, address, birth_date_str
        create_customer(tx_data.get('name'), tx_data.get('address'), tx_data.get('birth_date'))
    elif tx_type == "create_account":
        # Args: customer_id
        create_account(tx_data.get('customer_id'))
    elif tx_type == "transfer_out":
        process_transfer_out(tx_data)
    elif tx_type == "transfer_in":
        process_incoming_payment(tx_data)
    elif tx_type == "credit_request": # Kann zu credit_disbursement & credit_fee führen
        # request_credit verarbeitet die Anfrage und löst intern Auszahlung + Gebühr aus
        request_credit(tx_data) 
    elif tx_type == "credit_disbursement":
        # Annahme: request_credit kann auch direkt mit Auszahlungsdaten umgehen
        # oder wir brauchen eine dedizierte Funktion in credit_service
        # für eine bereits genehmigte Auszahlung.
        # Fürs Erste, wenn es eine Datei dieses Typs gibt, behandeln wir sie wie eine Anfrage,
        # die dann intern die Auszahlung vornimmt.
        print(f"Processing 'credit_disbursement' file by calling request_credit for main_account: {tx_data.get('main_account')}")
        request_credit(tx_data) # request_credit sollte idempotent sein oder Status prüfen
    elif tx_type == "credit_fee":
        # Diese Datei wird von generate_test_data erzeugt, um die explizite Verarbeitung zu testen.
        # request_credit (ausgelöst durch credit_disbursement) sollte die Gebühr bereits erhoben haben.
        # Ein robuster Ansatz wäre, hier zu prüfen, ob die Gebühr für den zugehörigen Kredit bereits verbucht wurde.
        # Vereinfachter Ansatz: Gebühr versuchen zu buchen, wenn Konto existiert und gedeckt ist.
        print(f"Processing 'credit_fee' file for main_account: {tx_data.get('from_account')}")
        main_account_id = tx_data.get('from_account')
        credit_account_id = tx_data.get('credit_account') # Sollte in der Datei vorhanden sein
        fee_amount_to_charge = Decimal(str(tx_data.get('amount', config.CREDIT_FEE)))

        main_account = get_account(main_account_id)
        credit_account = get_account(credit_account_id) # Nur zur Validierung, dass der Kredit existiert

        if main_account and main_account.get('status') == 'active' and credit_account:
            # Prüfen, ob diese spezifische Gebühr (basierend auf einer eindeutigen ID aus tx_data?) schon gebucht wurde,
            # oder ob für den credit_account generell schon eine Gebühr gebucht wurde.
            # Für diesen Testfall gehen wir davon aus, dass die Datei eine explizite Buchung anfordert.
            
            balance_before_fee = main_account['balance']
            tx_status = "rejected"
            tx_reason = "Insufficient funds for credit fee (file processing)"
            new_balance = balance_before_fee

            if balance_before_fee >= fee_amount_to_charge:
                main_account['balance'] -= fee_amount_to_charge
                new_balance = main_account['balance']
                tx_status = "completed"
                tx_reason = "Credit fee processed from file."
                update_bank_ledger([
                    ('customer_liabilities', -fee_amount_to_charge),
                    ('income', +fee_amount_to_charge)
                ])
                print(f"Credit Fee {fee_amount_to_charge} charged via file to {main_account_id}. New balance: {new_balance}")
            else:
                print(f"Credit Fee {fee_amount_to_charge} from file for {main_account_id} rejected: {tx_reason}")

            # Transaktion für die Gebühr erstellen und speichern
            # Verwende die tx_id aus der Datei, falls vorhanden, sonst generiere eine neue.
            file_tx_id = tx_data.get('transaction_id', generate_id("FEE"))
            fee_tx_log = {
                "transaction_id": file_tx_id,
                "type": "credit_fee",
                "from_account": main_account_id,
                "credit_account": credit_account_id,
                "amount": fee_amount_to_charge,
                "timestamp": tx_data.get('timestamp', datetime.now().isoformat()),
                "status": tx_status,
                "balance_before": balance_before_fee,
                "balance_after": new_balance,
                "reason": tx_reason
            }
            add_transaction_to_account(main_account, fee_tx_log)
            if credit_account: # Auch im Kreditkonto vermerken, falls es existiert
                add_transaction_to_account(credit_account, fee_tx_log) 
        elif not main_account:
            print(f"Credit_fee file processing skipped: Main account {main_account_id} not found.")
        elif not credit_account:
            print(f"Credit_fee file processing skipped: Credit account {credit_account_id} not found.")
        else:
            print(f"Credit_fee file processing skipped: Main account {main_account_id} not active.")

    elif tx_type == "credit_repayment":
        # Unterscheiden, ob es eine manuelle oder eine automatisch generierte Datei ist?
        # Derzeit verarbeitet generate_test_data RP-Dateien.
        # process_manual_credit_repayment ist für 'MRP'-IDs.
        # Wir könnten eine neue Funktion credit_service.process_system_credit_repayment(tx_data) benötigen,
        # oder process_manual_credit_repayment erweitern.
        # Fürs Erste: Annahme, dass manual_credit_repayment dies verarbeiten kann, wenn die Felder passen.
        print(f"Processing 'credit_repayment' file for credit_account: {tx_data.get('credit_account')}")
        process_manual_credit_repayment(tx_data) # Potenziell anpassen für System-Repayments
    elif tx_type == "manual_credit_repayment": # Explizit manuelle, von test_script genutzt
        process_manual_credit_repayment(tx_data)
    elif tx_type == "quarterly_fee":
        # account_service.process_quarterly_fees iteriert. Für eine einzelne Datei brauchen wir:
        # account_service.apply_specific_quarterly_fee(tx_data)
        print(f"Processing 'quarterly_fee' file for account: {tx_data.get('account')}")
        # Diese Funktion muss in account_service.py erstellt werden:
        # from .account_service import apply_specific_quarterly_fee (hypothetical)
        # apply_specific_quarterly_fee(tx_data)
        # Temporär, bis die Funktion existiert:
        # account_service.py -> process_quarterly_fees wurde soeben angepasst, um dies besser zu handhaben.
        # Der Aufruf über time_event ist der primäre Weg. Eine einzelne Datei wäre eine Ausnahme.
        # Wir können versuchen, die Logik aus process_quarterly_fees hier zu adaptieren:
        acc_id = tx_data.get('account')
        acc = get_account(acc_id)
        if acc and acc.get('status') == 'active':
            fee_amt = Decimal(str(tx_data.get('amount')))
            bal_before = acc['balance']
            new_bal = bal_before
            status = 'rejected'
            reason = 'Default file processing - insufficient funds'
            if bal_before >= fee_amt:
                acc['balance'] -= fee_amt
                acc['last_fee_date'] = parse_datetime(tx_data.get('timestamp')).isoformat()
                new_bal = acc['balance']
                status = 'completed'
                reason = 'Processed from quarterly_fee file.'
                update_bank_ledger([('customer_liabilities', -fee_amt), ('income', +fee_amt)])
            tx_data.update({'status': status, 'reason': reason, 'balance_before': bal_before, 'balance_after': new_bal})
            add_transaction_to_account(acc, tx_data)
        else:
            print(f"Skipping quarterly_fee file for inactive/non-existent account {acc_id}")

    elif tx_type == "credit_penalty":
        # credit_service.calculate_daily_penalties akkumuliert. Eine Datei wäre eine explizite Buchung.
        # credit_service.apply_specific_credit_penalty(tx_data)
        print(f"Processing 'credit_penalty' file for credit_account: {tx_data.get('credit_account')}")
        # Temporär, bis apply_specific_credit_penalty existiert:
        cr_acc_id = tx_data.get('credit_account')
        cr_acc = get_account(cr_acc_id)
        if cr_acc:
            penalty_amt = Decimal(str(tx_data.get('amount')))
            # Hier wird die Strafe dem Hauptkonto belastet und dem Kreditkonto gutgeschrieben (oder direkt Income)
            # Die genaue Buchung ist laut Spezifikation nicht 100% klar, ob es den Kreditsaldo erhöht oder direkt Income ist.
            # Annahme: Es ist eine Gebühr, die vom Hauptkonto abgebucht und als Einkommen verbucht wird.
            main_acc_id = tx_data.get('main_account', cr_acc_id[2:]) # versuche main_account aus tx oder abzuleiten
            main_acc = get_account(main_acc_id)
            if main_acc and main_acc.get('status') == 'active' and main_acc.get('balance') >= penalty_amt:
                main_acc['balance'] -= penalty_amt
                update_bank_ledger([('customer_liabilities', -penalty_amt), ('income', +penalty_amt)])
                tx_data.update({'status': 'completed', 'balance_before': main_acc.get('balance') + penalty_amt, 'balance_after': main_acc.get('balance')})
                add_transaction_to_account(main_acc, tx_data)
                add_transaction_to_account(cr_acc, tx_data) # Auch im Kreditkonto vermerken
                print(f"Credit penalty {penalty_amt} charged from {main_acc_id} for {cr_acc_id}")
            else:
                tx_data.update({'status': 'rejected', 'reason': 'Insufficient funds or main account issue for penalty'})
                add_transaction_to_account(cr_acc, tx_data)
                if main_acc: add_transaction_to_account(main_acc, tx_data)
                print(f"Credit penalty for {cr_acc_id} rejected.")
        else:
            print(f"Skipping credit_penalty for non-existent credit_account {cr_acc_id}")

    elif tx_type == "interest_accrual":
        # credit_service.calculate_daily_penalties akkumuliert. Eine Datei wäre eine explizite Buchung.
        # Dies ist normalerweise eine interne Buchung, die den Kreditsaldo erhöht.
        # credit_service.apply_specific_interest_accrual(tx_data)
        print(f"Processing 'interest_accrual' file for credit_account: {tx_data.get('credit_account')}")
        cr_acc_id = tx_data.get('credit_account')
        cr_acc = get_account(cr_acc_id)
        if cr_acc:
            accrual_amt = Decimal(str(tx_data.get('amount')))
            cr_bal_before = cr_acc['balance']
            cr_acc['balance'] += accrual_amt # Zinsen erhöhen Kreditsaldo
            update_bank_ledger([('credit_assets', +accrual_amt), ('income', +accrual_amt)]) # Bank verdient Zinsen
            tx_data.update({'status': 'completed', 'credit_balance_before': cr_bal_before, 'credit_balance_after': cr_acc['balance']})
            add_transaction_to_account(cr_acc, tx_data)
            print(f"Interest {accrual_amt} accrued for {cr_acc_id}. New credit balance: {cr_acc['balance']}")
        else:
            print(f"Skipping interest_accrual for non-existent credit_account {cr_acc_id}")

    elif tx_type == "credit_write_off":
        # credit_service.write_off_bad_credits iteriert. Eine Datei wäre für einen spezifischen Fall.
        # credit_service.apply_specific_write_off(tx_data)
        print(f"Processing 'credit_write_off' file for credit_account: {tx_data.get('credit_account')}")
        # Diese Funktion muss in credit_service.py erstellt werden oder write_off_bad_credits angepasst.
        # Temporär:
        cr_acc_id = tx_data.get('credit_account')
        cr_acc = get_account(cr_acc_id)
        if cr_acc and cr_acc.get('status') != 'written_off':
            amount_to_write_off = Decimal(str(tx_data.get('amount')))
            # Sicherstellen, dass wir nicht mehr abschreiben als vorhanden
            actual_write_off = min(amount_to_write_off, cr_acc['balance'])
            
            update_bank_ledger([
                ('credit_assets', -actual_write_off),
                ('income', -actual_write_off) 
            ])
            cr_acc['balance'] -= actual_write_off
            if cr_acc['balance'] < Decimal('0.00'): cr_acc['balance'] = Decimal('0.00')
            cr_acc['status'] = 'written_off'
            tx_data.update({'status': 'completed', 'amount': actual_write_off}) # Update amount if adjusted
            add_transaction_to_account(cr_acc, tx_data)
            print(f"Credit {cr_acc_id} written off for amount {actual_write_off}.")
        else:
            print(f"Skipping credit_write_off for non-existent or already written-off credit_account {cr_acc_id}")

    elif tx_type == "account_closure": # Bereits vorhanden
        process_account_closure(tx_data)
    else:
        print(f"Warning: Unknown transaction type '{tx_type}'. Skipping.")
