# RohGPT

RohGPT is a locally hosted chat assistant built with Django and Ollama. It keeps chat history in a local SQLite database and can answer questions about text-based PDF files.

## Features

- Local AI responses through Ollama and the `llama3.2:3b` model
- Multiple conversations, chat search, and saved message history
- PDF text extraction and question answering for uploaded PDFs
- English responses by default, including when a question is asked in another language
- Responsive, dark navy chat interface

## Requirements

- Python 3.10 or later
- [Ollama](https://ollama.com/download)
- The `llama3.2:3b` Ollama model

The model runs locally after it has been downloaded. An internet connection is needed to install dependencies and download the model the first time.

## Setup on Windows

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull llama3.2:3b
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Keep Ollama running while using the chat.

If PowerShell blocks virtual environment activation, run the commands below without activating it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull llama3.2:3b
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

## Run tests

```powershell
python manage.py test chatbot
```

## Configuration and data

- Ollama is expected at `http://127.0.0.1:11434`; the model name and endpoint are configured in `chatbot/views.py`.
- Django uses SQLite. The local `db.sqlite3` file is intentionally excluded from Git and is created by running migrations.
- An optional `DJANGO_SECRET_KEY` environment variable can be set to use a stable Django secret key. Without it, a development key is generated at startup.
- PDF uploads are limited to 10 MB, 200 pages, and 100,000 extracted characters. Scanned PDFs that need OCR are not supported.

## Deployment note

The included Django settings are for local development (`DEBUG = True` and no configured production hosts). Before exposing the app to a network, configure production settings, a stable secret key, allowed hosts, and secure deployment options.
