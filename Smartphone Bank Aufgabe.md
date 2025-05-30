Smart-Phone Haifisch Bank:
    1. Nur natürliche Personen
        a. Name und Adresse
        b. Geburtsdatum
    2. Services:
        a. Kunden können Konten eröffnen und schliessen
        b. Kundendaten können angepasst werden
    3. Konten:
        a. Es gibt nur einen Kontokurrent Konto
        b. Es gibt kein Sparkonto oder Ander komplexe Konten
        c. Konten geben keine Kredite
        d. Konten haben eine IBAN Nummer. 
        e. Jeder Kunde hat nur ein Konto
        f. Jedes Konto hat eine Gebühr von CHF 100 p.a. und wird quartalsweise von den Konten abgezogen.
        g. Jeder Kunde erhält eine Kreditkonto, wenn er einen Kredit beantragt. In der Software wird diese immer angelegt, bleibt aber bei null, wen nicht der Kreditbeantrag wird. 
    4. Zahlungsverkehr:
        a. Kunden können Gelder überweisen an ein IBAN Nummer
        b. Gelder können auf die Konten der Kunden überwiesen werden (externe Daten) durch das Zahlungssystem 
        c. Es gibt kein Bargeld, es kann kein Bargeld am Automaten bezogen werden, es kann kein Bargeld eingezahlt werden 
    5. Alle Transaktionen kommen per Daten zum System:
        a. Daten repräsentieren die Überweisungen (E-Banking der Kunden)
        b. Daten repräsentieren die Einzahlungen, die vom Zahlungsverkehrssystem kommen. 
        c. Alle Daten habe eine eindeutige Zeitstempel. Wir können annehmen, dass diese eineindeutig die Transaktionsordnung bestimmt. 
        d. Alle Transaktionen kommen per File Transfer. 
    6. Kredit
        a. Kredit wird mittels der Kredittransaktion eröffnet.
        b. Kunden können einen Kredit mit Laufzeit von 1 Jahr haben.
        c. Der maximale Kredit ist CHF15,000, der minimale Kredit ist CHF1000. Der Kunde kann jeden Betrag zwischen 1000 und 15,000 erhalten. 
        d. Der Kredit hat eine Gebühr von CHF 250 unabhängig vom Betrag.
        e. Der Kredit wird ausbezahlt und dann die Gebühr belastet. 
        f. Der Kredit hat einen Zins von 15% p.a. und wird monatlich berechnet. 
        g. Der Kredit kann jederzeit im Ganzen der Teile zurückgezahlt werden. 
        h. Der Kredit wird über die Laufzeit amortisierte, d.h. nach einem Jahr wird der Kredit zurückbezahlt. Die Bank zieht monatlich die Zahlungen automatisch ab. 
        i. Wenn die Amortisationszahlung nicht geleistet werden können (weil das Konto unter null sinkt), wird das Konto gesperrt und der Kreditzins läuft auf dem Kredit weiter. Das Konto wird nur wieder eröffnet, wenn neues Geld einbezahlt wird, und die ausstehenden Zahlungen und zusätzlicher Zins bezahlt werden kann). Der Strafzins ist 30% und wird täglich berechnet. 
        j. Kredit werden alle genehmigt und vergeben. 
        k. Kredit wird auch mittel Daten erzeugt. 
        l. Die Kredit-Verwaltung erzeugt die Transaktionen zu der Rückzahlung der Kredit und erzeugt die Transaktionsdaten. Die Kredit-Verwaltung wird durch die «Zeit-Transaktion» am Anfang des Monats angestossen, siehe Simulation der Zeit. 
    7. Buchungssystem der Bank
        a. Die Bank führt ein Konto für die Verpflichtungen gegenüber dem Kunden.
        b. Die Bank führt ein Vermögenskonto bei der Zentralbank. Auf diesem erhält sie keine Zinsen. 
        c. Die Bank führt die Kredite als zweites Vermögenskonto. 
        d. Zins und Gebühren werden auf einem separaten Einnahmenkonto gutschrieben, Kreditverlust von diesem abgezogen. Dieses Konto reflektiert den Gewinn und Verlust der Bank. 
        e. Konten, welche nach 6 Monaten keine Kreditzahlungen gemacht haben, werden abgeschrieben. Der ausstehende Betrag wird als Verlust dem Einnahmekonto abgezogen. 
    8. Simulation der Zeit:
        a. Es gibt eine Zeit-Transaktion, d.h. ein Datensatz kündigt die Neue Zeit an. Diese Transaktion kommt jeden Arbeitstag. Diese stellt die die Zeit intern der Berechnungsfunktionen um. 
        b. Transaktionen innerhalb eines Tages erhalten werden entsprechend der Zeitstempels abgehandelt. 
        c. Durch das Einlesen der der neuen Zeittransaktion werden die interne Zeit der Berechnungsfunktionen (Zinsen) angepasst.  
    9. Speicherung
        a. Alle Daten werden als Files im Json Format gespeichert. 
        b. Jedes Konto hat die Transaktionen zugewiesen inkl. Der abgelehnten. Die Kontostände werden auch für die Abgelehnten Transaktionen ausgewiesen (d.h. den alten Wert vor der Transaktion).
        c. Es muss keine Signierung oder Hashes berechnet werden.
    10. Mengengerüst:
        a. Die Smartphonebank hat ca. 50 Kunden.
        b. Die Zeitsimulation ist 2 Jahre
        c. Die gesamten Transaktionen sind durch die Files vorgegeben. 
        d. Pro Kunde gibt es ca. 20 Transaktionen pro Monat. 
        e. Für das Testen des Systems werden vollständig alle Transaktionen und Kontostände von 10 Kunden vorgelegt. 
    11. Software Architektur:
        a. Die Software wird nur mittels Funktionen (ohne Klassen und objectorientierter Programmierung) gebaut, jedoch mit Daten als Json Strukturen.
        b. Die Transaktion und die Simulation der Zeit sind JSON Daten die von aussen als Files geliefert werden. 
        c. Es muss keine Form von UI/UX gebaut werden. 


