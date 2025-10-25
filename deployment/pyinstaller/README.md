# PyInstaller-Build der QR-Automation-CLI

Dieses Verzeichnis enthält eine reproduzierbare PyInstaller-Konfiguration,
um den Python-Einstiegspunkt `qr_automation.cli` als eigenständige Windows-
Executable (`qr-automation.exe`) zu veröffentlichen.

## Voraussetzungen

* Python \>= 3.10
* Virtuelle Umgebung mit dem Projekt ("editable install")
* PyInstaller 6.x (`pip install .[build]`)
* Windows 10/11 mit Visual C++ Redistributable (für Uvicorn/SQLAlchemy)

## Build-Schritte

```powershell
# In eine neue Powershell-Sitzung im Repository wechseln
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install .[build]

# Executable erzeugen
pyinstaller deployment/pyinstaller/qr_automation_cli.spec --noconfirm
```

PyInstaller legt das Ergebnis unter `dist/qr-automation/qr-automation.exe`
ab. Zusätzlich wird die Beispiel-Gateway-Konfiguration und das Projekt-
README in die Distribution kopiert.

## Starten der Anwendung

```powershell
# Innerhalb des dist-Ordners
./qr-automation.exe chat --host 0.0.0.0 --port 8000
```

Die `chat`-Komponente öffnet den FastAPI-Server inklusive WebSocket-
Broadcasting. Alternativ stehen die Subkommandos `mcp` und `gateway`
entsprechend der Python-CLI zur Verfügung.

## Aufräumen

```powershell
Remove-Item build -Recurse -Force
Remove-Item dist -Recurse -Force
```

Die erzeugten Artefakte werden nicht versioniert und können gefahrlos
wieder entfernt werden.
