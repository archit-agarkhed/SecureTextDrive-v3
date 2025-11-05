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

def show_database_structure():
    """Show the database schema and tables"""
    print("=" * 60)
    print("DATABASE STRUCTURE DEMONSTRATION")
    print("=" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Show all tables
    print("\n1. DATABASE TABLES:")
    print("-" * 30)
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    for table in tables:
        print(f"   • {table[0]}")
    
    # Show USERS table structure
    print("\n2. USERS TABLE STRUCTURE:")
    print("-" * 30)
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'users'
    """)
    columns = cur.fetchall()
    for col in columns:
        print(f"   • {col[0]} ({col[1]}) - Nullable: {col[2]}")
    
    # Show filecon table structure
    print("\n3. FILECON TABLE STRUCTURE:")
    print("-" * 30)
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'filecon'
    """)
    columns = cur.fetchall()
    for col in columns:
        print(f"   • {col[0]} ({col[1]}) - Nullable: {col[2]}")
    
    cur.close()
    conn.close()

def show_users_data():
    """Show user data with password decryption demonstration"""
    print("\n4. USERS TABLE DATA:")
    print("-" * 30)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT email, password, auth FROM users")
    users = cur.fetchall()
    
    for user in users:
        email, encrypted_password, auth = user
        print(f"\n   Email: {email}")
        print(f"   Encrypted Password: {encrypted_password}")
        
        # Decrypt password to show the affine cipher in action
        try:
            decrypted_password = decrypt(encrypted_password, 23)
            print(f"   Decrypted Password: {decrypted_password}")
        except:
            print(f"   Decrypted Password: [Could not decrypt]")
        
        print(f"   Auth Status: {auth}")
        print("-" * 40)
    
    cur.close()
    conn.close()

def show_files_data():
    """Show file data with encryption details"""
    print("\n5. FILECON TABLE DATA:")
    print("-" * 30)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT email, fpath, fcon, encryption_method, key_size 
        FROM filecon 
        LIMIT 3
    """)
    files = cur.fetchall()
    
    for file in files:
        email, filename, encrypted_content, method, key_size = file
        print(f"\n   Email: {email}")
        print(f"   Filename: {filename}")
        print(f"   Encryption Method: {method}")
        print(f"   Key Size: {key_size} bits")
        print(f"   Encrypted Content (first 50 chars): {str(encrypted_content)[:50]}...")
        print(f"   Content Size: {len(encrypted_content)} bytes")
        print("-" * 40)
    
    cur.close()
    conn.close()

def show_statistics():
    """Show database statistics"""
    print("\n6. DATABASE STATISTICS:")
    print("-" * 30)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Count users
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    print(f"   Total Users: {user_count}")
    
    # Count files
    cur.execute("SELECT COUNT(*) FROM filecon")
    file_count = cur.fetchone()[0]
    print(f"   Total Files: {file_count}")
    
    # Show file sizes
    cur.execute("SELECT AVG(LENGTH(fcon)) FROM filecon")
    avg_size = cur.fetchone()[0]
    if avg_size:
        print(f"   Average File Size: {avg_size:.2f} bytes")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        show_database_structure()
        show_users_data()
        show_files_data()
        show_statistics()
        
        print("\n" + "=" * 60)
        print("DATABASE DEMONSTRATION COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure your database credentials are correct and the database is accessible.")

