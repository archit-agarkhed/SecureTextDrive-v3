import binascii
import hashlib
import os
import re
import time
import rsa
from flask import send_file
from io import BytesIO
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from flask import Blueprint, render_template, request, Response,  session, flash, redirect, url_for, jsonify
import requests
from rsa_utils import generate_rsa_key_pair, rsa_encrypt, serialize_public_key,serialize_private_key
from password_encrypter import encrypt , decrypt
from rsa_utils import rsa_decrypt
import google.generativeai as genai

views = Blueprint('views', __name__)

# Backend server URL (configurable via BACKEND_URL env var)
server_url = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000/api')

def current_server_url():
    return session.get('backend_url', server_url)

@views.route('/set_backend', methods=['POST'])
def set_backend():
    data = request.json or {}
    mode = data.get('mode')
    url = data.get('url')
    if mode in ('full', 'restricted'):
        session['backend_url'] = 'http://127.0.0.1:8000/api' if mode == 'full' else 'http://127.0.0.1:8001/api'
        return jsonify({"message": "Backend switched", "backend_url": session['backend_url']}), 200
    if url:
        session['backend_url'] = url
        return jsonify({"message": "Backend switched", "backend_url": session['backend_url']}), 200
    return jsonify({"error": "Provide 'mode' as 'full'|'restricted' or 'url'"}), 400

@views.route('/get_backend', methods=['GET'])
def get_backend():
    url_val = current_server_url()
    mode = 'full' if url_val.endswith(':8000/api') else ('restricted' if url_val.endswith(':8001/api') else 'custom')
    return jsonify({"backend_url": url_val, "mode": mode}), 200

# Helper function to manage private keys locally
def get_private_key_for_file(filename):
    """Get private key for a specific file from local session storage"""
    private_keys = session.get('private_keys', {})
    return private_keys.get(filename)

def store_private_key_for_file(filename, private_key_pem):
    """Store private key for a specific file in local session storage"""
    if 'private_keys' not in session:
        session['private_keys'] = {}
    session['private_keys'][filename] = private_key_pem

def remove_private_key_for_file(filename):
    """Remove private key for a specific file from local session storage"""
    private_keys = session.get('private_keys', {})
    if filename in private_keys:
        del private_keys[filename]
        session['private_keys'] = private_keys

# Signup route
@views.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = encrypt(request.form.get('password'),23)
        confirm_password = encrypt(request.form.get('confirm_password'),23)

        # Send signup request to backend
        try:
            response = requests.post(f"{current_server_url()}/signup", json={
                "email": email,
                "password": password,
                "confirm_password": confirm_password
            })

            if response.status_code == 200:
                flash('Signup Successful! You can now log in.', 'success')
                return redirect(url_for('views.login'))
            else:
                error_data = response.json()
                return render_template('signup.html', error=error_data.get("error", "Unknown error"))
        except requests.exceptions.RequestException as e:
            return render_template('signup.html', error=f'Failed to connect to the server: {str(e)}')

    return render_template('signup.html')

# Login route
@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = encrypt(request.form.get('password'), 23)

        # Send login request to backend
        try:
            response = requests.post(f"{current_server_url()}/login", json={
                "email": email,
                "password": password
            })

            if response.status_code == 200:
                user_data = response.json()

                # Store user details in session
                session['email'] = user_data.get('email')
                flash('Login Successful!', 'success')
                return redirect(url_for('views.homes'))

            else:
                error_data = response.json()
                return render_template('login.html', error=error_data.get("error", "Unknown error"))

        except requests.exceptions.RequestException as e:
            return render_template('login.html', error=f'Failed to connect to the server: {str(e)}')

    return render_template('login.html')

# NOTE: Forgot-password functionality has been removed from the frontend.



# Home route
@views.route('/', methods=['GET', 'POST'])
def homes():
    email = session.get('email')
    auth = session.get('auth')

    # Query backend capabilities to decide if this instance can access data
    can_access_data = False
    try:
        caps_resp = requests.get(f"{current_server_url()}/capabilities", timeout=5)
        if caps_resp.status_code == 200:
            caps = caps_resp.json()
            can_access_data = bool(caps.get('dataAccessEnabled', False))
    except requests.exceptions.RequestException:
        can_access_data = False

    session['can_access_data'] = can_access_data

    # If data access is disabled, don't even try retrieving files
    if not can_access_data or not email:
        return render_template('home.html', email=email, auth=auth, file_list=[], can_access_data=can_access_data)

    try:
        response = requests.post(f"{current_server_url()}/retrieve_file", json={
            "email": email,
            "auth": auth
        })

        if response.status_code == 200:
            data = response.json()
            file_list = data.get('files', [])
            return render_template('home.html',  email=email, auth=auth, file_list=file_list, can_access_data=can_access_data)
        else:
            return render_template('home.html',  email=email, auth=auth, file_list=[], can_access_data=can_access_data)
    except requests.exceptions.RequestException:
        return render_template('home.html', email=email, auth=auth, file_list=[], can_access_data=can_access_data)
###
@views.route('/logout', methods=['GET'])
def logout():
    # Preserve private keys across logout so uploaded files remain decryptable
    # (store them temporarily, clear session, then restore the keys only)
    private_keys = session.get('private_keys')
    session.clear()
    if private_keys:
        session['private_keys'] = private_keys
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('views.homes'))  # Redirect to the home page or login page

"""
Removed 2FA toggle and OTP verification routes.
"""

# Route to handle file uploads from the frontend
@views.route('/api/upload_file', methods=['POST'])
def upload_file():
    email = session.get('email')
    auth = session.get('auth')
    can_access_data = session.get('can_access_data', False)

    if not email:
        return jsonify({"error": "User is not logged in"}), 403

    if not can_access_data:
        return jsonify({"error": "This client is in restricted mode. Uploads are disabled."}), 403

    # Retrieve file data from request.json (as it's coming from the frontend as JSON)
    data = request.json
    filename = data.get('filename')
    file_content = data.get('content')

    # Debugging logs to verify data is being correctly received
    print(f"\nUploader Info\nEmail: {email}\nAuth: {auth}\nFilename: {filename}\n\n")

    if not filename or not file_content:
        return jsonify({"error": "Missing required fields"}), 400

    # Choose RSA key size based on auth (1 for 2048, else 1024)
    key_size = 2048 if auth == 1 else 1024
    encryption_method = "RSA"
    
    # Start timing before encryption
    start_time = time.time()
    
    # Generate RSA key pair for file encryption
    private_key, public_key = generate_rsa_key_pair(key_size)
    encrypted_content = rsa_encrypt(public_key, file_content)
    
    # Serialize the keys
    public_key_serialized = serialize_public_key(public_key)
    private_key_serialized = serialize_private_key(private_key)
    
    # Store private key locally in session (CLIENT-SIDE KEY MANAGEMENT)
    if 'private_keys' not in session:
        session['private_keys'] = {}
    session['private_keys'][filename] = private_key_serialized.decode('utf-8')
    
    print("\n\nEncrypted file content is :\n",encrypted_content,"\n")
    print("Private key stored locally for file:", filename)
    
    # End timing after encryption
    end_time = time.time()
    encryption_time = end_time - start_time
    print('time to encrypt', encryption_time)
    
    # Generate separate signing key pair for digital signatures
    (s_public_key, s_private_key) = rsa.newkeys(2048)
    digest = hashlib.sha256(encrypted_content).digest()
    signature = rsa.sign(digest, s_private_key, 'SHA-256')
    
    # Send ONLY public data to backend (NO private keys sent to server)
    try:
        response = requests.post(f"{current_server_url()}/upload_file", json={
            "email": email,
            "filename": filename,
            "content": encrypted_content.hex(),
            "public_key": public_key_serialized.decode('utf-8'),
            "encryption_method": encryption_method,
            "key_size": key_size,
            "signature": signature.hex(),
            "digest": digest.hex(),
            "sign_public_key": s_public_key.save_pkcs1().decode('utf-8')
        })

        if response.status_code == 200:
            return jsonify({"message": f"File uploaded successfully with RSA encryption (key size: {key_size})"}), 200
        else:
            # Try to surface backend error details if available
            try:
                error_data = response.json()
                detail = error_data.get("error", "Failed to upload the file")
            except ValueError:
                detail = response.text or "Failed to upload the file"
            return jsonify({"error": detail}), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to the backend: {str(e)}"}), 500

@views.route('/preview_file', methods=['POST'])
def preview_file():
    email = session.get('email')  # Retrieve the email from the session
    can_access_data = session.get('can_access_data', False)

    if not email:
        flash("You must be logged in to preview files.", "error")
        return redirect(url_for('views.login'))  # Redirect to login if not authenticated

    if not can_access_data:
        return jsonify({"error": "This client is in restricted mode. Preview is disabled."}), 403

    filename = request.json.get('filename')  # Retrieve filename from JSON payload

    if not filename:
        return jsonify({"error": "Filename is required."}), 400

    # Check if private key exists locally (CLIENT-SIDE KEY MANAGEMENT)
    private_keys = session.get('private_keys', {})
    private_key_pem = private_keys.get(filename)
    
    if not private_key_pem:
        flash("Private key not found locally. File may have been uploaded from a different session or the session has expired.", "error")
        return jsonify({"error": "Private key not found locally"}), 400

    # Get encrypted content and public key from backend (NO private key from server)
    api_url = f"{current_server_url()}/get_file_content"
    payload = {'email': email, 'filename': filename}

    try:
        # Make a POST request with the JSON payload
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            # Extract only encrypted content and public key from server response
            data = response.json()
            encrypted_content = data['content']
            public_key = data['public_key']
            
            print("Encryption Details")
            print(f"Encrypted Content: {encrypted_content}, Type: {type(encrypted_content)}")
            print(f"Public Key: {public_key}, Type: {type(public_key)}")
            print(f"Private Key: Retrieved from local session storage")
            
            # Clean the encrypted content
            hex_content = encrypted_content.replace('\\x', '')  # Remove \x prefixes
            print('hex_content: ',hex_content)
            
            try:
                encrypted_bytes = bytes.fromhex(hex_content)  # Convert hex to bytes
                print('\nEncrypted_bytes',encrypted_bytes)
            except ValueError as e:
                flash("Invalid encrypted content format: " + str(e), "error")
                return redirect(url_for('views.homes'))

            # Load the private key from local storage
            try:
                private_key_obj = serialization.load_pem_private_key(
                    private_key_pem.encode(),  # Convert private key to bytes
                    password=None
                )
            except ValueError as e:
                flash("Invalid private key format: " + str(e), "error")
                return redirect(url_for('views.homes'))

            # Decrypt the file content using the locally stored private key
            try:
                decrypted_content = rsa_decrypt(private_key_obj, encrypted_bytes)
                print('\nDecrypted file content:', decrypted_content)
                return jsonify({"message": f"{decrypted_content}"}), 200
            except Exception as e:
                flash(f"Decryption failed: {str(e)}", "error")
                return redirect(url_for('views.homes'))

        else:
            # Handle error response from backend
            error_data = response.json()
            flash(error_data.get("error", "Failed to retrieve file content."), "error")
            return redirect(url_for('views.homes'))
    except requests.exceptions.RequestException as e:
        flash(f"Failed to connect to the server: {str(e)}", "error")
        return redirect(url_for('views.homes'))

@views.route('/delete_file', methods=['POST'])
def delete_file():

    email = session.get('email')
    can_access_data = session.get('can_access_data', False)
    if not email:
        flash("You must be logged in to delete files.", "error")
        return redirect(url_for('views.login'))  # Redirect to login if not authenticated

    if not can_access_data:
        return jsonify({"error": "This client is in restricted mode. Delete is disabled."}), 403


    filename = request.json.get('filename')  # Retrieve filename from JSON payload
    if not filename:
        return jsonify({"error": "Filename is required."}), 400

    # Prepare the request to the backend API
    api_url = f"{current_server_url()}/delete_file"
    payload = {'email': email, 'filename': filename}

    try:
        # Make a DELETE request with the JSON payload

        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            # Handle successful deletion - also remove private key from local storage
            remove_private_key_for_file(filename)
            data = response.json()
            flash(data.get("message", "File deleted successfully."), "success")
            return jsonify({"message": "File deleted successfully."}), 200

        else:
            # Handle error response from backend
            error_data = response.json()
            flash(error_data.get("error", "Failed to delete the file."), "error")
            return jsonify({"error": "Failed to delete the file."}), 400
    except requests.exceptions.RequestException as e:
        flash(f"Failed to connect to the server: {str(e)}", "error")
        return jsonify({"error": f"Failed to connect to the server: {str(e)}"}), 500

# ---------- Summarization (Gemini) ----------
def _ensure_genai_configured():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise RuntimeError('GOOGLE_API_KEY is not set')
    # Configure once per process; calling again is cheap/no-op
    genai.configure(api_key=api_key)

def _normalize_model_name(name: str) -> str:
    # genai.GenerativeModel typically expects names without the 'models/' prefix
    return name.split('/')[-1]

def _select_available_model() -> str:
    _ensure_genai_configured()
    # Allow explicit override via env
    env_model = os.getenv('GOOGLE_GEMINI_MODEL')
    if env_model:
        return _normalize_model_name(env_model)
    try:
        models = list(genai.list_models())
    except Exception:
        models = []

    # Build a quick lookup of model metadata by short and full names
    by_name = {}
    for m in models:
        short = _normalize_model_name(getattr(m, 'name', ''))
        full = getattr(m, 'name', '')
        by_name[short] = m
        by_name[full] = m

    candidates = [
        'gemini-2.5-flash-lite',  # user requested
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-1.5-pro',
        'gemini-1.0-pro',
        'gemini-pro',
    ]

    # If list_models worked, choose the first with generateContent support
    if by_name:
        for c in candidates:
            m = by_name.get(c) or by_name.get(f'models/{c}')
            if not m:
                continue
            methods = set(getattr(m, 'supported_generation_methods', []) or [])
            if not methods or 'generateContent' in methods:
                return _normalize_model_name(getattr(m, 'name', c))

    # Fallback: return the first candidate (SDK will error if unavailable)
    return candidates[0]

def _summarize_chunked(text: str) -> str:
    """Summarize long text with chunk+merge to stay under model limits."""
    _ensure_genai_configured()
    chosen_model = _select_available_model()
    model = genai.GenerativeModel(chosen_model)

    # Simple char-based chunking (approx). Adjust as needed.
    max_chunk = 8000
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)] or [""]

    partial_summaries = []
    for ch in chunks:
        prompt = f"Summarize the following text concisely in 5-7 bullet points.\n\nText:\n{ch}"
        resp = model.generate_content(prompt)
        partial_summaries.append(resp.text.strip() if getattr(resp, 'text', None) else '')

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    # Merge pass
    merge_input = "\n\n".join(partial_summaries)
    merge_prompt = (
        "Combine the following partial summaries into a single, clear summary with 6-10 concise bullet points.\n\n"
        f"Partial summaries:\n{merge_input}"
    )
    merge_resp = model.generate_content(merge_prompt)
    return merge_resp.text.strip() if getattr(merge_resp, 'text', None) else ""

@views.route('/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        if not text or not isinstance(text, str):
            return jsonify({"error": "Missing 'text'"}), 400

        # Optional basic guard on length
        if len(text) > 500000:  # 500k chars safety cap
            return jsonify({"error": "Text too large to summarize in one request."}), 413

        summary = _summarize_chunked(text)
        return jsonify({"summary": summary}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500
