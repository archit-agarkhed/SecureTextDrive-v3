# SecureTextDrive v3

SecureTextDrive is a Flask-based secure text-file storage demo. It separates the user-facing frontend from the storage backend so the backend only receives encrypted content, public keys, and metadata.

The project is built for learning and demonstration: it shows signup/login, text-file upload, RSA encryption, encrypted database storage, local/session private-key handling, file preview/decryption, deletion, restricted mode, database demos, and optional Gemini-powered summarization.

## Table of Contents

- [Project Goals](#project-goals)
- [Architecture](#architecture)
- [Main Features](#main-features)
- [Repository Structure](#repository-structure)
- [Technology Stack](#technology-stack)
- [How Encryption Works](#how-encryption-works)
- [Database Schema](#database-schema)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [Using the App](#using-the-app)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Utility Scripts](#utility-scripts)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)
- [Suggested Improvements](#suggested-improvements)

## Project Goals

SecureTextDrive demonstrates a safer client-server design for private file storage:

- Users create accounts and log in through a Flask frontend.
- Users upload text files through the browser UI.
- File content is encrypted before it is sent to the backend API.
- The backend stores encrypted content, public keys, and metadata in PostgreSQL.
- Private keys are not intentionally stored in the backend database.
- Users can preview, download, delete, and summarize decrypted text files.
- The project includes full and restricted runtime modes for demos.

Important implementation detail: the project models "client-side" key ownership through the frontend tier. In the current code, encryption/decryption and private-key storage happen in the frontend Flask app using server-side Flask sessions. It is not pure browser-side Web Crypto encryption.

## Architecture

```text
Browser
  |
  | HTML forms, fetch requests
  v
Frontend Flask app
SecureTextDrive-FrontEnd/app.py
Port 5000 in full mode, port 5001 in restricted mode
  |
  | JSON API requests
  | Sends encrypted content, public key, signature metadata
  v
Backend Flask API
SecureTextDrive-Backend/app.py
Port 8000 in full mode, port 8001 in restricted mode
  |
  | psycopg2
  v
PostgreSQL database
USERS and FILECON tables
```

### Frontend Responsibilities

- Render signup, login, and home/file-management pages.
- Call backend APIs for account and file operations.
- Generate RSA key pairs for uploaded files.
- Encrypt uploaded text content with RSA-OAEP.
- Store private keys in the Flask server-side session filesystem.
- Retrieve encrypted content from the backend and decrypt it for preview.
- Provide download, delete, and summarization actions.
- Let users switch between full and restricted backend modes.

### Backend Responsibilities

- Provide JSON APIs for signup, login, file upload, file listing, file retrieval, and deletion.
- Store user records in PostgreSQL.
- Store encrypted file bytes in PostgreSQL.
- Store public keys and encryption metadata.
- Verify upload signatures using a provided signing public key.
- Enforce full/restricted data-access mode through `DATA_ACCESS_ENABLED`.

## Main Features

- User signup and login.
- Text-file upload from the browser.
- RSA-OAEP encryption with chunking in the frontend helper.
- Per-file RSA key-pair generation.
- Server-side session storage for private keys.
- Encrypted file storage in PostgreSQL as binary data.
- File preview by decrypting stored encrypted bytes.
- Download decrypted content as a `.txt` file.
- Delete stored files.
- Optional Gemini summarization for decrypted text.
- Full mode and restricted mode launch scripts.
- Database reset scripts for demos.
- Educational attack/demo scripts.

## Repository Structure

```text
SecureTextDrive-v3/
  SecureTextDrive-Backend/
    app.py                  Backend Flask API
    connect.py              Database connection helper
    mail_config.py          Flask-Mail object
    mail_settings.py        Mail server settings
    password_encrypter.py   Educational affine-cipher helpers
    rsa_utils.py            RSA helper functions
    attacks/
      ddos.py               DDoS simulation script
      password_attack.py    Affine-cipher brute-force demo
      sqlinjection.py       Safe-mode delete endpoint demo

  SecureTextDrive-FrontEnd/
    app.py                  Frontend Flask app entry point
    views.py                Frontend routes and backend API calls
    rsa_utils.py            Chunked RSA encryption/decryption helpers
    password_encrypter.py   Password transform used before API calls
    templates/              Jinja HTML templates
    static/                 CSS, JS, and image assets

  tools/
    summarize_cli.py        Gemini CLI summarization helper

  requirements.txt          Python dependencies
  SECURE_ARCHITECTURE.md    Existing architecture notes
  database_schema.txt       Database demonstration notes
  database_demo.py          Database inspection demo script
  live_db_demo.py           Interactive database demo script
  reset_db.py               Truncates users and filecon tables
  reset_all.sh              Resets DB and clears frontend sessions
  run_backend_full.*        Starts backend with data access enabled
  run_backend_restricted.*  Starts backend with data access disabled
  run_frontend_full.*       Starts frontend pointing to full backend
  run_frontend_restricted.* Starts frontend pointing to restricted backend
```

## Technology Stack

- Python
- Flask
- Flask-CORS
- Flask-Mail
- Flask-Session
- PostgreSQL
- psycopg2
- cryptography
- rsa
- requests
- Google Generative AI SDK
- HTML, CSS, and browser JavaScript

## How Encryption Works

### Signup and Login

1. The frontend receives an email and password from the HTML form.
2. The frontend transforms the password using `password_encrypter.py`.
3. The backend stores and compares the transformed password in the `USERS` table.

This password transform is an affine cipher. It is educational and reversible. It should not be treated as secure password hashing.

### Upload Flow

1. User selects a text file in the browser.
2. Browser JavaScript reads the file as text with `FileReader.readAsText`.
3. Browser sends the filename and text content to the frontend Flask route `/api/upload_file`.
4. The frontend generates a per-file RSA key pair.
5. The frontend encrypts the text content with the public key.
6. The frontend stores the private key in the Flask session under `session['private_keys'][filename]`.
7. The frontend generates a separate signing key pair and signs a SHA-256 digest of the encrypted content.
8. The frontend sends encrypted content, public key, signing metadata, filename, user email, and encryption metadata to the backend.
9. The backend stores encrypted content and public metadata in the `filecon` table.

### Preview and Download Flow

1. User clicks a saved file.
2. Frontend asks the backend for the encrypted file content and public key.
3. Frontend loads the matching private key from the Flask session.
4. Frontend decrypts the encrypted bytes.
5. Browser displays decrypted content in a modal.
6. User can download the decrypted content as a text file.

### Key Storage Behavior

- Backend database receives no real private key for new uploads.
- The current backend insert still includes a `prikey` value as an empty string, likely for schema compatibility.
- Private keys live in frontend server-side Flask session storage.
- If the session is lost, cleared, expired, or accessed from another device/session, old files may not be decryptable from that session.

## Database Schema

The project uses a PostgreSQL database with two main tables.

### USERS

```sql
CREATE TABLE users (
    email VARCHAR PRIMARY KEY,
    password VARCHAR,
    auth BOOLEAN
);
```

Purpose:

- `email`: user identifier.
- `password`: transformed password value.
- `auth`: currently used as an authentication/security flag.

### FILECON

```sql
CREATE TABLE filecon (
    email VARCHAR,
    fpath VARCHAR,
    fcon BYTEA,
    pubkey TEXT,
    encryption_method VARCHAR,
    key_size INTEGER,
    prikey TEXT
);
```

Purpose:

- `email`: owner email.
- `fpath`: uploaded filename.
- `fcon`: encrypted file content.
- `pubkey`: public key in PEM format.
- `encryption_method`: currently `"RSA"`.
- `key_size`: RSA key size.
- `prikey`: legacy/backward-compatible column; new uploads insert an empty string.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/archit-agarkhed/SecureTextDrive-v3.git
cd SecureTextDrive-v3
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux/WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The virtual environment is intentionally ignored by Git through `.gitignore`.

## Running the App

Run the backend and frontend in separate terminals.

### Full Mode

Full mode enables data access: upload, list, preview, summarize, and delete.

Windows:

```bat
run_backend_full.bat
run_frontend_full.bat
```

macOS/Linux/WSL:

```bash
bash run_backend_full.sh
bash run_frontend_full.sh
```

Open:

```text
http://127.0.0.1:5000
```

### Restricted Mode

Restricted mode points the frontend to a backend where data access is disabled. It is useful for showing an instance that can run login/capability checks but blocks file operations.

Windows:

```bat
run_backend_restricted.bat
run_frontend_restricted.bat
```

macOS/Linux/WSL:

```bash
bash run_backend_restricted.sh
bash run_frontend_restricted.sh
```

Open:

```text
http://127.0.0.1:5001
```

### Manual Run Commands

Backend:

```bash
cd SecureTextDrive-Backend
DATA_ACCESS_ENABLED=1 PORT=8000 python app.py
```

Frontend:

```bash
cd SecureTextDrive-FrontEnd
BACKEND_URL=http://127.0.0.1:8000/api PORT=5000 python app.py
```

For Windows PowerShell, set environment variables like this:

```powershell
$env:DATA_ACCESS_ENABLED="1"
$env:PORT="8000"
python app.py
```

## Using the App

1. Start the backend and frontend.
2. Open the frontend URL in your browser.
3. Sign up with an email and password.
4. Log in.
5. Click the `+` file card to upload a text file.
6. Click a saved file to preview decrypted content.
7. Use the modal buttons to download, delete, or summarize content.
8. Use the mode buttons in the header to switch between full and restricted backend URLs.

## Configuration

### Runtime Environment Variables

| Variable | Used By | Purpose |
| --- | --- | --- |
| `PORT` | Backend and frontend | Selects the Flask port. |
| `DATA_ACCESS_ENABLED` | Backend | `1` allows file operations, `0` blocks them. |
| `BACKEND_URL` | Frontend | Backend API base URL, for example `http://127.0.0.1:8000/api`. |
| `GOOGLE_API_KEY` | Frontend and CLI tool | Enables Gemini summarization. |
| `GOOGLE_GEMINI_MODEL` | Frontend | Optional model override for summarization. |
| `MAIL_PASSWORD` | Backend | Enables mail sending if mail settings are present. |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` | `reset_db.py` | Database settings for reset scripts. |

### Database Configuration

The backend currently defines its PostgreSQL connection values directly in `SecureTextDrive-Backend/app.py` and `SecureTextDrive-Backend/connect.py`. For production or shared projects, move these values into environment variables and rotate any credentials that have been committed.

### Gemini Summarization

The web UI summarization endpoint requires:

```bash
export GOOGLE_API_KEY="your-api-key"
```

Optional:

```bash
export GOOGLE_GEMINI_MODEL="gemini-1.5-flash"
```

The CLI summarizer can be run with:

```bash
python tools/summarize_cli.py --file path/to/file.txt
```

or:

```bash
python tools/summarize_cli.py --file path/to/file.txt --out summary.txt
```

## API Reference

### Backend API

Base URL in full mode:

```text
http://127.0.0.1:8000/api
```

Base URL in restricted mode:

```text
http://127.0.0.1:8001/api
```

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/signup` | Create a user. |
| `POST` | `/login` | Log in and set backend session email. |
| `GET` | `/home` | Return current backend session email. |
| `GET` | `/capabilities` | Return full/restricted data-access capability. |
| `POST` | `/logout` | Clear backend session. |
| `POST` | `/upload_file` | Store encrypted file content and public metadata. |
| `POST` | `/retrieve_file` | List files for an email. |
| `POST` | `/get_file_content` | Get encrypted content and public key for one file. |
| `POST` | `/delete_file` | Delete one stored file. |
| `DELETE` | `/delete_all_filecon` | Demo endpoint guarded by `safe_mode`. |

### Frontend Routes

| Method | Route | Description |
| --- | --- | --- |
| `GET`, `POST` | `/signup` | Signup page and form handler. |
| `GET`, `POST` | `/login` | Login page and form handler. |
| `GET`, `POST` | `/` | Home page and saved file list. |
| `GET` | `/logout` | Clear frontend login session while preserving local private keys. |
| `POST` | `/set_backend` | Switch full/restricted/custom backend URL. |
| `GET` | `/get_backend` | Return active backend URL and mode. |
| `POST` | `/api/upload_file` | Encrypt uploaded text and forward encrypted payload to backend. |
| `POST` | `/preview_file` | Fetch encrypted file and decrypt with session private key. |
| `POST` | `/delete_file` | Delete file through backend and remove local private key. |
| `POST` | `/summarize` | Summarize decrypted text using Gemini. |

### Example Backend Requests

Signup:

```bash
curl -X POST http://127.0.0.1:8000/api/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret","confirm_password":"secret"}'
```

Capabilities:

```bash
curl http://127.0.0.1:8000/api/capabilities
```

## Utility Scripts

### Run Scripts

- `run_backend_full.bat` / `run_backend_full.sh`: backend on port `8000` with data access enabled.
- `run_backend_restricted.bat` / `run_backend_restricted.sh`: backend on port `8001` with data access disabled.
- `run_frontend_full.bat` / `run_frontend_full.sh`: frontend on port `5000`, pointing to full backend.
- `run_frontend_restricted.bat` / `run_frontend_restricted.sh`: frontend on port `5001`, pointing to restricted backend.

### Reset Scripts

`reset_db.py` truncates `users` and `filecon`.

```bash
python reset_db.py
```

`reset_all.sh` resets the database and deletes frontend server-side session files.

```bash
bash reset_all.sh
```

Only run reset scripts against a database you are allowed to clear.

### Database Demo Scripts

- `database_demo.py`: prints schema, user data, file metadata, and statistics.
- `live_db_demo.py`: interactive teacher/demo script for database inspection.

### Attack/Demo Scripts

The `SecureTextDrive-Backend/attacks` folder contains educational scripts:

- `ddos.py`: sends many login requests to simulate load/abuse.
- `password_attack.py`: brute-forces affine-cipher password transforms.
- `sqlinjection.py`: calls the protected delete-all endpoint to demonstrate safe mode behavior.

Run these only in a local/demo environment you control.

## Security Notes

This project is educational. It demonstrates security concepts, but several areas should be improved before production use.

### Good Design Ideas Demonstrated

- Backend stores encrypted file content instead of plaintext.
- Backend receives public keys, not user private keys.
- File content is separated from account/session handling.
- Restricted mode can block data access while keeping the service online.
- The database can be inspected to show encrypted bytes and metadata.

### Current Limitations

- Database credentials and Flask `secret_key` values are currently hardcoded in source files.
- The repo was public with committed secrets, so credentials should be rotated.
- Flask runs with `debug=True`, which is development-only.
- `CORS(app)` enables broad CORS behavior.
- Passwords use a reversible affine cipher instead of secure password hashing.
- RSA `1024` bit keys are not recommended for modern security.
- Direct RSA file encryption is inefficient; production systems usually use hybrid encryption.
- Private keys are stored in frontend Flask server-side sessions, not in browser Web Crypto or a dedicated client keystore.
- Files uploaded from another session may be impossible to decrypt if the local/session private key is missing.
- Signature verification currently logs failure but does not clearly reject the upload.
- There is no CSRF protection on frontend form/actions.
- There is no rate limiting on login or upload endpoints.
- File upload currently reads files as text, not arbitrary binary files.

### Production-Oriented Changes to Make

- Move all secrets to environment variables or a secret manager.
- Rotate exposed database and mail credentials.
- Replace affine password encryption with `werkzeug.security` or `bcrypt`/`argon2`.
- Disable Flask debug mode in deployed environments.
- Add CSRF protection for browser-facing routes.
- Add rate limiting for auth and upload endpoints.
- Restrict CORS origins.
- Use AES-GCM for file content and RSA/ECC only to wrap the symmetric key.
- Store private keys in a browser-controlled keystore for true end-to-end encryption.
- Add tests for auth, upload, decryption, restricted mode, and failure cases.

## Troubleshooting

### `ModuleNotFoundError`

Make sure the virtual environment is activated and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Frontend Cannot Connect to Backend

Check that the backend is running and that `BACKEND_URL` points to the correct port:

```text
Full backend:       http://127.0.0.1:8000/api
Restricted backend: http://127.0.0.1:8001/api
```

### Uploads Are Disabled

You are likely using restricted mode. Start full mode or switch the UI mode to `Full`.

### Summarization Fails

Set `GOOGLE_API_KEY` before starting the frontend:

```bash
export GOOGLE_API_KEY="your-api-key"
```

On PowerShell:

```powershell
$env:GOOGLE_API_KEY="your-api-key"
```

### Private Key Not Found

The file was probably uploaded in a different session, the frontend session was cleared, or the `.flask_session` directory was deleted. Because private keys are not stored in the backend, that session cannot decrypt the file without the original private key.

### Database Reset Does Not Work

Check the database environment variables used by `reset_db.py`:

```bash
export DB_HOST="..."
export DB_NAME="..."
export DB_USER="..."
export DB_PASSWORD="..."
export DB_PORT="5432"
```

## Suggested Improvements

- Add a proper migration file for the `users` and `filecon` tables.
- Add `.env.example` with safe placeholder values.
- Refactor database settings in the backend to read from environment variables.
- Add unit and integration tests.
- Add a health-check route.
- Replace duplicate password/RSA helper modules with shared code.
- Remove stale templates/routes for removed forgot-password and OTP features.
- Add structured logging instead of `print`.
- Add Docker Compose for Flask apps and PostgreSQL.
- Document a real deployment target.

## License

No license file is currently included. Add a license before distributing or accepting external contributions.
