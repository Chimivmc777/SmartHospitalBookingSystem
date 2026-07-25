import mysql.connector
from faker import Faker
import random

fake = Faker()

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

db = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)

cursor = db.cursor()

specializations = [
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Pediatrics",
    "Dermatology",
    "Gynecology",
    "General Medicine"
]

qualifications = [
    "MBBS",
    "MD",
    "MS",
    "MDS",
    "DM",
    "DNB"
]

for i in range(100):

    hospital_id = random.randint(1,4)

    department_id = random.randint(1,15)

    name = fake.name()

    specialization = random.choice(specializations)

    qualification = random.choice(qualifications)

    experience = random.randint(1,25)

    license_number = f"BMCL-{1000+i}"

    email = f"doctor{i}@health.bt"

    phone = f"+97517{random.randint(100000,999999)}"

    password = "password123"

    consultation_fee = random.randint(300,1200)

    cursor.execute("""
    INSERT INTO doctors
    (
    hospital_id,
    department_id,
    name,
    specialization,
    qualification,
    experience,
    license_number,
    email,
    phone,
    password,
    consultation_fee
    )

    VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

    """,
    (
        hospital_id,
        department_id,
        name,
        specialization,
        qualification,
        experience,
        license_number,
        email,
        phone,
        password,
        consultation_fee
    ))

db.commit()

print("✅ 100 Doctors Added Successfully!")

cursor.close()
db.close()