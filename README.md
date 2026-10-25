# RohGPT

RohGPT is a private AI chat app built with Django and Ollama. The AI, chat history, uploaded PDFs, and image attachments stay on the user's computer. Its public website is a static landing and download page; it does not host AI inference.

## Features

- Local AI responses through Ollama and the `llama3.2:3b` model
- Streaming responses with a stop button and selectable installed Ollama models
- Multiple chats, chat search, rename, Markdown export, and continue-in-new-chat
- Optional local accounts; signing in claims guest chats from that browser session
- Per-chat preference memory
- PDF text extraction and local keyword-based retrieval for document questions
- Optional image questions with an Ollama vision model
- Sanitized Markdown, tables, and syntax-highlighted code blocks
- English responses by default, including when a question is asked in another language
- Browser voice input and speech playback where supported
- Responsive navy interface and an installable PWA with an offline fallback screen
- Windows, Linux, and macOS desktop builds published through GitHub Releases

## Requirements

- Python 3.10 or later
- [Ollama](https://ollama.com/download)
- The `llama3.2:3b` Ollama model
- Optional: an Ollama vision model such as `llava`

Desktop release builds package RohGPT but do not bundle Ollama or AI models. Install Ollama and download a model separately; model downloads can be several gigabytes.

The model runs locally after it has been downloaded. An internet connection is needed to install dependencies and download the model the first time.

## Setup on Windows

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull llama3.2:3b
# Optional image understanding:
ollama pull llava
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Keep Ollama running while using the chat. The optional `llava` model appears in the model selector after it is installed.

If PowerShell blocks virtual environment activation, run the commands below without activating it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull llama3.2:3b
# Optional image understanding:
ollama pull llava
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
- Set `DJANGO_SECRET_KEY` to a stable, private value if you want sessions to survive server restarts. Without it, a random development key is generated at startup.
- PDF uploads are limited to 10 MB, 200 pages, and 100,000 extracted characters. Relevant text excerpts are selected locally; scanned PDFs that need OCR are not supported.
- Image uploads accept up to three PNG, JPEG, or WebP images per message, each up to 5 MB. They are normalized and stored under `media/`. Image understanding requires a compatible vision model installed in Ollama.
- User accounts are optional. There is no email or password-reset service; account credentials are kept in the local database.
- Voice input depends on browser speech-recognition support and may use the browser vendor's speech service. Speech playback uses voices available on the device.
- The PWA caches its static shell and an offline fallback screen, not private chat pages. The Django app and Ollama must be running locally for chat and inference.
- Conversation memory is an editable per-chat note, not hidden model training or permanent cross-chat memory.

## Deployment note

The default configuration is for local development. Before deployment, set `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`, configure HTTPS and a trusted reverse proxy, and run Django's deployment checks:

```powershell
python manage.py check --deploy
```

Do not expose Django's development server to the public internet. Set `DJANGO_SECURE_SSL_REDIRECT=false` only when HTTPS redirects are correctly enforced by a trusted TLS-terminating proxy.

## Public website and desktop releases

The public landing/download page is in `site/`. `render.yaml` configures it as a Render static site; it does not run Django or Ollama. To publish it, connect this GitHub repository in Render and create the service from the Blueprint file. Render will provide a public `onrender.com` URL; a custom domain can be added in Render's dashboard.

The landing page checks GitHub Releases for desktop packages. To build and publish packages for Windows 64-bit, Debian/Ubuntu Linux 64-bit (plus a portable Linux archive), Intel macOS, and Apple silicon, push a version tag such as `v1.0.0`. The `Build desktop releases` GitHub Actions workflow creates the packages and attaches them to that release. Initial Windows and macOS packages are unsigned and may show SmartScreen or Gatekeeper warnings. Linux requires WebKitGTK. Signed Windows and signed/notarized macOS distribution require signing certificates/accounts.

Desktop builds start the Django app locally and open it in a native window. The SQLite database, uploaded files, and app key are stored in the operating system's user data folder. The app listens only on the local computer and connects to Ollama at `http://127.0.0.1:11434` by default.
