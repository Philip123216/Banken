# src/credit_service.py
# Kreditverwaltungsmodul für das Smart-Phone Haifisch Bank System
# Enthält Funktionen zur Kreditvergabe, Tilgung, Strafzinsberechnung und Abschreibung

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta  # Externes Paket für Datumsberechnungen
import os
import json
from . import config
from .utils import generate_id, save_json, load_json, parse_datetime
from .ledger_service import update_bank_ledger

def calculate_amortization(principal, annual_rate, term_months):
    """
    Berechnet den Tilgungsplan für einen Kredit.
    
    Args:
        principal (Decimal): Kreditsumme
        annual_rate (Decimal): Jährlicher Zinssatz
        term_months (int): Kreditlaufzeit in Monaten
        
    Returns:
        tuple: (monthly_payment, schedule)
            - monthly_payment: Monatliche Rate
            - schedule: Liste der Tilgungsplan-Einträge
            
    Hinweis:
        Verwendet die Formel: P = (r*PV) / (1 - (1+r)^-n)
        wobei P = Zahlung, r = monatlicher Zinssatz, PV = Kreditsumme, n = Anzahl Zahlungen
    """
    monthly_rate = annual_rate / 12

    # Monatliche Rate berechnen
    if monthly_rate == 0:
        # Spezialfall: Keine Zinsen
        monthly_payment = principal / term_months
    else:
        monthly_payment = (monthly_rate * principal) / (1 - (1 + monthly_rate) ** -term_months)

    # Auf 2 Dezimalstellen runden
    monthly_payment = monthly_payment.quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

    # Tilgungsplan generieren
    schedule = []
    remaining_principal = principal

    for month in range(1, term_months + 1):
        if remaining_principal <= 0:
            break

        # Zinsen für diesen Zeitraum berechnen
        interest_payment = (remaining_principal * monthly_rate).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Tilgung für diesen Zeitraum berechnen (Rate - Zinsen)
        principal_payment = (monthly_payment - interest_payment).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Letzte Rate anpassen um Rundungsprobleme zu vermeiden
        if month == term_months or principal_payment > remaining_principal:
            principal_payment = remaining_principal
            monthly_payment = principal_payment + interest_payment

        # Restkreditsumme aktualisieren
        remaining_principal = (remaining_principal - principal_payment).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        # Zum Plan hinzufügen
        schedule.append({
            "month": month,
            "payment": monthly_payment,
            "principal": principal_payment,
            "interest": interest_payment,
            "remaining": remaining_principal
        })

    return monthly_payment, schedule

def request_credit(transaction_data):
    """
    Verarbeitet einen Kreditantrag, zahlt den Kredit aus und erhebt die Gebühr.
    
    Args:
        transaction_data (dict): Transaktionsdaten mit:
            - main_account: ID des Hauptkontos
            - amount: Kreditsumme
            - timestamp: Zeitstempel
            
    Returns:
        dict/None: Transaktionsdatensatz oder None bei Fehler
        
    Hinweis:
        - Prüft Kreditlimits und Kontostatus
        - Erstellt Tilgungsplan
        - Aktualisiert Ledger
        - Erhebt Kreditgebühr
    """
    # Import hier um zirkuläre Imports zu vermeiden
    from .account_service import get_account, add_transaction_to_account, save_account
    from .time_processing_service import get_system_date
    
    main_account_id = transaction_data.get('main_account')
    credit_account_id = f"CR{main_account_id}"
    amount_str = transaction_data.get('amount', '0')
    requested_amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    system_date_for_credit_start = parse_datetime(timestamp) if timestamp else get_system_date()

    main_account = get_account(main_account_id)
    credit_account = get_account(credit_account_id)

    # --- Validierungen ---
    if not main_account or not credit_account:
        print(f"Credit Request Failed: Account(s) not found for {main_account_id}.")
        return None  # Oder einen abgelehnten Transaktionsstatus zurückgeben

    if main_account['status'] != 'active':
        print(f"Credit Request Failed: Main account {main_account_id} is not active.")
        return None

    if credit_account['status'] not in ['inactive', 'paid_off']:
        print(f"Credit Request Failed: Credit account {credit_account_id} is already active or blocked.")
        return None

    if not (config.MIN_CREDIT <= requested_amount <= config.MAX_CREDIT):
        print(f"Credit Request Failed: Amount {requested_amount} is outside limits ({config.MIN_CREDIT}-{config.MAX_CREDIT}).")
        return None

    # --- Auszahlung verarbeiten ---
    disbursement_tx_id = generate_id("CRD")  # Credit Disbursement
    balance_before_disburse = main_account['balance']
    main_account['balance'] += requested_amount
    balance_after_disburse = main_account['balance']

    # Auszahlungstransaktion erstellen (später hinzufügen)
    disburse_tx = {
        "transaction_id": disbursement_tx_id,
        "type": "credit_disbursement",
        "credit_account": credit_account_id,
        "main_account": main_account_id,
        "amount": requested_amount,
        "timestamp": timestamp,
        "status": "completed",
        "main_balance_before": balance_before_disburse,
        "main_balance_after": balance_after_disburse
    }

    # --- Kreditkonto aktualisieren ---
    credit_balance_before = credit_account['balance']
    credit_account['balance'] = requested_amount  # Ausstehender Kreditbetrag
    credit_account['original_amount'] = requested_amount
    credit_account['status'] = 'active'
    credit_account['credit_start_date'] = system_date_for_credit_start.isoformat()
    credit_account['credit_end_date'] = (system_date_for_credit_start + relativedelta(months=config.CREDIT_TERM_MONTHS)).isoformat()
    credit_account['remaining_payments'] = config.CREDIT_TERM_MONTHS
    credit_account['missed_payments_count'] = 0
    credit_account['penalty_accrued'] = Decimal('0.00')  # Strafen bei neuem Kredit zurücksetzen

    # Tilgungsplan berechnen
    monthly_payment, schedule = calculate_amortization(requested_amount, config.CREDIT_INTEREST_RATE_PA, config.CREDIT_TERM_MONTHS)
    credit_account['monthly_payment'] = monthly_payment
    credit_account['amortization_schedule'] = schedule  # Plan speichern

    print(f"Credit Approved: {requested_amount} for {main_account_id}. Monthly Payment: {monthly_payment}")

    # --- Ledger für Auszahlung aktualisieren ---
    update_bank_ledger([
        ('credit_assets', +requested_amount),  # Bankvermögen erhöht sich
        ('customer_liabilities', +requested_amount)  # Bank schuldet dem Kunden mehr (auf seinem Konto)
    ])

    # --- Kreditgebühr verarbeiten ---
    fee_tx_id = generate_id("FEE")
    balance_before_fee = main_account['balance']  # Kontostand nach Auszahlung verwenden

    # Gebührentransaktion erstellen (später hinzufügen)
    fee_tx = {
        "transaction_id": fee_tx_id,
        "type": "credit_fee",
        "from_account": main_account_id,
        "credit_account": credit_account_id,  # Gebühr mit Kreditereignis verknüpfen
        "amount": config.CREDIT_FEE,
        "timestamp": timestamp,  # Gleichen Zeitstempel verwenden
        "status": "rejected",  # Standard
        "balance_before": balance_before_fee,
        "balance_after": balance_before_fee,
        "reason": ""
    }

    if balance_before_fee < config.CREDIT_FEE:
        print(f"Warning: Insufficient funds in {main_account_id} to pay credit fee ({config.CREDIT_FEE}). Fee not charged.")
        fee_tx["status"] = "rejected"
        fee_tx["reason"] = "Insufficient funds for credit fee"
    else:
        main_account['balance'] -= config.CREDIT_FEE
        fee_tx["status"] = "completed"
        fee_tx["balance_after"] = main_account['balance']
        print(f"Credit Fee Charged: {config.CREDIT_FEE} from {main_account_id}. New balance: {main_account['balance']:.2f}")

        # --- Ledger für Gebühr aktualisieren ---
        update_bank_ledger([
            ('customer_liabilities', -config.CREDIT_FEE),  # Kundenkontostand verringert sich
            ('income', +config.CREDIT_FEE)  # Bank erzielt Einnahmen
        ])

    # --- Alle Änderungen speichern ---
    # Hauptkonto speichern
    save_account(main_account)

    # Kreditkonto speichern
    save_account(credit_account)

    # Transaktionen zu den jeweiligen Konten hinzufügen
    add_transaction_to_account(main_account, disburse_tx)  # Auszahlung zum Hauptkonto
    add_transaction_to_account(main_account, fee_tx)  # Gebühr zum Hauptkonto
    add_transaction_to_account(credit_account, disburse_tx)  # Auszahlung auch zum Kreditkonto verknüpfen
    add_transaction_to_account(credit_account, fee_tx)

    return disburse_tx

def process_manual_credit_repayment(transaction_data):
    """
    Verarbeitet eine manuelle (teilweise oder vollständige) Kredittilgung durch den Kunden.
    
    Args:
        transaction_data (dict): Transaktionsdaten mit:
            - main_account: ID des Hauptkontos
            - credit_account: ID des Kreditkontos
            - amount: Tilgungsbetrag
            - timestamp: Zeitstempel
            
    Hinweis:
        - Fokussiert auf automatische monatliche Tilgung
        - Ermöglicht zusätzliche manuelle Tilgungen
        - Vereinfacht: Reduziert direkt den Kapitalbetrag
        - Berechnet den Tilgungsplan nicht neu
    """
    # Import hier um zirkuläre Imports zu vermeiden
    from .account_service import get_account, add_transaction_to_account, save_account
    main_account_id = transaction_data.get('main_account')
    credit_account_id = transaction_data.get('credit_account')  # Sollte CR<main_account_id> sein
    amount_str = transaction_data.get('amount', '0')
    repayment_amount = Decimal(amount_str).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    transaction_id = generate_id("MRP")  # Manual RePayment

    main_account = get_account(main_account_id)
    credit_account = get_account(credit_account_id)

    # --- Base TX Record ---
    tx_record = {
        "transaction_id": transaction_id,
        "type": "manual_credit_repayment",
        "credit_account": credit_account_id,
        "main_account": main_account_id,
        "amount": repayment_amount,
        "principal_amount": Decimal('0.00'),  # Will be determined
        "interest_amount": Decimal('0.00'),  # Manual repayment goes to principal first
        "timestamp": timestamp,
        "status": "rejected",
        "credit_balance_before": None,
        "credit_balance_after": None,
        "account_balance_before": None,
        "account_balance_after": None,
        "reason": ""
    }

    # --- Validations ---
    if not main_account or not credit_account:
        tx_record["reason"] = "Account(s) not found"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        # Cannot save transaction record if accounts don't exist
        return tx_record

    if main_account['status'] == 'closed' or credit_account['status'] not in ['active', 'blocked']:
        tx_record[
            "reason"] = f"Invalid account status (Main: {main_account['status']}, Credit: {credit_account['status']})"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        # Save rejection to accounts if they exist
        if main_account: add_transaction_to_account(main_account, tx_record)
        if credit_account: add_transaction_to_account(credit_account, tx_record)
        return tx_record

    tx_record["account_balance_before"] = main_account['balance']
    tx_record["credit_balance_before"] = credit_account['balance']

    if main_account['balance'] < repayment_amount:
        tx_record["reason"] = "Insufficient funds in main account"
        print(f"Manual Repayment Failed: {tx_record['reason']}")
        tx_record["account_balance_after"] = main_account['balance']
        tx_record["credit_balance_after"] = credit_account['balance']
        add_transaction_to_account(main_account, tx_record)
        add_transaction_to_account(credit_account, tx_record)
        return tx_record

    # --- Process Repayment ---
    # Apply repayment primarily to principal for manual payments.
    # Consider accrued interest/penalties if account is blocked? Rule says 'ganz oder Teile'.
    # Simple: Reduce principal by the amount paid, up to the outstanding balance.
    principal_paid = min(repayment_amount, credit_account['balance'])
    tx_record["principal_amount"] = principal_paid
    # Any overpayment is ignored or refunded? Let's assume exact or less payment.
    if repayment_amount > credit_account['balance']:
        print(
            f"Warning: Repayment amount {repayment_amount} exceeds outstanding balance {credit_account['balance']}. Paying off balance.")
        repayment_amount = credit_account['balance']  # Adjust actual payment
        principal_paid = repayment_amount
        tx_record["amount"] = repayment_amount  # Update transaction amount

    main_account['balance'] -= repayment_amount
    credit_account['balance'] -= principal_paid

    tx_record["status"] = "completed"
    tx_record["account_balance_after"] = main_account['balance']
    tx_record["credit_balance_after"] = credit_account['balance']

    print(
        f"Manual Repayment: {repayment_amount} applied to {credit_account_id}. Credit Balance: {credit_account['balance']:.2f}, Main Balance: {main_account['balance']:.2f}")

    # --- Update Credit Account Status if Paid Off ---
    if credit_account['balance'] <= 0:
        credit_account['balance'] = Decimal('0.00')  # Ensure exactly zero
        credit_account['status'] = 'paid_off'
        credit_account['remaining_payments'] = 0
        # Clear schedule? Optional, keep for history? Keep for now.
        print(f"Credit account {credit_account_id} is now fully paid off.")

    # --- Ledger Update ---
    update_bank_ledger([
        ('customer_liabilities', -repayment_amount),  # Money leaves customer account
        ('credit_assets', -principal_paid)  # Loan asset decreases
        # No income component for manual principal repayment
    ])

    # --- Save ---
    add_transaction_to_account(main_account, tx_record)
    add_transaction_to_account(credit_account, tx_record)
    # Explicit saves just in case
    save_account(main_account)
    save_account(credit_account)

    return tx_record

def process_monthly_credit_payments(current_date):
    """
    Verarbeitet die monatlichen Kredittilgungen für alle aktiven Kredite.
    Wird typischerweise am ersten Tag des Monats durch `process_time_event` aufgerufen.
    Stellt sicher, dass Zins und Tilgung korrekt berechnet, Konten aktualisiert,
    Transaktionen erstellt und Ledger-Einträge vorgenommen werden.
    Handhabt auch nicht ausreichende Deckung und Kontosperrungen.
    """
    # Lokale Imports, um Abhängigkeiten klar zu halten und zirkuläre Imports zu vermeiden
    from .account_service import get_account, add_transaction_to_account, save_account
    # generate_id, update_bank_ledger und config sind bereits auf Modulebene verfügbar

    print(f"\n--- Processing Monthly Credit Payments for {current_date.isoformat()} ---")
    processed_successful_count = 0
    payment_attempted_count = 0

    for filename in os.listdir(config.ACCOUNTS_DIR):
        if not filename.startswith('CRCH-') or not filename.endswith('.json'):
            continue

        credit_account_id = filename[:-5]
        credit_account = get_account(credit_account_id)

        if not credit_account or credit_account.get('status') not in ['active', 'blocked']:
            continue

        # Sicherstellen, dass remaining_payments als int behandelt wird
        remaining_payments_val = credit_account.get('remaining_payments', 0)
        try:
            remaining_payments_int = int(remaining_payments_val)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert remaining_payments '{remaining_payments_val}' to int for {credit_account_id}. Defaulting to 0.")
            remaining_payments_int = 0

        current_credit_balance = credit_account.get('balance', Decimal('0.01'))
        if not isinstance(current_credit_balance, Decimal):
             current_credit_balance = Decimal(str(current_credit_balance))

        if remaining_payments_int <= 0 and current_credit_balance <= Decimal('0.00'):
            # Wenn keine Zahlungen mehr übrig sind und Saldo <=0, dann als paid_off markieren, falls noch nicht geschehen
            if credit_account.get('status') != 'paid_off':
                credit_account['status'] = 'paid_off'
                credit_account['balance'] = Decimal('0.00')
                save_account(credit_account)
                print(f"Credit {credit_account_id} already paid off or no remaining payments. Marked as paid_off.")
            continue
        
        payment_attempted_count += 1
        main_account_id = credit_account_id[2:] # Hauptkonto-ID ableiten
        main_account = get_account(main_account_id)

        if not main_account or main_account.get('status') == 'closed':
            print(f"Error: Main account {main_account_id} for credit {credit_account_id} not found or closed. Skipping payment.")
            # Hier könnte man eine Warnung im Kreditkonto hinterlegen
            continue

        scheduled_monthly_payment = credit_account.get('monthly_payment')
        if not isinstance(scheduled_monthly_payment, Decimal):
            scheduled_monthly_payment = Decimal(str(scheduled_monthly_payment if scheduled_monthly_payment is not None else '0.00'))

        if scheduled_monthly_payment <= Decimal('0.00'):
            print(f"Warning: Credit {credit_account_id} has zero or negative monthly payment ({scheduled_monthly_payment}). Skipping.")
            continue

        repayment_tx_id = generate_id("RP") 
        tx_status = "rejected" # Standardmäßig abgelehnt
        tx_reason = ""
        
        current_main_balance = main_account.get('balance', Decimal('0.00'))
        credit_balance_before_payment = credit_account.get('balance', Decimal('0.00'))
        
        actual_payment_amount_for_tx = scheduled_monthly_payment # Wird ggf. bei letzter Zahlung angepasst
        principal_component = Decimal('0.00')
        interest_component = Decimal('0.00')
        
        # Initialisiere Salden für Transaktionshistorie
        final_main_balance = current_main_balance
        final_credit_balance = credit_balance_before_payment

        # Wenn das Hauptkonto bereits gesperrt ist ODER wenn das Kreditkonto gesperrt ist
        # UND die Deckung nicht ausreicht, dann Zahlung fehlschlagen und missed_payment erhöhen.
        payment_can_be_attempted = True
        if main_account.get('status') == 'blocked':
            tx_reason = "Main account is blocked."
            print(f"Monthly payment attempt for {credit_account_id} (which is {credit_account.get('status')}) cannot be processed: {tx_reason}")
            payment_can_be_attempted = False # Zahlung kann nicht abgebucht werden
            # missed_payments_count wird unten erhöht, wenn das Kreditkonto 'active' oder 'blocked' war und eine Zahlung fällig war.

        if payment_can_be_attempted and current_main_balance < scheduled_monthly_payment:
            tx_reason = "Insufficient funds in main account for scheduled payment."
            print(f"Monthly payment for {credit_account_id} (status: {credit_account.get('status')}) failed: {tx_reason}")
            payment_can_be_attempted = False # Markiere als nicht erfolgreich
            # Sperre Hauptkonto, falls nicht schon gesperrt
            if main_account.get('status') != 'blocked':
                main_account['status'] = 'blocked'
                print(f"Main account {main_account_id} status changed to 'blocked' due to failed credit payment.")
        
        # Wenn das Kreditkonto 'active' oder 'blocked' war, war eine Zahlung fällig.
        # Wenn sie nicht geleistet werden konnte (payment_can_be_attempted == False), dann missed_payment erhöhen.
        if credit_account.get('status') in ['active', 'blocked'] and not payment_can_be_attempted:
            current_missed_payments = 0
            try:
                current_missed_payments = int(credit_account.get('missed_payments_count', 0))
            except (ValueError, TypeError):
                print(f"Warning: could not convert missed_payments_count '{credit_account.get('missed_payments_count')}' to int for {credit_account_id}. Defaulting to 0.")
            
            credit_account['missed_payments_count'] = current_missed_payments + 1
            credit_account['last_payment_attempt_date'] = current_date.isoformat()
            # Wenn das Kreditkonto 'active' war, wird es jetzt 'blocked'
            if credit_account.get('status') == 'active':
                 credit_account['status'] = 'blocked' 
                 print(f"Credit account {credit_account_id} status changed to 'blocked' due to missed payment.")

        elif payment_can_be_attempted and credit_account.get('status') == 'active': # Zahlung erfolgreich für aktives Konto
            tx_status = "completed"
            
            interest_component = (credit_balance_before_payment * config.CREDIT_MONTHLY_RATE).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)
            principal_component = (scheduled_monthly_payment - interest_component).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

            if principal_component < Decimal('0'):
                # Dies sollte bei korrekter Amortisation nicht passieren, kann aber bei Restsalden auftreten
                principal_component = scheduled_monthly_payment - interest_component # kann negativ sein, wenn Zins > Rate
                if principal_component < Decimal('0'): # Wenn Zins allein schon höher ist als Rate
                    interest_component = scheduled_monthly_payment # Gesamte Rate ist Zins
                    principal_component = Decimal('0') # Kein Tilgungsanteil
            
            if principal_component > credit_balance_before_payment: # Letzte Zahlung
                principal_component = credit_balance_before_payment
                actual_payment_amount_for_tx = principal_component + interest_component
            
            final_main_balance = current_main_balance - actual_payment_amount_for_tx
            main_account['balance'] = final_main_balance
            
            final_credit_balance = credit_balance_before_payment - principal_component
            credit_account['balance'] = final_credit_balance
            
            credit_account['remaining_payments'] = max(0, remaining_payments_int - 1)
            credit_account['missed_payments_count'] = 0 
            credit_account['last_payment_attempt_date'] = current_date.isoformat()
            
            if credit_account.get('status') == 'blocked':
                 credit_account['status'] = 'active'
                 print(f"Credit account {credit_account_id} status changed to 'active' due to successful payment.")

            update_bank_ledger([
                ('customer_liabilities', -actual_payment_amount_for_tx), 
                ('credit_assets', -principal_component),       
                ('income', +interest_component)                
            ])
            print(f"Monthly payment of {actual_payment_amount_for_tx} (P: {principal_component}, I: {interest_component}) processed for {credit_account_id}. Main acc new balance: {final_main_balance}")
            processed_successful_count += 1

        # Transaktionshistorie erstellen
        repayment_tx = {
            "transaction_id": repayment_tx_id,
            "type": "credit_repayment",
            "credit_account": credit_account_id,
            "main_account": main_account_id,
            "amount": actual_payment_amount_for_tx, # Der Betrag, der tatsächlich vom Hauptkonto abgebucht wurde/hätte werden sollen
            "principal_amount": principal_component if tx_status == 'completed' else Decimal('0.00'),
            "interest_amount": interest_component if tx_status == 'completed' else Decimal('0.00'),
            "timestamp": current_date.isoformat(),
            "status": tx_status,
            "reason": tx_reason,
            "credit_balance_before": credit_balance_before_payment,
            "credit_balance_after": final_credit_balance, # Endgültiger Kreditsaldo
            "account_balance_before": current_main_balance,
            "account_balance_after": final_main_balance    # Endgültiger Hauptkontosaldo
        }

        # Transaktion zu beiden Konten hinzufügen (speichert die Konten)
        if main_account : add_transaction_to_account(main_account, repayment_tx)
        add_transaction_to_account(credit_account, repayment_tx) 

        if credit_account['balance'] <= Decimal('0.00') and tx_status == 'completed':
            credit_account['balance'] = Decimal('0.00')
            if credit_account['status'] != 'paid_off':
                credit_account['status'] = 'paid_off'
                credit_account['remaining_payments'] = 0
                print(f"Credit {credit_account_id} fully paid off.")
                save_account(credit_account) # Sicherstellen, dass der paid_off Status gespeichert wird
        else:
            # Speichere credit_account, falls 'missed_payments_count' oder 'status' sich geändert hat, auch bei fehlgeschlagener Zahlung
            save_account(credit_account)


    if payment_attempted_count == 0:
        print("No active credits found needing monthly payments for this period.")
    elif processed_successful_count == 0 and payment_attempted_count > 0:
        print(f"{payment_attempted_count} payment attempts for active credits, all failed or not applicable this period.")
    print("--- Monthly Credit Payment Processing Complete ---")

def calculate_daily_penalties(current_date):
    """
    Berechnet tägliche Strafzinsen für überfällige Kredite.
    Stellt sicher, dass Strafzinsen nur einmal pro Tag für gesperrte Konten mit positivem Saldo berechnet werden.
    
    Args:
        current_date (datetime): Aktuelles Systemdatum
    """
    # Import hier, um zirkuläre Imports bei Bedarf zu handhaben (obwohl get_account ok sein sollte)
    from .account_service import get_account, save_account 

    print(f"\n--- Calculating Daily Penalties for {current_date.isoformat()} ---")
    penalties_calculated_count = 0

    for filename in os.listdir(config.ACCOUNTS_DIR):
        if not filename.startswith('CRCH-') or not filename.endswith('.json'):
            continue

        credit_account_id = filename[:-5]
        credit_account = get_account(credit_account_id)

        if not credit_account:
            print(f"Warning: Could not load credit account {credit_account_id} in calculate_daily_penalties.")
            continue
        
        # DEBUG: Show initial state for this account in this run
        print(f"DEBUG PENALTY: Processing {credit_account_id}, Status: {credit_account.get('status')}, Balance: {credit_account.get('balance')}, LastPenaltyDate: {credit_account.get('last_penalty_calculation_date')}, CurrentDateForPenalty: {current_date.isoformat()}")

        if credit_account.get('status') != 'blocked':
            continue

        current_credit_balance = credit_account.get('balance', Decimal('0.00'))
        # Sicherstellen, dass es Decimal ist (obwohl get_account dies tun sollte)
        if not isinstance(current_credit_balance, Decimal):
            current_credit_balance = Decimal(str(current_credit_balance))

        if current_credit_balance <= Decimal('0.00'):
            continue # Keine Strafzinsen auf Null- oder negativem Saldo

        # Prüfen, ob für heute bereits Strafzinsen berechnet wurden
        last_penalty_date_str = credit_account.get('last_penalty_calculation_date')
        if last_penalty_date_str:
            try:
                # Nur das Datum vergleichen, ohne Zeitanteil, falls current_date Zeit hat
                last_penalty_date = parse_datetime(last_penalty_date_str).date()
                if last_penalty_date == current_date.date():
                    # print(f"Daily penalty for {credit_account_id} already calculated on {last_penalty_date_str}. Skipping.")
                    continue
            except Exception as e:
                print(f"Warning: Could not parse last_penalty_calculation_date '{last_penalty_date_str}' for {credit_account_id}: {e}")

        daily_penalty_rate = config.PENALTY_INTEREST_RATE_PA / Decimal('365')
        # Berechne den Strafzinsbetrag und runde ihn korrekt
        penalty_amount_today = (current_credit_balance * daily_penalty_rate).quantize(config.CHF_QUANTIZE, ROUND_HALF_UP)

        if penalty_amount_today > Decimal('0.00'):
            accrued_penalties_before = credit_account.get('penalty_accrued', Decimal('0.00'))
            if not isinstance(accrued_penalties_before, Decimal):
                accrued_penalties_before = Decimal(str(accrued_penalties_before))
            
            new_total_accrued_penalties = accrued_penalties_before + penalty_amount_today
            credit_account['penalty_accrued'] = new_total_accrued_penalties
            credit_account['last_penalty_calculation_date'] = current_date.isoformat() # Nur Datumsteil wäre besser, aber ISO reicht für den Test
            
            print(f"Daily penalty of {penalty_amount_today:.2f} accrued for {credit_account_id}. Balance: {current_credit_balance:.2f}, Old Accrued: {accrued_penalties_before:.2f}, New Total Accrued: {new_total_accrued_penalties:.2f}")
            penalties_calculated_count += 1
            
            # Ledger Update für akkumulierte Strafzinsen (als Ertrag für die Bank und Erhöhung der Forderung)
            # Dies sollte idealerweise beim Entsperren oder Abschreiben realisiert werden,
            # aber hier zu loggen, dass die Forderung entsteht, ist auch eine Möglichkeit.
            # update_bank_ledger([('income', penalty_amount_today), ('credit_assets_penalties', +penalty_amount_today)])
            # Fürs Erste lassen wir das Ledger-Update hier weg, es wird beim Entsperrversuch/Abschreibung relevant.

            save_account(credit_account) # Speichere das Konto mit den aktualisierten Strafen
        # else:
            # print(f"Calculated penalty_amount for {credit_account_id} is {penalty_amount_today:.2f}, not accruing.")

    if penalties_calculated_count == 0:
        print("No daily penalties were newly calculated in this run (either no eligible accounts or already calculated today).")
    print("--- Daily Penalty Processing Complete ---")

def write_off_bad_credits(current_date):
    """
    Schreibt Kredite ab, die zu lange überfällig sind.
    
    Args:
        current_date (datetime): Aktuelles Systemdatum
        
    Hinweis:
        - Wird am 1. des Monats ausgeführt
        - Prüft auf zu viele verpasste Zahlungen
        - Schreibt Kredite ab und markiert sie als verloren
    """
    print(f"\n--- Processing Credit Write-offs for {current_date.isoformat()} ---")
    # Import für get_account und save_account, falls noch nicht oben global genug
    from .account_service import get_account, save_account
    written_off_count = 0

    for filename in os.listdir(config.ACCOUNTS_DIR):
        if not filename.startswith('CRCH-') or not filename.endswith('.json'):
            continue
        
        credit_account_id = filename[:-5]
        credit_account = get_account(credit_account_id) # Verwende get_account für korrekte Typen

        if not credit_account:
            print(f"Warning: Could not load credit account {credit_account_id} in write_off_bad_credits.")
            continue
            
        # Sollte 'blocked' Konten für Abschreibung prüfen
        if credit_account.get('status') != 'blocked':
            continue
        
        missed_payments_val = credit_account.get('missed_payments_count', 0)
        try:
            missed_payments_int = int(missed_payments_val)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert missed_payments '{missed_payments_val}' to int for {credit_account_id} in write_off. Defaulting to 0.")
            missed_payments_int = 0
                
        # Prüfen ob zu viele Zahlungen verpasst wurden
        if missed_payments_int >= config.MAX_MISSED_PAYMENTS:
            balance_at_write_off = credit_account.get('balance', Decimal('0.00'))
            penalties_at_write_off = credit_account.get('penalty_accrued', Decimal('0.00'))
            total_loss = balance_at_write_off + penalties_at_write_off

            credit_account['status'] = 'written_off'
            credit_account['write_off_date'] = current_date.isoformat()
            credit_account['balance_at_write_off'] = balance_at_write_off # Saldo zum Zeitpunkt der Abschreibung festhalten
            credit_account['penalties_at_write_off'] = penalties_at_write_off
            # Saldo und Strafzinsen auf Null setzen nach Abschreibung für die Bankbilanz intern?
            # Oder den Saldo so lassen, um den Verlust zu dokumentieren? Aktuell bleibt er.
            
            print(f"Credit {credit_account_id} written off. Amount: {balance_at_write_off}, Penalties: {penalties_at_write_off}, Total Loss: {total_loss}")
            written_off_count += 1
            
            # Ledger Update für Abschreibung
            # Reduziere 'credit_assets' um den abgeschriebenen Betrag (Kapital)
            # Erhöhe 'expenses' oder spezifisches 'credit_loss_expenses' Konto um den Totalverlust
            # Reduziere 'income' oder 'credit_assets_penalties' um die abgeschriebenen Strafzinsen, da sie nicht realisiert wurden
            update_bank_ledger([
                ('credit_assets', -balance_at_write_off), # Reduziert den Wert der Kreditanlagen
                ('income', -penalties_at_write_off), # Reduziert (ggf. negative) Einnahmen aus Strafzinsen, da uneinbringlich
                ('credit_losses', +total_loss) # Erfasst den Verlust als Aufwand
            ])
            
            save_account(credit_account)
    
    if written_off_count > 0:
        print(f"--- {written_off_count} credit(s) written off ---")
    else:
        print("No credits met write-off criteria in this run.")
