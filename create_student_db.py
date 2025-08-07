import sqlite3
import random
from faker import Faker

# Initialize Faker
fake = Faker()

# Connect to SQLite
conn = sqlite3.connect("student.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    grade INTEGER,
    city TEXT,
    enrollment_date TEXT
)
""")

# Insert 100 fake student records
for _ in range(100):
    name = fake.name()
    age = random.randint(18, 25)
    grade = random.randint(50, 100)
    city = fake.city()
    enrollment_date = fake.date_between(start_date='-2y', end_date='today').isoformat()

    cursor.execute("""
    INSERT INTO students (name, age, grade, city, enrollment_date)
    VALUES (?, ?, ?, ?, ?)
    """, (name, age, grade, city, enrollment_date))

# Commit and close
conn.commit()
conn.close()

print("✅ student.db with 100 records created.")
