import sqlite3

conn = sqlite3.connect('attendance.db')  # use your actual DB filename
cursor = conn.cursor()

cursor.execute("DELETE FROM attendance WHERE date > DATE('now', 'localtime')")
deleted = cursor.rowcount
conn.commit()
conn.close()

print(f"{deleted} future attendance entries deleted.")
