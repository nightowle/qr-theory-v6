# Task: Vollbündige Integration der Q v.6.00 Korrekturen (Patch)


## Describung
Diese Aufvgabe zielt die komplette Integration aller Korrekturdateien aus `main_patch.txt` und den dazuhörigen Tex-Dateien in das Repository qr=theory-v6 .  Alle vorhärigen Rückfragen wurden automatisch mit *JA* beantwortet, sodas dieser Task den gesamten Workflow bündelt.


## Schritte
1. **Root-Datei einfugen**
0 - main_patch.tex (bereits erledigt).

2. **Ordnerstruktur anlegen**
- sections/
- checklists/
- tables/

3. **Korrekturdateien einfugen**
- sections/bao_fix.tex
- sections/hubble_evolution_fix.tex
- sections/rotation_btfr_qr.tex
- checklists/units_bianchi_checklist.tex
- tables/abgleich_abw.tex

4. **Commit erstellen**
- Commit-Message: "Add QR Theory v6.00 correction sections (BAO, Hubble, BTFR, Bianchi, Abgleich)"

5. **Validierung**
- Sicherstellen, dass `main_patch.tex` mit erfolgreich kompiliert.
- ÜBerpröfung dass alle Includes (`\input{...}`) korrekt verbunden sind.


## Akazeptanzkriter
- [ ] alle Dateien sind im Repo vorhanden.
- [ ] Kompilation mit `main_patch.tex` löft fehlerfrei.
- [ ] Commit-Historie dokumentiert die Korrektur-Integration.

---

Status: Automatisch durch Blue starten 🎣