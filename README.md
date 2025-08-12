# Exiobase Explorer

> **Hinweis:** Dieses Projekt befindet sich noch in der Entwicklung.

Ein Python-Tool zur Analyse von Exiobase-Daten mit Modulen für Input-Output-Systeme, Impact-Analysen und Supply-Chain-Management.

---

## Features

- **IOSystem Modul**: Lädt und verarbeitet Input-Output-Daten aus Exiobase.
- **SupplyChain Modul**: Modelliert und analysiert Lieferketten mit hierarchischen Strukturen.

---

## Installation

1. **Repository klonen**
   ```bash
   git clone https://github.com/JonasLmbt/exiobase_explorer.git
   cd exiobase_explorer
   ```

2. **Virtuelle Umgebung erstellen (empfohlen)**
   ```bash
   python -m venv venv
   ```

   **Windows:**
   ```bash
   venv\Scripts\activate
   ```

   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

---

## Nutzung

1. Lade die pxp-Version der Datenbank von Exiobase herunter und lege sie im Ordner `exiobase` ab (Dateinamen nicht ändern): [Exiobase Datenbank herunterladen](https://zenodo.org/records/14869924)

2. Richte die Fast-Load-Datenbanken ein:
   ```bash
   python setup.py
   ```

3. Starte das Tool:
   ```bash
   python main.py
   ```

---

## Module

- **IOSystem**
  - Laden und Verarbeiten von Input-Output-Daten aus Exiobase
  - Verwaltung von Datenbanken und Berechnung von IO-Matrizen

- **SupplyChain**
  - Modellierung und Analyse von Lieferketten mit hierarchischen Strukturen
  - Funktionen zur Verwaltung von Sektoren und wirtschaftlichen Einheiten

---
