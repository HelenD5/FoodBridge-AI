from services.database import get_connection

try:
    conn = get_connection()
    print("SUCCESS! MySQL Connected!")
    print("Database:", conn.database)
    conn.close()

except Exception as e:
    print("Connection failed:", e)