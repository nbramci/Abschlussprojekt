# EKG-Analyse-App

Diese Anwendung ermöglicht das Hochladen, die Visualisierung und Analyse von EKG-Daten. Benutzer:innen können sich anmelden, erhalten eine Visualisierung und automatische Anomalieerkennung in den EKG-Daten. Admins haben erweiterte Rechte, um Benutzer und Tests zu verwalten.

---

## Voraussetzungen

Für den Betrieb der App müssen folgende Python-Pakete installiert sein:

```bash
pip install streamlit pandas numpy plotly scipy fpdf tinydb passlib[bcrypt] Pillow
```


- **streamlit**: Web-App-Framework  
- **pandas**, **numpy**: Datenverarbeitung und numerische Berechnung  
- **plotly**: Interaktive Visualisierung der EKG-Daten  
- **scipy**: Signalverarbeitung (Peak-Erkennung)  
- **fpdf**: PDF-Erstellung für Analyse-Zusammenfassungen  
- **tinydb**: Speicherung der Benutzerdaten und EKG-Tests  
- **passlib**: Passwort-Hashing und Sicherheit  
- **Pillow**: Bildverarbeitung (z. B. Profilbilder)

## Starten der App


Navigiere im Terminal in das Projektverzeichnis und führe folgenden Befehl aus:

```bash
streamlit run main.py
```

**Hinweis:**  
Einige Module wie `read_person_data.py` verwenden relative Importe und können daher **nicht direkt** ausgeführt werden. Bitte starte die Anwendung immer über `main.py`.


## Benutzerrollen & Test-Accounts

Die Anwendung unterstützt zwei Rollen mit unterschiedlichen Berechtigungen:

- **Benutzer (user)**: Kann sich einloggen, eigene EKG-Daten analysieren und downloaden.
- **Administrator (admin)**: Hat zusätzlich Zugriff auf alle Benutzer:innen, Admins und deren EKG-Daten. Kann neue Benutzer:innen sowie neue EKG-Tests für Benutzer:innen, Admins oder sich selbst anlegen und verwalten.

Zum Testen können folgende Accounts verwendet werden:

| Rolle   | Benutzername | Passwort |
|---------|--------------|----------|
| Admin   | admin        | admin    |
| User    | jhuber       | 123      |
| User    | yheyer       | 123      |
| User    | yschmirander | 123      |

**Hinweis:** Passwörter werden mit `bcrypt` sicher verschlüsselt gespeichert.

## Erfüllte Anforderungen

Die folgenden Projektanforderungen wurden erfolgreich umgesetzt:

- ✅ Deployment vorbereitet (via Streamlit Sharing mit requirements.txt)
- ✅ Session-Zusammenfassung integriert
- ✅ Datenexport (PDF/CSV) möglich
- ✅ Automatische Anomalieerkennung im EKG-Signal
- ✅ Optimiertes Design für Computer Bildschirme
- ✅ Performante EKG-Verarbeitung durch Auflösungsreduktion (jeder 4. Wert wird verwendet)
- ✅ Neue Personen und Tests können hinzugefügt werden
- ✅ Bestehende Personen und deren Attribute/Bild können editiert werden
- ✅ Berechnung und Anzeige der Herzrate über gesamten Zeitraum
- ✅ Speicherung via TinyDB
- ✅ Suchleiste zur Filterung der Personenauswahl in der Auswahlbox
- ✅ Benutzerdefinierter Zeitbereich für EKG-Plots auswählbar
- ✅ Einheitlicher Stil (z. B. Namenskonventionen, modulare Struktur)
- ✅ Docstrings für Klassen, Methoden und Funktionen vorhanden
- ✅ Testdatum und Länge der EKG-Zeitreihe werden angezeigt
- ✅ Auswahlmöglichkeit zwischen mehreren Tests pro Person
- ✅ Geburtsjahr, Name und Bild der Person werden angezeigt
- ✅ Login-System mit Benutzer- und Admin-Rollen
- ✅ Passwörter werden sicher mit `bcrypt` gehasht
- ✅ Inkorrekte oder unregelmäßige Timestamps in EKG-Dateien werden automatisch erkannt und korrigiert

## Projektstruktur

```text
projekt/
├── data/
│   ├── ekg_data/               # EKG-Rohdaten
│   ├── profile_pictures/       # Profilbilder
│   └── tinydb_person_db.json   # Datenbankdatei
├── exports/                    # Exportierte Reports (PDFs)
├── src/
│   ├── __init__.py
│   ├── database.py             # Datenbanklogik (TinyDB)
│   ├── ekgdata.py              # EKG-Verarbeitung & Analyse
│   ├── person.py               # Datenmodell für Personen
│   ├── read_person_data.py     # Einlesen & Zuordnung von EKG-Daten
├── main.py                     # Streamlit App (Startpunkt)
├── README.md
├── requirements.txt
├── pyproject.toml
└── pdm.lock
```

## Format der EKG-Dateien

Es können ausschließlich EKG-Dateien im `.txt`-Format hochgeladen werden. Die Datei muss zwei Spalten enthalten:

- **Erste Spalte:** Signalstärke in mV  
- **Zweite Spalte:** Zeit in ms

Die Datei darf keine Kopfzeile enthalten.

Beispiel:

```
124   0
129   2
126   4
...
```

## Bekannte Einschränkungen

- Kein responsives Design für Mobilgeräte   
- Nach dem Hochladen eines EKG-Tests muss die entsprechende Person manuell neu ausgewählt werden, damit der Test angezeigt wird  
- Keine Cloud-Anbindung – sämtliche Daten werden lokal gespeichert  
- Beim Deployment via Streamlit Sharing kann es zu Problemen bei der Erstellung von Bildern für die PDF-Zusammenfassung kommen. Für diesen Fall wurde eine Fehlermeldung implementiert – anstelle des Bildes erscheint ein Hinweistext, dass das Bild nicht erstellt werden konnte.  
  **Hinweis:** Für die volle Funktionalität (einschließlich PDF-Bilderstellung) sollte die Anwendung lokal ausgeführt werden.