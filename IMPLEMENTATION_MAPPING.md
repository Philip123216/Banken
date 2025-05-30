# Implementierungs-Mapping: Anforderungen zu Code

Dieses Dokument bildet die Anforderungen aus "Smartphone Bank Aufgabe.md" (und teilweise "Technische Beschreibung.md") auf die entsprechenden Implementierungen im Quellcode ab.

## 1. Natürliche Personen

*   **1.a Name und Adresse, 1.b Geburtsdatum:**
    *   **Implementierung:** `src/customer_service.py` -> Funktion `create_customer` nimmt `name`, `address`, `date_of_birth` entgegen.
    *   **Datenspeicherung:** Kunden-JSON-Dateien in `data/customers/` speichern diese Attribute.

## 2. Services

*   **2.a Kunden können Konten eröffnen und schliessen:**
    *   **Konto eröffnen:** `src/account_service.py` -> `create_account`. Erstellt Haupt- und initial leeres Kreditkonto.
    *   **Konto schliessen:** `src/account_service.py` -> `close_account`. Setzt Kontostatus auf `closed` (wenn Saldo 0).
*   **2.b Kundendaten können angepasst werden:**
    *   **Implementierung:** `src/customer_service.py` -> `update_customer_details`.
    *   **Hinweis:** Im `test_script.py` nicht explizit als Szenario getestet, aber Funktion ist vorhanden.

## 3. Konten

*   **3.a Es gibt nur einen Kontokorrent Konto:**
    *   **Implementierung:** `src/account_service.py` -> `create_account` erstellt ein Konto vom Typ `current_account` (implizit, da keine anderen Typen definiert).
*   **3.b Es gibt kein Sparkonto oder andere komplexe Konten:**
    *   **Implementierung:** Korrekt, keine solche Funktionalität implementiert.
*   **3.c Konten geben keine Kredite:**
    *   **Implementierung:** Korrekt. Kredite werden über `src/credit_service.py` und assoziierte Kreditkonten (`CRCH-xxxx`) verwaltet. Das Hauptkonto (`CH-xxxx`) selbst vergibt keine Kredite.
*   **3.d Konten haben eine IBAN Nummer:**
    *   **Implementierung:** `src/account_service.py` -> `create_account` generiert eine `account_id` (z.B. `CH-xxxx`), die als IBAN-Äquivalent dient.
*   **3.e Jeder Kunde hat nur ein Konto:**
    *   **Implementierung:** `src/account_service.py` -> `create_account` prüft via `get_customer_account`, ob bereits ein Konto für den Kunden existiert und verhindert die Erstellung eines zweiten.
*   **3.f Jedes Konto hat eine Gebühr von CHF 100 p.a. und wird quartalsweise von den Konten abgezogen:**
    *   **Implementierung:** `src/account_service.py` -> `process_quarterly_fees`. `config.QUARTERLY_FEE` ist `25.00`. Die Logik berücksichtigt `last_fee_date`.
*   **3.g Jeder Kunde erhält ein Kreditkonto, wenn er einen Kredit beantragt. In der Software wird diese immer angelegt, bleibt aber bei null, wen nicht der Kredit beantragt wird:**
    *   **Implementierung:** `src/account_service.py` -> `create_account` erstellt initial ein Hauptkonto und ein zugehöriges Kreditkonto (`CRCH-xxxx`) mit Saldo 0 und Status `inactive`. `src/credit_service.py` -> `request_credit` aktiviert dieses dann.

## 4. Zahlungsverkehr

*   **4.a Kunden können Gelder überweisen an eine IBAN Nummer:**
    *   **Implementierung:** `src/transaction_service.py` -> `process_transfer_out`.
*   **4.b Gelder können auf die Konten der Kunden überwiesen werden (externe Daten) durch das Zahlungssystem:**
    *   **Implementierung:** `src/transaction_service.py` -> `process_incoming_payment`.
*   **4.c Es gibt kein Bargeld:**
    *   **Implementierung:** Korrekt, keine Funktionen für Bargeldabhebung/-einzahlung implementiert.

## 5. Alle Transaktionen kommen per Daten zum System

*   **5.a Daten repräsentieren die Überweisungen (E-Banking der Kunden):**
    *   **Implementierung:** `src/generate_test_data.py` erstellt Transaktionsdateien vom Typ `transfer_out`. `src/transaction_service.py` -> `process_transaction_file` und `process_transaction` können diese verarbeiten.
*   **5.b Daten repräsentieren die Einzahlungen, die vom Zahlungsverkehrssystem kommen:**
    *   **Implementierung:** `src/generate_test_data.py` erstellt Transaktionsdateien vom Typ `transfer_in`. `src/transaction_service.py` kann diese verarbeiten.
*   **5.c Alle Daten habe eine eindeutige Zeitstempel:**
    *   **Implementierung:** Alle Transaktionserstellungsfunktionen (z.B. in `generate_test_data.py`, `transaction_service.py`) nehmen einen `timestamp` entgegen oder generieren ihn.
*   **5.d Alle Transaktionen kommen per File Transfer:**
    *   **Konzept:** Das System ist so ausgelegt, dass `src/main.py` (oder ein ähnlicher Orchestrator) Transaktionsdateien aus einem Verzeichnis lesen und über `src/transaction_service.py` -> `process_transaction_file` verarbeiten könnte. `src/generate_test_data.py` erstellt diese Dateien.
    *   **Test:** `src/test_script.py` ruft die Service-Funktionen meist direkt auf, simuliert aber das Verhalten.

## 6. Kredit

*   **6.a Kredit wird mittels der Kredittransaktion eröffnet:**
    *   **Implementierung:** `src/generate_test_data.py` erstellt eine `credit_request` (oder `credit_disbursement`) Transaktionsdatei. `src/transaction_service.py` -> `process_transaction` leitet dies an `src/credit_service.py` -> `request_credit` weiter.
*   **6.b Kunden können einen Kredit mit Laufzeit von 1 Jahr haben:**
    *   **Implementierung:** `config.py` -> `CREDIT_TERM_MONTHS = 12`. `src/credit_service.py` -> `request_credit` verwendet dies.
*   **6.c Der maximale Kredit ist CHF 15,000, der minimale Kredit ist CHF 1000:**
    *   **Implementierung:** `config.py` -> `MIN_CREDIT = Decimal("1000.00")`, `MAX_CREDIT = Decimal("15000.00")`. `src/credit_service.py` -> `request_credit` prüft diese Limits.
*   **6.d Der Kredit hat eine Gebühr von CHF 250 unabhängig vom Betrag:**
    *   **Implementierung:** `config.py` -> `CREDIT_FEE = Decimal("250.00")`. `src/credit_service.py` -> `request_credit` erhebt diese Gebühr.
*   **6.e Der Kredit wird ausbezahlt und dann die Gebühr belastet:**
    *   **Implementierung:** `src/credit_service.py` -> `request_credit` führt zuerst die Auszahlung auf das Hauptkonto durch und belastet dann die Gebühr vom Hauptkonto.
*   **6.f Der Kredit hat einen Zins von 15% p.a. und wird monatlich berechnet:**
    *   **Implementierung:** `config.py` -> `CREDIT_INTEREST_RATE_PA = Decimal("0.15")`. `src/credit_service.py` -> `process_monthly_credit_payments` berechnet Zinsen auf monatlicher Basis (`config.CREDIT_MONTHLY_RATE`).
*   **6.g Der Kredit kann jederzeit im Ganzen der Teile zurückgezahlt werden:**
    *   **Implementierung:** `src/credit_service.py` -> `process_manual_credit_repayment`.
*   **6.h Der Kredit wird über die Laufzeit amortisiert, d.h. nach einem Jahr wird der Kredit zurückbezahlt. Die Bank zieht monatlich die Zahlungen automatisch ab:**
    *   **Implementierung:** `src/credit_service.py` -> `calculate_amortization` berechnet den monatlichen Zahlungsplan. `process_monthly_credit_payments` versucht, diese Rate monatlich vom Hauptkonto abzubuchen. Die Laufzeit ist durch `config.CREDIT_TERM_MONTHS` definiert.
*   **6.i Wenn die Amortisationszahlung nicht geleistet werden können [...], wird das Konto gesperrt [...]. Der Strafzins ist 30% und wird täglich berechnet:**
    *   **Implementierung:**
        *   `src/credit_service.py` -> `process_monthly_credit_payments`: Wenn Zahlung fehlschlägt, wird Hauptkonto und Kreditkonto auf `blocked` gesetzt, `missed_payments_count` erhöht.
        *   `config.py` -> `PENALTY_INTEREST_RATE_PA = Decimal("0.30")`.
        *   `src/credit_service.py` -> `calculate_daily_penalties`: Berechnet tägliche Strafzinsen für `blocked` Kreditkonten mit positivem Saldo und addiert sie zu `penalty_accrued`.
*   **6.j Kredit werden alle genehmigt und vergeben:**
    *   **Implementierung:** `src/credit_service.py` -> `request_credit` hat keine Bonitätsprüfung; solange die Betragsgrenzen eingehalten werden und das Konto aktiv ist, wird der Kredit gewährt.
*   **6.k Kredit wird auch mittel Daten erzeugt:**
    *   **Implementierung:** Siehe 6.a. `generate_test_data.py` erzeugt die `credit_request` Dateien.
*   **6.l Die Kredit-Verwaltung erzeugt die Transaktionen zu der Rückzahlung der Kredit und erzeugt die Zins Transaktionen (intern):**
    *   **Implementierung:** `src/credit_service.py` -> `process_monthly_credit_payments` erstellt interne Transaktions-Records (`type: "credit_repayment"`) für jede automatische monatliche Zahlung (oder deren Versuch), die Zins- und Tilgungsanteile ausweisen. Diese werden den Kontohistorien hinzugefügt.
*   **6.m Kreditkonto wird bei null wieder auf null gesetzt, wenn der Kredit zurückbezahlt ist:**
    *   **Implementierung:** `src/credit_service.py` -> `process_monthly_credit_payments` und `process_manual_credit_repayment` setzen den Status des Kreditkontos auf `paid_off` und den Saldo auf `0.00`, wenn der Kredit vollständig getilgt ist.
*   **6.n Wenn nach 3 Monaten keine Zahlung mehr eintrifft, dann wird der Kredit abgeschrieben:**
    *   **Implementierung:** `config.py` -> `MAX_MISSED_PAYMENTS = 3`. `src/credit_service.py` -> `write_off_bad_credits` prüft `blocked` Konten. Wenn `missed_payments_count >= MAX_MISSED_PAYMENTS`, wird der Status auf `written_off` gesetzt und entsprechende Ledger-Buchungen vorgenommen. `process_monthly_credit_payments` erhöht `missed_payments_count` bei fehlgeschlagenen Zahlungsversuchen für `active` oder `blocked` Konten.

## 7. Buchungssystem der Bank (Ledger)

*   **7.a bis 7.f (Konten im Ledger):**
    *   **Implementierung:** `src/ledger_service.py` -> `load_bank_ledger` initialisiert die Konten: `customer_liabilities`, `central_bank_assets`, `credit_assets`, `income`, `credit_losses`.
    *   Die verschiedenen Service-Funktionen (z.B. `request_credit`, `process_monthly_credit_payments`, `process_quarterly_fees`, `write_off_bad_credits`, `process_transfer_out`, `process_incoming_payment`) rufen `update_bank_ledger` auf, um die entsprechenden Buchungen vorzunehmen.

## 8. Simulation der Zeit

*   **8.a Zeit-Transaktion:**
    *   **Implementierung:** `src/time_processing_service.py` -> `process_time_event` nimmt ein Datum entgegen, aktualisiert `system_date.json` und ruft periodische Funktionen auf (`process_monthly_credit_payments`, `calculate_daily_penalties`, `process_quarterly_fees`, `write_off_bad_credits`).
*   **8.b Simulationszeitraum:**
    *   **Implementierung:** `src/generate_test_data.py` simuliert standardmäßig 2 Jahre (anpassbar über `SIMULATION_YEARS`). `src/test_script.py` simuliert kürzere, spezifische Zeiträume.

## 9. Technische Anforderungen

*   **9.a JSON Speicherung:**
    *   **Implementierung:** `src/utils.py` -> `load_json`, `save_json` (mit `DecimalEncoder`). Alle Services verwenden diese für Persistenz.
*   **9.b Datumsformat ISO 8601:**
    *   **Implementierung:** Datumsangaben werden typischerweise als ISO-Strings gehandhabt und mit `datetime.fromisoformat()` oder `utils.parse_datetime` geparst.
*   **9.c Python Module, Services:**
    *   **Implementierung:** Code ist in Module wie `customer_service.py`, `account_service.py`, etc. unterteilt.
*   **9.d Logging:**
    *   **Implementierung:** Durchgängige Verwendung von `print()` für das Logging von Aktionen und Fehlern in allen Modulen.
*   **9.e IDs:**
    *   **Implementierung:** `src/utils.py` -> `generate_id` wird für Kunden-, Konto- und Transaktions-IDs verwendet.

## 10. Testdaten und Simulation

*   **10.a `generate_test_data.py`:**
    *   **Implementierung:** Das Skript existiert und generiert ca. 50 Kunden und Transaktionen über 2 Jahre. Es erstellt Transaktionsdateien für Überweisungen, Einzahlungen und Kreditauszahlungen. Es erstellt auch Dateien für systemische Ereignisse wie Quartalsgebühren, Kreditgebühren, Zinszahlungen, Strafzinsen etc., um deren Verarbeitung durch ein Hauptsystem zu ermöglichen.
*   **10.b Zufällige, aber plausible Daten:**
    *   **Implementierung:** `generate_test_data.py` verwendet `random`-Funktionen, um Beträge, Daten etc. zu variieren.
*   **10.c Die gesamten Transaktionen sind durch die Files vorgegeben:**
    *   **Implementierung:** `generate_test_data.py` erstellt Dateien für alle wesentlichen Transaktionstypen, die das System auslösen oder verarbeiten muss, inklusive der oben genannten systemischen Transaktionen. Das Hauptsystem (simuliert durch `test_script.py` oder ein separates `main.py`) würde diese Dateien lesen und die entsprechenden Service-Funktionen aufrufen. Die Service-Funktionen selbst generieren dann die internen Buchungen und Statusänderungen.
*   **10.d Validierung der Testdaten:**
    *   **Implementierung:** Am Ende von `generate_test_data.py` gibt es eine Zusammenfassung und grundlegende Zählungen. `src/test_script.py` enthält `validate_system_integrity`, die eine Bilanzprüfung durchführt. 