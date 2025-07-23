# syntax=docker/dockerfile:1

# ===== 1. BASIS-IMAGE =====
# Eine spezifische Version für reproduzierbare Builds verwenden,
# so spezifisch wie nur möglich, um Platz zu sparen
FROM python:3.11-slim-bullseye

# ===== 2. UMGEBUNGSVARIABLEN =====
# Verhindert das Erstellen von .pyc-Dateien und stellt sicher, dass die Ausgabe direkt an das Terminal gesendet wird.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ===== 3. SYSTEMABHÄNGIGKEITEN =====
# (Optional) Falls Pakete wie z.B. für Datenbank-Konnektoren benötigt werden
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# ===== 4. ARBEITSVERZEICHNIS =====
# Das Arbeitsverzeichnis für die Anwendung festlegen.
WORKDIR /usr/src/app

# ===== 5. ABHÄNGIGKEITEN INSTALLIEREN =====
# 'requirements.txt' zuerst kopieren.
# Dies nutzt den Docker-Cache optimal aus.
COPY requirements.txt ./
# Pip auf die neueste Version aktualisieren.
RUN /usr/local/bin/python -m pip install --upgrade pip
# Python-Abhängigkeiten installieren, ohne den Cache zu speichern, um die Image-Größe zu reduzieren.
RUN pip install --no-cache-dir -r requirements.txt

# ===== 6. ANWENDUNGSCODE KOPIEREN =====
# Den Anwendungscode in das Arbeitsverzeichnis kopieren.
COPY . . 

# ===== 7. ANWENDUNG STARTEN (Entwicklung) =====
# Startet den Django-Entwicklungsserver und macht ihn im Netzwerk verfügbar.
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]