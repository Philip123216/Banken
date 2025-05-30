# Smart-Phone Haifisch Bank Simulation

Dieses Projekt simuliert die Kernfunktionen einer einfachen Smartphone-Bank, einschliesslich Kunden-, Konto-, Transaktions- und Kreditmanagement. Es verwendet eine dateibasierte Speicherung im JSON-Format und beinhaltet eine Zeitsimulation zur Verarbeitung periodischer Ereignisse.

## Projektstruktur

- **`src/`**: Enthält den gesamten Quellcode der Simulation.
  - **`__init__.py`**: Markiert das `src` Verzeichnis als Python-Paket.
  - **`account_service.py`**: Funktionen zur Kontoerstellung, -schliessung und -verwaltung (z.B. Quartalsgebühren).
  - **`config.py`**: Konfigurationsvariablen (Dateipfade, Gebühren, Zinssätze etc.).
  - **`credit_service.py`**: Funktionen zur Kreditvergabe, -tilgung, Strafzinsberechnung und Abschreibung.
  - **`customer_service.py`**: Funktionen zur Kundenverwaltung.
  - **`generate_test_data.py`**: Skript zur Generierung umfangreicher Testdaten über einen längeren Zeitraum (z.B. 50 Kunden, 2 Jahre) zur Simulation des Gesamtsystems.
  - **`ledger_service.py`**: Verwaltung des Hauptbuchs der Bank.
  - **`main.py`**: (Optional) Ein Haupteinstiegspunkt, falls eine komplette Simulation über `generate_test_data.py` hinaus gestartet werden soll, die Transaktionsdateien verarbeitet.
  - **`test_script.py`**: Ein Skript für Unit- und Integrationstests spezifischer Szenarien durch direkte Funktionsaufrufe. Es testet Kernfunktionen wie Kontoerstellung, Überweisungen, Kreditaufnahme, monatliche Zahlungen, verpasste Zahlungen, Strafzinsen und Kreditabschreibung.
  - **`time_processing_service.py`**: Steuert die Simulation der Zeit und löst periodische Aufgaben aus.
  - **`transaction_service.py`**: Verarbeitet einzelne Transaktionen aus Dateien oder direkten Aufrufen.
  - **`utils.py`**: Hilfsfunktionen (ID-Generierung, JSON-Handling, Datums-Parsing).
- **`data/`**: Verzeichnis für die Datenspeicherung (wird von den Skripten erstellt).
  - **`accounts/`**: Enthält JSON-Dateien für jedes Konto.
  - **`customers/`**: Enthält JSON-Dateien für jeden Kunden.
  - **`transactions/`**: Enthält JSON-Dateien für jede Transaktion (generiert von `generate_test_data.py`).
  - **`bank_ledger.json`**: Das Hauptbuch der Bank.
  - **`system_date.json`**: Speichert das aktuelle Systemdatum der Simulation.
- **`.gitignore`**: Spezifiziert Dateien, die von Git ignoriert werden sollen.
- **`IMPLEMENTATION_MAPPING.md`**: Ordnet die Anforderungen den Implementierungsdetails zu.
- **`README.md`**: Diese Datei.
- **`Smartphone Bank Aufgabe.md`**: Aufgabenbeschreibung.
- **`Technische Beschreibung.md`**: Technische Spezifikationen.

## Setup

Es wird empfohlen, eine virtuelle Umgebung zu verwenden:

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

Installieren Sie die benötigten Abhängigkeiten:

```bash
pip install python-dateutil
```

## Ausführung

1.  **Generierung von Testdaten für eine umfassende Simulation:**
    Führt eine Simulation mit vielen Kunden und Transaktionen über einen längeren Zeitraum durch und generiert entsprechende Transaktionsdateien.

    ```bash
    python -m src.generate_test_data
    ```
    Dies bereinigt auch vorherige Daten in den `data` Unterverzeichnissen.

2.  **Ausführung des Skript-basierten Tests:**
    Dieses Skript führt eine Reihe vordefinierter Tests für spezifische funktionale Szenarien durch, einschliesslich der kritischen Pfade der Kreditverarbeitung.

    ```bash
    python -m src.test_script
    ```
    Dieses Skript führt zu Beginn ebenfalls ein `cleanup_test_data()` durch.

## Implementierungsdetails

Weitere Details zur Zuordnung der Anforderungen zu den Code-Modulen finden Sie in `IMPLEMENTATION_MAPPING.md`.
