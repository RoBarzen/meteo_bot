# TopMeteo Forecast Telegram Bot

Ein intuitiver Telegram Bot für den Zugriff auf TopMeteo Wettervorhersagen für Segelflug.

## Features

- 🌤️ **Intuitive Navigation**: Einfache Menüführung mit Buttons
- 📅 **Tagesauswahl**: Heute, Morgen und weitere Tage
- 🕐 **Zeitauswahl**: Verschiedene UTC-Zeiten für Thermikkarte und Wolkenverteilung
- 📊 **Vorhersagetypen**: 
  - Flugdistanz (PFD, 18m)
  - Thermikkarte
  - Wolkenverteilung
- 🔄 **Navigation**: Einfache Zurück-Navigation zwischen Menüs

## Installation

1. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements_telegram.txt
   ```

2. **Telegram Bot erstellen:**
   - Chatte mit [@BotFather](https://t.me/botfather) auf Telegram
   - Sende `/newbot` und folge den Anweisungen
   - Kopiere den Bot Token

3. **Bot Token konfigurieren:**
   - Öffne `telegram_bot.py`
   - Ersetze `'YOUR_BOT_TOKEN_HERE'` mit deinem Bot Token

4. **Bot starten:**
   ```bash
   python telegram_bot.py
   ```

## Verwendung

### Bot Commands

- `/start` - Startet den Bot und zeigt das Hauptmenü
- `/forecast` - Zeigt die Vorhersageauswahl

### Navigation

1. **Tag auswählen**: Heute, Morgen, oder weitere Tage
2. **Vorhersagetyp wählen**: Flugdistanz, Thermikkarte, oder Wolkenverteilung
3. **Zeit wählen**: Für Thermikkarte und Wolkenverteilung (6-18 UTC)
4. **Vorhersage erhalten**: Das Bild wird mit Beschreibung gesendet

### Beispiel-Navigation

```
Start → Vorhersage anzeigen → Heute → Thermikkarte → 12:00
```

## Dateistruktur

Der Bot erwartet folgende Verzeichnisstruktur:
```
day0/
├── forecast_flugdistanz_day0_hour10.png
├── forecast_thermikkarte_day0_hour06.png
├── forecast_thermikkarte_day0_hour07.png
└── ...
day1/
├── forecast_flugdistanz_day1_hour10.png
└── ...
```

## Features im Detail

### Intuitive Benutzeroberfläche
- **Emoji-Unterstützung**: Visuelle Orientierung durch Emojis
- **Button-Navigation**: Keine Texteingabe erforderlich
- **Zurück-Navigation**: Einfache Rückkehr zu vorherigen Menüs

### Intelligente Datenverwaltung
- **Automatische Erkennung**: Verfügbare Tage und Zeiten werden automatisch erkannt
- **Fehlerbehandlung**: Benutzerfreundliche Fehlermeldungen
- **Dynamische Menüs**: Nur verfügbare Optionen werden angezeigt

### Benutzerfreundliche Ausgabe
- **Beschreibende Captions**: Jedes Bild enthält Tag, Zeit und Vorhersagetyp
- **Formatierte Zeiten**: UTC-Zeiten werden klar angezeigt
- **Deutsche Lokalisierung**: Alle Texte auf Deutsch

## Sicherheit

- Der Bot Token sollte geheim gehalten werden
- Keine sensiblen Daten werden gespeichert
- Nur lokale Dateien werden gelesen

## Troubleshooting

### Bot antwortet nicht
- Prüfe, ob der Bot Token korrekt ist
- Stelle sicher, dass der Bot läuft
- Prüfe die Logs auf Fehlermeldungen

### Keine Vorhersagen verfügbar
- Stelle sicher, dass die `day0/`, `day1/`, etc. Verzeichnisse existieren
- Prüfe, ob die Bilddateien im korrekten Format vorliegen

### Fehler beim Senden von Bildern
- Prüfe die Dateiberechtigungen
- Stelle sicher, dass die Bilddateien nicht beschädigt sind 