import hashlib
import os

from flask import Flask, request, jsonify, session, flash, Response
import binascii
from mail_config import mail
from mail_settings import *
from flask_mail import Message
import psycopg2
import rsa
from flask_cors import CORS

from password_encrypter import decrypt

app = Flask(__name__)
CORS(app)
app.secret_key = 'abcdlala'

# Capability flags (configurable via environment variables)
# When DATA_ACCESS_ENABLED is false, this backend instance will allow login
# but will block any data access operations (upload/list/get/delete files).
DATA_ACCESS_ENABLED = os.getenv('DATA_ACCESS_ENABLED', '1') == '1'

# Database connection details
hostname = 'postgresql-ascscs.alwaysdata.net'
database = 'ascscs_securedrive'
username = 'ascscs'
pwd = '@7sdDgVUuhCXjD6'
port_id = 5432

# Mail configuration (tolerate missing MAIL_PASSWORD)
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', globals().get('MAIL_PASSWORD'))
MAIL_AVAILABLE = bool(MAIL_USERNAME) and bool(MAIL_SERVER) and bool(MAIL_PORT) and bool(MAIL_PASSWORD)

if MAIL_AVAILABLE:
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = MAIL_PORT
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
    mail.init_app(app)
else:
    # Initialize anyway to keep interface consistent, but won't send mail
    try:
        mail.init_app(app)
    except Exception:
        pass


def get_db_connection():
    return psycopg2.connect(
        host=hostname,
        dbname=database,
        user=username,
        password=pwd,
        port=port_id
    )

# Simple password reset email sender (replaces OTP utilities)
def send_reset_email(mail, email, password):
    if not MAIL_AVAILABLE:
        print("MAIL not configured. Skipping send_reset_email.")
        return False
    try:
        msg = Message('Your Password', sender='support@hmmbo.com', recipients=[email])
        msg.body = f"Your password is: {password}."
        mail.send(msg)
        return True
    except Exception as e:
        print("Failed to send reset email:", e)
        return False

# Signup API
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not email or not password or not confirm_password:
        return jsonify({"error": "Email, password, and confirm password are required."}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the email already exists
        cur.execute('SELECT * FROM USERS WHERE email = %s', (email,))
        if cur.fetchone() is not None:
            return jsonify({"error": "Email already exists."}), 400

        # Insert new user into the database
        cur.execute('INSERT INTO USERS(email, password, auth) VALUES(%s, %s, %s)', (email, password, True))
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "Signup Successful."}), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500

# Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the email and password match any entry in the database
        cur.execute('SELECT email, password FROM USERS WHERE email = %s AND password = %s', (email, password))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session['email'] = user[0]
            print('\nLogin Successful!')
            return jsonify({
                "message": "Login Successful!",
                "email": session['email']
            }), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

# NOTE: Forgot-password API removed. Password reset via email has been intentionally disabled.

"""
OTP/2FA functionality removed: gen_otp and /api/auth endpoints deleted.
"""

@app.route('/api/home', methods=['GET'])
def home():
    email = session.get('email')
    if email:
        return jsonify({"email": email}), 200
    else:
        return jsonify({"error": "Unauthorized access"}), 401

# Public capabilities endpoint so frontend can adapt UI/flows
@app.route('/api/capabilities', methods=['GET'])
def capabilities():
    return jsonify({
        "dataAccessEnabled": DATA_ACCESS_ENABLED,
        "mode": "full" if DATA_ACCESS_ENABLED else "restricted"
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    # Clear the user session
    session.clear()
    # Optionally, you can also add a print statement for logging
    print("\nUser logged out successfully.")
    # Return a success message
    return jsonify({"message": "Logged out successfully."}), 200

"""
2FA toggle endpoint removed.
"""

# Route to handle file upload and storage in the database
# Route to handle file upload and storage in the database
@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    if not DATA_ACCESS_ENABLED:
        return jsonify({"error": "Data access is disabled on this instance (restricted mode)."}), 403
    try:
        # Get the data from the request
        data = request.json
        email = data.get('email')
        filename = data.get('filename')
        encrypted_content_hex = data.get('content')
        public_key_pem = data.get('public_key')
        encryption_method = data.get('encryption_method')  # New field for encryption method
        key_size = data.get('key_size')  # New field for key size
        signature = data.get('signature')
        s_public_key = data.get('sign_public_key')

        print(email,filename,encrypted_content_hex,public_key_pem,encryption_method,key_size)

        # Check if email, filename, or encrypted content is missing
        if not email or not filename or not encrypted_content_hex or not public_key_pem or not encryption_method or not key_size:
            return jsonify({"error": "Missing required fields"}), 400

        # Decode the hex-encoded encrypted content back to bytes
        try:
            encrypted_content = binascii.unhexlify(encrypted_content_hex)
        except binascii.Error:
            return jsonify({"error": "Invalid encrypted content format"}), 400

        msg = binascii.unhexlify(encrypted_content_hex)  # Decode the hex string
        signature = binascii.unhexlify(signature)  # Convert signature back to bytes
        s_public_key = rsa.PublicKey.load_pkcs1(s_public_key.encode('utf-8'))
        digest = hashlib.sha256(msg).digest()  #

        print(msg)
        print(digest)
        print(signature)
        print(s_public_key)

        try:
            rsa.verify(digest, signature, s_public_key)
            print("\nSignature verification successful. Message is authentic.\n")
        except rsa.VerificationError:
            print("\nSignature verification failed. Message is not authentic.\n")


        # Store the encrypted content and public key into the database
        # Assuming you already have a 'filecon' table with columns: email, fpath, fcon, pubkey, encryption_method, key_size
        conn = get_db_connection()
        cur = conn.cursor()

        check_file_query = '''
                    SELECT COUNT(*) FROM filecon WHERE email = %s AND fpath = %s
                '''
        cur.execute(check_file_query, (email, filename))
        file_exists = cur.fetchone()[0] > 0  # Fetch the count and check if it's greater than 0

        if file_exists:
            cur.close()
            conn.close()
            return jsonify({"error": "File already exists."}), 409


        insert_filecon = '''
            INSERT INTO filecon (email, fpath, fcon, pubkey, encryption_method, key_size, prikey) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''

        cur.execute(insert_filecon, (email, filename, encrypted_content, public_key_pem, encryption_method, key_size, ''))
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "File uploaded and stored successfully"}), 200

    except Exception as error:
        print("Error during file upload:", error)
        return jsonify({"error": str(error)}), 500

@app.route('/api/retrieve_file', methods=['POST'])
def retrieve_file():
    if not DATA_ACCESS_ENABLED:
        return jsonify({"error": "Data access is disabled on this instance (restricted mode)."}), 403
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        # Database connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve all file info based on email
        cur.execute('SELECT fpath, fcon, pubkey, key_size FROM filecon WHERE email = %s', (email,))
        file_records = cur.fetchall()  # Fetch all records

        if not file_records:
            return jsonify({"error": "No files found for this email"}), 404

        files = []
        for record in file_records:
            file_path = record[0]
            encrypted_content = record[1]
            pukey = record[2]
            ks = record[3]
            print("\nFile Path : Content")
            print(file_path,":", encrypted_content,"\n\n")
            decrypted_content = encrypted_content  # Decrypt if necessary
            files.append({
                "filename": file_path,
                "content": decrypted_content,
                "public_key": pukey,
                "key_size": ks
                # Include the decrypted content if necessary
            })

        return jsonify({"files": files}), 200  # Return the list of files in JSON format

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        cur.close()
        conn.close()

safe_mode = True
@app.route('/api/delete_all_filecon', methods=['DELETE'])
def delete_all_filecon():
    if safe_mode:  # Check if safe_mode is enabled
        return jsonify({"error": "Deletion is not allowed in safe mode."}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # SQL query to delete all rows in the filecon table
        cur.execute('DELETE FROM filecon;')
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "All contents deleted successfully."}), 200

    except Exception as error:
        print("Error during deletion:", error)
        return jsonify({"error": "An error occurred during deletion."}), 500
@app.route('/api/get_file_content', methods=['POST'])
def get_file_content():
    if not DATA_ACCESS_ENABLED:
        return jsonify({"error": "Data access is disabled on this instance (restricted mode)."}), 403
    data = request.json
    email = data.get('email')
    filename = data.get('filename')

    if not email or not filename:
        return jsonify({"error": "Email and filename are required"}), 400

    try:
        # Database connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve the encrypted content and public key based on email and filename
        cur.execute('SELECT fcon, pubkey FROM filecon WHERE email = %s AND fpath = %s', (email, filename))
        result = cur.fetchone()

        if result is None:
            return jsonify({"error": "File not found"}), 404

        encrypted_content = result[0]
        public_key = result[1]

        return jsonify({
            "filename": filename,
            "content": encrypted_content,
            "public_key": public_key
        }), 200

    except Exception as error:
        print("Error retrieving file content:", error)
        return jsonify({"error": "An error occurred while retrieving file content."}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    if not DATA_ACCESS_ENABLED:
        return jsonify({"error": "Data access is disabled on this instance (restricted mode)."}), 403
    data = request.json
    email = data.get('email')
    filename = data.get('filename')

    if not email or not filename:
        return jsonify({"error": "Email and filename are required"}), 400

    try:
        # Database connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Delete the file entry based on email and filename
        cur.execute('DELETE FROM filecon WHERE email = %s AND fpath = %s', (email, filename))
        conn.commit()  # Commit the changes to the database

        # Check if any rows were affected
        if cur.rowcount == 0:
            return jsonify({"error": "File not found"}), 404

        return jsonify({"message": "File deleted successfully."}), 200

    except Exception as error:
        print("Error deleting file:", error)
        return jsonify({"error": "An error occurred while deleting the file."}), 500

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))
    app.run(debug=True, port=port)