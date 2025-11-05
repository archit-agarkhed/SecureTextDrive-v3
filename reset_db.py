import os
import psycopg2

DB_HOST = os.getenv('DB_HOST', 'postgresql-ascscs.alwaysdata.net')
DB_NAME = os.getenv('DB_NAME', 'ascscs_securedrive')
DB_USER = os.getenv('DB_USER', 'ascscs')
DB_PASSWORD = os.getenv('DB_PASSWORD', '@7sdDgVUuhCXjD6')
DB_PORT = int(os.getenv('DB_PORT', '5432'))

def main() -> None:
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
    )
    cur = conn.cursor()
    # Truncate file and user data; restart identity and cascade for safety
    cur.execute('TRUNCATE TABLE filecon RESTART IDENTITY CASCADE;')
    cur.execute('TRUNCATE TABLE users RESTART IDENTITY CASCADE;')
    conn.commit()
    cur.close()
    conn.close()
    print('Database reset: tables users and filecon truncated.')

if __name__ == '__main__':
    main()


