# Smart-Phone Haifisch Bank - Modulares System

Dies ist ein modulares Banksystem, das im Rahmen des Kurses CDS305 entwickelt wurde. Es simuliert grundlegende Bankfunktionalitäten wie Kunden- und Kontoverwaltung, Transaktionsverarbeitung, Kreditmanagement und Ledger-Buchhaltung.

## Setup Guide / Einrichtungsanleitung

### English

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Philip123216/Banken.git
   cd Banken
   ```

2. **Set up Python Virtual Environment**
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Tests**
   ```bash
   # Run the scripted test
   python -m test_data.scripted_test
   ```

### Deutsch

1. **Repository klonen**
   ```bash
   git clone https://github.com/Philip123216/Banken.git
   cd Banken
   ```

2. **Python Virtual Environment einrichten**
   ```bash
   # Virtual Environment erstellen
   python -m venv venv

   # Virtual Environment aktivieren
   # Unter Windows:
   venv\Scripts\activate
   # Unter Linux/Mac:
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **Tests ausführen**
   ```bash
   # Scripted Test ausführen
   python -m test_data.scripted_test
   ```

## Projektstruktur

Das Projekt ist wie folgt strukturiert:
- `data/`: Enthält JSON-Dateien für Kundendaten, Konten, Ledger und Systemdatum.
- `src/`: Enthält den Python-Quellcode, unterteilt in Service-Module.
    - `config.py`: Globale Konfigurationen.
    - `utils.py`: Allgemeine Hilfsfunktionen.
    - `*_service.py`: Spezifische Funktionalitätsmodule.
    - `main.py`: Haupteinstiegspunkt für die Simulation.
- `example_transactions_*.json`: Beispieldateien zur Demonstration der Transaktionsverarbeitung.
- `test_data/`: Enthält Testskripte und Test-Transaktionsdateien.

## Anforderungen (Requirements)

- Python 3.10 oder neuer
- Alle Python-Abhängigkeiten sind in `requirements.txt` gelistet (inkl. `python-dateutil`)

## Nutzung (Usage)

### 1. Simulation mit Transaktionsdateien

Führen Sie die Hauptsimulation mit einer oder mehreren Transaktionsdateien aus:
```bash
python -m src.main test_data/test_transactions.json
```

### 2. Scripted Test (empfohlen für vollständigen Systemtest)

Das Skript `test_data/scripted_test.py` führt einen vollständigen Testlauf durch:
- Erstellt Kunden und Konten
- Führt Ein- und Auszahlungen durch
- Beantragt und tilgt einen Kredit
- Führt eine Zeit-Event-Verarbeitung (z.B. Quartalsgebühr) durch
- Schließt ein Konto nach vollständiger Auszahlung

Ausführen mit:
```bash
python -m test_data.scripted_test
```

Das Skript gibt die Ergebnisse jedes Schritts aus und prüft, ob alle Kernfunktionen korrekt arbeiten.

## Hinweise
- Die IDs für Kunden und Konten werden dynamisch generiert.
- Für eigene Tests können Sie das Skript anpassen oder eigene Transaktionsdateien erstellen.

## Wichtige Dateien für Sinan
- `IMPLEMENTATION_MAPPING.md`: Zeigt die Implementierung aller Anforderungen
- `Smartphone Bank Aufgabe.md`: Enthält die ursprünglichen Anforderungen
- `Technische Beschreibung.md`: Enthält die technische Dokumentation
- `test_data/scripted_test.py`: Beispiel für die Verwendung des Systems
- `test_data/test_transactions.json`: Beispiel-Transaktionsdatei

## Fehlerbehebung / Troubleshooting

1. **ImportError: No module named 'src'**
   - Stellen Sie sicher, dass Sie sich im Hauptverzeichnis des Projekts befinden
   - Führen Sie Python-Befehle mit `-m` aus (z.B. `python -m src.main`)

2. **ModuleNotFoundError**
   - Überprüfen Sie, ob die Virtual Environment aktiviert ist
   - Führen Sie `pip install -r requirements.txt` erneut aus

3. **JSON Decode Error**
   - Stellen Sie sicher, dass die JSON-Dateien korrekt formatiert sind
   - Überprüfen Sie die Dateiberechtigungen im `data/` Verzeichnis
