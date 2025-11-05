import psycopg2
import binascii
from password_encrypter import decrypt

# Database connection details
hostname = 'postgresql-ascscs.alwaysdata.net'
database = 'ascscs_securedrive'
username = 'ascscs'
pwd = '@7sdDgVUuhCXjD6'
port_id = 5432

def get_db_connection():
    return psycopg2.connect(
        host=hostname,
        dbname=database,
        user=username,
        password=pwd,
        port=port_id
    )

def interactive_database_demo():
    """Interactive database demonstration for teachers"""
    
    print("🔐 SecureTextDrive Database Demonstration")
    print("=" * 50)
    
    while True:
        print("\nChoose what to demonstrate:")
        print("1. Show Database Schema")
        print("2. Show Users Table (with password decryption)")
        print("3. Show Files Table (with encryption details)")
        print("4. Add a test user")
        print("5. Show RSA Key Storage")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == '1':
            show_schema()
        elif choice == '2':
            show_users_with_decryption()
        elif choice == '3':
            show_files_with_encryption()
        elif choice == '4':
            add_test_user()
        elif choice == '5':
            show_rsa_keys()
        elif choice == '6':
            print("Demo completed!")
            break
        else:
            print("Invalid choice. Please try again.")

def show_schema():
    """Show database schema"""
    print("\n📊 DATABASE SCHEMA")
    print("-" * 30)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Show tables
    cur.execute("""
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    
    for table in tables:
        print(f"\n📋 Table: {table[0]} ({table[1]})")
        
        # Show columns for each table
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table[0],))
        
        columns = cur.fetchall()
        for col in columns:
            col_name, data_type, max_length, nullable = col
            length_info = f"({max_length})" if max_length else ""
            null_info = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"   • {col_name}: {data_type}{length_info} {null_info}")
    
    cur.close()
    conn.close()

def show_users_with_decryption():
    """Show users with password decryption demonstration"""
    print("\n👥 USERS TABLE WITH PASSWORD DECRYPTION")
    print("-" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password, auth FROM users")
    users = cur.fetchall()
    
    if not users:
        print("No users found in database.")
        return
    
    for i, user in enumerate(users, 1):
        email, encrypted_password, auth = user
        print(f"\n👤 User {i}:")
        print(f"   Email: {email}")
        print(f"   Encrypted Password: {encrypted_password}")
        
        # Demonstrate affine cipher decryption
        try:
            decrypted_password = decrypt(encrypted_password, 23)
            print(f"   Decrypted Password: {decrypted_password}")
            print("   ✅ Affine cipher decryption successful!")
        except Exception as e:
            print(f"   ❌ Decryption failed: {e}")
        
        print(f"   Auth Status: {auth}")
    
    cur.close()
    conn.close()

def show_files_with_encryption():
    """Show files with encryption details"""
    print("\n📁 FILES TABLE WITH ENCRYPTION DETAILS")
    print("-" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT email, fpath, fcon, encryption_method, key_size, 
               LENGTH(fcon) as content_size,
               LENGTH(pubkey) as pubkey_size,
               LENGTH(prikey) as prikey_size
        FROM filecon
    """)
    files = cur.fetchall()
    
    if not files:
        print("No files found in database.")
        return
    
    for i, file in enumerate(files, 1):
        email, filename, encrypted_content, method, key_size, content_size, pubkey_size, prikey_size = file
        print(f"\n📄 File {i}:")
        print(f"   Owner: {email}")
        print(f"   Filename: {filename}")
        print(f"   Encryption Method: {method}")
        print(f"   Key Size: {key_size} bits")
        print(f"   Encrypted Content Size: {content_size} bytes")
        print(f"   Public Key Size: {pubkey_size} characters")
        print(f"   Private Key Size: {prikey_size} characters")
        
        # Show first few bytes of encrypted content
        if encrypted_content:
            content_preview = str(encrypted_content)[:100] + "..." if len(str(encrypted_content)) > 100 else str(encrypted_content)
            print(f"   Content Preview: {content_preview}")
        
        print("   🔒 File is RSA encrypted and stored securely!")
    
    cur.close()
    conn.close()

def add_test_user():
    """Add a test user to demonstrate the process"""
    print("\n➕ ADD TEST USER")
    print("-" * 20)
    
    email = input("Enter email for test user: ")
    password = input("Enter password for test user: ")
    
    # Encrypt password using affine cipher (like the frontend does)
    from password_encrypter import encrypt
    encrypted_password = encrypt(password, 23)
    
    print(f"\nPassword encryption process:")
    print(f"   Original: {password}")
    print(f"   Encrypted: {encrypted_password}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"❌ User {email} already exists!")
        else:
            # Insert new user
            cur.execute("INSERT INTO users (email, password, auth) VALUES (%s, %s, %s)",
                       (email, encrypted_password, True))
            conn.commit()
            print(f"✅ User {email} added successfully!")
            print(f"   Encrypted password stored: {encrypted_password}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error adding user: {e}")

def show_rsa_keys():
    """Show RSA key storage format"""
    print("\n🔑 RSA KEY STORAGE DEMONSTRATION")
    print("-" * 35)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT pubkey, prikey FROM filecon LIMIT 1")
    result = cur.fetchone()
    
    if not result:
        print("No RSA keys found in database.")
        return
    
    pubkey, prikey = result
    
    print("📋 Public Key (PEM format):")
    print("-" * 30)
    print(pubkey[:200] + "..." if len(pubkey) > 200 else pubkey)
    
    print(f"\n📋 Private Key (PEM format):")
    print("-" * 30)
    print(prikey[:200] + "..." if len(prikey) > 200 else prikey)
    
    print(f"\n📊 Key Statistics:")
    print(f"   Public Key Length: {len(pubkey)} characters")
    print(f"   Private Key Length: {len(prikey)} characters")
    print(f"   Keys stored in PEM format for easy serialization")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        interactive_database_demo()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your database credentials are correct and the database is accessible.")

