from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os
import qrcode
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_file
)
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from flask import Flask, render_template, request, redirect, send_file, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

app = Flask(__name__)
app.secret_key = "smart_hospital_secret_key"

def send_email(to_email, subject, body):

    sender_email = "chimininja777@gmail.com"
    sender_password = "zdfo qcsz oxtl wzxi"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(sender_email, sender_password)

    server.sendmail(
        sender_email,
        to_email,
        message.as_string()
    )

    server.quit()

# ==========================
# Database Connection
# ==========================
try:
    db = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
    cursor = db.cursor()
    print("✅ Connected to MySQL successfully!")

except mysql.connector.Error as err:
    print("❌ Database Connection Error:", err)


# ==========================
# Home Page
# ==========================
@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# Registration
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        gender = request.form["gender"]
        age = request.form["age"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]
        password = request.form["password"]
        password = generate_password_hash(password)

        try:

            sql = """
            INSERT INTO patients
            (name, gender, age, phone, email, address, password)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """

            cursor.execute(sql,
                (
                    name,
                    gender,
                    age,
                    phone,
                    email,
                    address,
                    password
                )
            )

            db.commit()

            return redirect("/login")

        except mysql.connector.Error as err:
            return f"Database Error : {err}"

    return render_template("register.html")


# ==========================
# Login
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM patients WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if user and check_password_hash(user[7], password):

            session["patient_id"] = user[0]
            session["patient_name"] = user[1]

            return redirect("/dashboard")

        else:

            return """
            <h2 style='color:red;text-align:center'>
            Invalid Email or Password
            </h2>

            <center>
                <a href="/login">Try Again</a>
            </center>
            """

    return render_template("login.html")


# ==========================
# Dashboard
# ==========================
@app.route("/dashboard")
def dashboard():

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE patient_id=%s
        AND status='Unread'
    """, (session["patient_id"],))

    unread_notifications = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",
        name=session["patient_name"],
        unread_notifications=unread_notifications
    )

# ==========================
# Book Appointment
# ==========================
@app.route("/book", methods=["GET", "POST"])
def book():

    if "patient_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        patient_id = session["patient_id"]
        schedule_id = request.form["schedule_id"]

        # Get schedule details
        cursor.execute("""
            SELECT doctor_id,
                   available_date,
                   start_time
            FROM doctor_schedule
            WHERE schedule_id=%s
        """, (schedule_id,))

        schedule = cursor.fetchone()

        if schedule is None:
            return "Invalid Schedule"

        doctor_id = schedule[0]
        appointment_date = schedule[1]
        appointment_time = schedule[2]

        # Save appointment
        cursor.execute("""
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                schedule_id,
                appointment_date,
                appointment_time
            )
            VALUES (%s,%s,%s,%s,%s)
        """,
        (
            patient_id,
            doctor_id,
            schedule_id,
            appointment_date,
            appointment_time
        ))

        db.commit()

        # =====================================
        # Generate QR Code
        # =====================================

        appointment_id = cursor.lastrowid

        qr_data = f"""
Appointment ID: {appointment_id}
Patient ID: {patient_id}
Doctor ID: {doctor_id}
Date: {appointment_date}
Time: {appointment_time}
Status: Pending
"""

        qr = qrcode.make(qr_data)

        qr_path = os.path.join(
            "static",
            "qr_codes",
            f"{appointment_id}.png"
        )

        qr.save(qr_path)

        # =====================================
        # Notification for Patient
        # =====================================

        cursor.execute("""
            INSERT INTO notifications
            (patient_id, message)
            VALUES(%s,%s)
        """,
        (
            patient_id,
            "📅 Your appointment has been booked successfully."
        ))

        # =====================================
        # Notification for Doctor
        # =====================================

        cursor.execute("""
            INSERT INTO notifications
            (doctor_id, message)
            VALUES(%s,%s)
        """,
        (
            doctor_id,
            "📅 You have received a new appointment."
        ))

        db.commit()

        # =====================================
        # Send Email
        # =====================================

        cursor.execute("""
            SELECT
                p.name,
                p.email,
                d.name
            FROM patients p
            JOIN doctors d
                ON d.doctor_id=%s
            WHERE p.patient_id=%s
        """,
        (
            doctor_id,
            patient_id
        ))

        patient = cursor.fetchone()

        subject = "Appointment Booked - Smart Hospital"

        body = f"""
Dear {patient[0]},

Your appointment has been booked successfully.

Appointment ID : {appointment_id}

Doctor : Dr. {patient[2]}

Date : {appointment_date}

Time : {appointment_time}

Status : Pending

Thank you for choosing Smart Hospital.

Regards,
Smart Hospital Team
"""

        send_email(
            patient[1],
            subject,
            body
        )

        # =====================================
        # Redirect to Receipt
        # =====================================

        return redirect(f"/appointment_receipt/{appointment_id}")

    # =====================================
    # Show Available Schedules
    # =====================================

    cursor.execute("""
        SELECT
            ds.schedule_id,
            d.name,
            d.specialization,
            ds.available_date,
            ds.start_time,
            ds.end_time
        FROM doctor_schedule ds
        JOIN doctors d
            ON ds.doctor_id=d.doctor_id
        WHERE ds.status='Available'
    """)

    schedules = cursor.fetchall()

    return render_template(
        "book_appointment.html",
        schedules=schedules
    )

# ==========================
# My Appointments
# ==========================
@app.route("/appointments")
def appointments():

    if "patient_id" not in session:
        return redirect("/login")

    patient_id = session["patient_id"]

    cursor.execute("""
    SELECT
        a.appointment_id,
        d.name,
        d.specialization,
        a.appointment_date,
        a.appointment_time,
        a.status
    FROM appointments a
    JOIN doctors d
    ON a.doctor_id=d.doctor_id
    WHERE a.patient_id=%s
    ORDER BY a.appointment_date
    """, (patient_id,))

    appointments = cursor.fetchall()

    return render_template(
        "appointments.html",
        appointments=appointments
    )


# ==========================
# Logout
# ==========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================
# Cancel Appointment
# ==========================
@app.route("/cancel/<int:appointment_id>")
def cancel_appointment(appointment_id):

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        UPDATE appointments
        SET status='Cancelled'
        WHERE appointment_id=%s
        AND patient_id=%s
    """, (appointment_id, session["patient_id"]))

    db.commit()

    return redirect("/appointments")

# ==========================
# Doctor Login
# ==========================
@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM doctors WHERE email=%s",
            (email,)
        )

        doctor = cursor.fetchone()

        if doctor and check_password_hash(doctor[7], password):

            session["doctor_id"] = doctor[0]
            session["doctor_name"] = doctor[2]

            return redirect("/doctor/dashboard")

        else:

            return """
            <h2 style='color:red;text-align:center;margin-top:80px;'>
            Invalid Doctor Email or Password
            </h2>

            <center>
                <a href="/doctor/login">Try Again</a>
            </center>
            """

    return render_template("doctor_login.html")


# ==========================
# Doctor Dashboard
# ==========================
@app.route("/doctor/dashboard")
def doctor_dashboard():

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    # Pending Appointments
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=%s
        AND status='Pending'
    """, (doctor_id,))

    pending = cursor.fetchone()[0]

    # Confirmed Appointments
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=%s
        AND status='Confirmed'
    """, (doctor_id,))

    confirmed = cursor.fetchone()[0]

    # Total Prescriptions
    cursor.execute("""
        SELECT COUNT(*)
        FROM prescriptions
        WHERE doctor_id=%s
    """, (doctor_id,))

    prescriptions = cursor.fetchone()[0]

    return render_template(
        "doctor_dashboard.html",
        name=session["doctor_name"],
        pending=pending,
        confirmed=confirmed,
        prescriptions=prescriptions
    )


# ==========================
# Doctor Logout
# ==========================
@app.route("/doctor/logout")
def doctor_logout():

    session.pop("doctor_id", None)
    session.pop("doctor_name", None)

    return redirect("/")

# ==========================
# Doctor Appointments
# ==========================
@app.route("/doctor/appointments")
def doctor_appointments():

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            a.appointment_date,
            a.appointment_time,
            a.status
        FROM appointments a
        JOIN patients p
        ON a.patient_id = p.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date
    """, (session["doctor_id"],))

    appointments = cursor.fetchall()

    return render_template(
        "doctor_appointments.html",
        appointments=appointments
    )

# ==========================
# Confirm Appointment
# ==========================
@app.route("/doctor/confirm/<int:id>")
def confirm_appointment(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    # Update appointment status
    cursor.execute("""
        UPDATE appointments
        SET status='Confirmed'
        WHERE appointment_id=%s
    """, (id,))

    # Get patient id
    cursor.execute("""
        SELECT patient_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    patient = cursor.fetchone()

    # Send notification
    if patient:

        cursor.execute("""
            INSERT INTO notifications
            (patient_id, message)
            VALUES(%s,%s)
        """,
        (
            patient[0],
            "✅ Your appointment has been confirmed by the doctor."
        ))

    db.commit()

    # Get patient email and doctor name
    cursor.execute("""
        SELECT
            p.name,
            p.email,
            d.name
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        WHERE a.appointment_id=%s
    """, (id,))

    patient = cursor.fetchone()

    # Email subject
    subject = "Appointment Confirmed - Smart Hospital"

    # Email body
    body = f"""
Dear {patient[0]},

Great news!

Your appointment has been confirmed by Dr. {patient[2]}.

Please visit the hospital on your scheduled date and time.

Thank you for choosing Smart Hospital.

Regards,
Smart Hospital Team
"""

    # Send email
    send_email(
        patient[1],
        subject,
        body
    )

    return redirect("/doctor/appointments")
# ==========================
# Complete Appointment
# ==========================
@app.route("/doctor/complete/<int:id>")
def complete_appointment(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    # Update appointment status
    cursor.execute("""
        UPDATE appointments
        SET status='Completed'
        WHERE appointment_id=%s
    """, (id,))

    # Get patient id
    cursor.execute("""
        SELECT patient_id
        FROM appointments
        WHERE appointment_id=%s
    """, (id,))

    patient = cursor.fetchone()

    # Notify patient
    if patient:
        cursor.execute("""
            INSERT INTO notifications
            (patient_id, message)
            VALUES(%s,%s)
        """,
        (
            patient[0],
            "🎉 Your appointment has been completed."
        ))

    db.commit()

    return redirect("/doctor/appointments")


# ==========================
# Admin Login
# ==========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM admins WHERE username=%s",
            (username,)
        )

        admin = cursor.fetchone()

        if admin and check_password_hash(admin[2], password):

            session["admin_id"] = admin[0]
            session["admin_name"] = admin[1]

            return redirect("/admin/dashboard")

        else:

            return """
            <h2 style='color:red;text-align:center;margin-top:100px;'>
            Invalid Admin Username or Password
            </h2>

            <center>
                <a href="/admin/login">Try Again</a>
            </center>
            """

    return render_template("admin_login.html")

# ==========================
# Admin Dashboard
# ==========================
@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect("/admin/login")

    # ==========================
    # Total Doctors
    # ==========================
    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cursor.fetchone()[0]

    # ==========================
    # Total Patients
    # ==========================
    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]

    # ==========================
    # Total Appointments
    # ==========================
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]

    # ==========================
    # Total Prescriptions
    # ==========================
    cursor.execute("SELECT COUNT(*) FROM prescriptions")
    total_prescriptions = cursor.fetchone()[0]

    # ==========================
    # Total Departments
    # ==========================
    cursor.execute("SELECT COUNT(*) FROM departments")
    total_departments = cursor.fetchone()[0]

    # ==========================
    # Appointment Status Counts
    # ==========================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Pending'
    """)
    pending = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Confirmed'
    """)
    confirmed = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Completed'
    """)
    completed = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Cancelled'
    """)
    cancelled = cursor.fetchone()[0]

    # ==========================
    # Monthly Appointment Statistics
    # ==========================

    cursor.execute("""
        SELECT
            MONTHNAME(appointment_date),
            COUNT(*)
        FROM appointments
        GROUP BY MONTH(appointment_date), MONTHNAME(appointment_date)
        ORDER BY MONTH(appointment_date)
    """)

    data = cursor.fetchall()

    months = []
    counts = []

    for row in data:
        months.append(row[0])
        counts.append(row[1])

    # ==========================
    # Recent Appointments
    # ==========================

    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            d.name,
            a.appointment_date,
            a.status
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_id DESC
        LIMIT 5
    """)

    recent = cursor.fetchall()

    # ==========================
    # Render Dashboard
    # ==========================

    return render_template(
        "admin_dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        total_prescriptions=total_prescriptions,
        total_departments=total_departments,
        pending=pending,
        confirmed=confirmed,
        completed=completed,
        cancelled=cancelled,
        months=months,
        counts=counts,
        recent=recent
    )
# ==========================
# Admin Logout
# ==========================
@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_name", None)

    return redirect("/")

# ==========================
# View Doctors
# ==========================
@app.route("/admin/doctors")
def admin_doctors():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cursor.execute("""
        SELECT
            d.doctor_id,
            d.name,
            dep.department_name,
            d.specialization,
            d.experience,
            d.email,
            d.phone
        FROM doctors d
        JOIN departments dep
            ON d.department_id = dep.department_id
        WHERE
            d.name LIKE %s
            OR d.email LIKE %s
            OR d.specialization LIKE %s
        ORDER BY d.doctor_id
    """,
    (
        "%" + search + "%",
        "%" + search + "%",
        "%" + search + "%"
    ))

    doctors = cursor.fetchall()

    return render_template(
        "doctors.html",
        doctors=doctors,
        search=search
    )
# ==========================
# Add Doctor
# ==========================
@app.route("/admin/add-doctor", methods=["GET", "POST"])
def add_doctor():

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        department_id = request.form["department_id"]
        name = request.form["name"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        try:
            cursor.execute("""
                INSERT INTO doctors
                (department_id, name, specialization,
                 experience, email, phone, password)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                department_id,
                name,
                specialization,
                experience,
                email,
                phone,
                password
            ))

            db.commit()

            return redirect("/admin/doctors")

        except mysql.connector.Error as err:
            return f"<h2>Database Error: {err}</h2>"

    # Load all departments
    cursor.execute("""
        SELECT department_id, department_name
        FROM departments
    """)

    departments = cursor.fetchall()

    return render_template(
        "add_doctor.html",
        departments=departments
    )

# ==========================
# Delete Doctor
# ==========================
@app.route("/admin/delete-doctor/<int:id>")
def delete_doctor(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute(
        "DELETE FROM doctors WHERE doctor_id=%s",
        (id,)
    )

    db.commit()

    return redirect("/admin/doctors")

# ==========================
# Edit Doctor
# ==========================
@app.route("/admin/edit-doctor/<int:id>", methods=["GET", "POST"])
def edit_doctor(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        department_id = request.form["department_id"]
        name = request.form["name"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]
        email = request.form["email"]
        phone = request.form["phone"]

        cursor.execute("""
            UPDATE doctors
            SET
                department_id=%s,
                name=%s,
                specialization=%s,
                experience=%s,
                email=%s,
                phone=%s
            WHERE doctor_id=%s
        """,
        (
            department_id,
            name,
            specialization,
            experience,
            email,
            phone,
            id
        ))

        db.commit()

        return redirect("/admin/doctors")

    cursor.execute("""
        SELECT *
        FROM doctors
        WHERE doctor_id=%s
    """, (id,))

    doctor = cursor.fetchone()

    return render_template(
        "edit_doctor.html",
        doctor=doctor
    )

# ==========================
# Manage Departments
# ==========================
@app.route("/admin/departments")
def departments():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
        SELECT *
        FROM departments
        ORDER BY department_id
    """)

    departments = cursor.fetchall()

    return render_template(
        "departments.html",
        departments=departments
    )

# ==========================
# Add Department
# ==========================
@app.route("/admin/add-department", methods=["GET", "POST"])
def add_department():

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        name = request.form["department_name"]
        description = request.form["description"]

        cursor.execute("""
            INSERT INTO departments
            (department_name, description)
            VALUES (%s,%s)
        """, (name, description))

        db.commit()

        return redirect("/admin/departments")

    return render_template("add_department.html")

# ==========================
# Edit Department
# ==========================
@app.route("/admin/edit-department/<int:id>", methods=["GET", "POST"])
def edit_department(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        name = request.form["department_name"]
        description = request.form["description"]

        cursor.execute("""
            UPDATE departments
            SET
                department_name=%s,
                description=%s
            WHERE department_id=%s
        """,
        (
            name,
            description,
            id
        ))

        db.commit()

        return redirect("/admin/departments")

    cursor.execute("""
        SELECT *
        FROM departments
        WHERE department_id=%s
    """, (id,))

    department = cursor.fetchone()

    return render_template(
        "edit_department.html",
        department=department
    )

# ==========================
# Delete Department
# ==========================
@app.route("/admin/delete-department/<int:id>")
def delete_department(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
        DELETE FROM departments
        WHERE department_id=%s
    """, (id,))

    db.commit()

    return redirect("/admin/departments")


# ==========================
# Delete Schedule
# ==========================
@app.route("/admin/delete_schedule/<int:id>")
def delete_schedule(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
        DELETE FROM doctor_schedule
        WHERE schedule_id=%s
    """, (id,))

    db.commit()

    return redirect("/admin/schedules")

# ==========================
# Edit Schedule
# ==========================
@app.route("/admin/edit_schedule/<int:id>", methods=["GET", "POST"])
def edit_schedule(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        available_date = request.form["available_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE doctor_schedule
            SET
                available_date=%s,
                start_time=%s,
                end_time=%s,
                status=%s
            WHERE schedule_id=%s
        """,
        (
            available_date,
            start_time,
            end_time,
            status,
            id
        ))

        db.commit()

        return redirect("/admin/schedules")

    cursor.execute("""
        SELECT
            schedule_id,
            doctor_id,
            available_date,
            start_time,
            end_time,
            status
        FROM doctor_schedule
        WHERE schedule_id=%s
    """,(id,))

    schedule = cursor.fetchone()

    return render_template(
        "edit_schedule.html",
        schedule=schedule
    )

# ==========================
# Manage Patients
# ==========================
@app.route("/admin/patients")
def admin_patients():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cursor.execute("""
        SELECT
            patient_id,
            name,
            gender,
            age,
            phone,
            email,
            address
        FROM patients
        WHERE
            name LIKE %s
            OR email LIKE %s
            OR phone LIKE %s
        ORDER BY patient_id
    """,
    (
        "%" + search + "%",
        "%" + search + "%",
        "%" + search + "%"
    ))

    patients = cursor.fetchall()

    return render_template(
        "patients.html",
        patients=patients,
        search=search
    )

# ==========================
# Delete Patient
# ==========================
@app.route("/admin/delete-patient/<int:id>")
def delete_patient(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
        DELETE FROM patients
        WHERE patient_id=%s
    """, (id,))

    db.commit()

    return redirect("/admin/patients")

# ==========================
# Admin Appointments
# ==========================
@app.route("/admin/appointments")
def admin_appointments():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            d.name,
            a.appointment_date,
            a.appointment_time,
            a.status

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN doctors d
            ON a.doctor_id = d.doctor_id

        WHERE
            p.name LIKE %s
            OR d.name LIKE %s
            OR a.status LIKE %s
            OR a.appointment_date LIKE %s

        ORDER BY a.appointment_date DESC
    """,
    (
        "%" + search + "%",
        "%" + search + "%",
        "%" + search + "%",
        "%" + search + "%"
    ))

    appointments = cursor.fetchall()

    return render_template(
        "admin_appointments.html",
        appointments=appointments,
        search=search
    )

# ==========================
# Delete Appointment
# ==========================
@app.route("/admin/delete-appointment/<int:id>")
def delete_admin_appointment(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
    DELETE FROM appointments
    WHERE appointment_id=%s
    """,(id,))

    db.commit()

    return redirect("/admin/appointments")

# ==========================
# Add Prescription
# ==========================
@app.route("/doctor/prescription/<int:appointment_id>", methods=["GET", "POST"])
def add_prescription(appointment_id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    # Get appointment details
    cursor.execute("""
        SELECT patient_id, doctor_id
        FROM appointments
        WHERE appointment_id=%s
    """, (appointment_id,))

    appointment = cursor.fetchone()

    if appointment is None:
        return "Appointment not found"

    patient_id = appointment[0]
    doctor_id = appointment[1]

    if request.method == "POST":

        diagnosis = request.form["diagnosis"]
        medicines = request.form["medicines"]
        dosage = request.form["dosage"]
        notes = request.form["notes"]

        # Save prescription
        cursor.execute("""
            INSERT INTO prescriptions
            (
                appointment_id,
                doctor_id,
                patient_id,
                diagnosis,
                medicines,
                dosage,
                notes
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            appointment_id,
            doctor_id,
            patient_id,
            diagnosis,
            medicines,
            dosage,
            notes
        ))

        db.commit()

        # Notification
        cursor.execute("""
            INSERT INTO notifications
            (patient_id, message)
            VALUES(%s,%s)
        """,
        (
            patient_id,
            "💊 Your prescription has been added. Please check your prescriptions."
        ))

        db.commit()

        # Get patient and doctor details
        cursor.execute("""
            SELECT
                p.name,
                p.email,
                d.name
            FROM patients p
            JOIN doctors d
                ON d.doctor_id=%s
            WHERE p.patient_id=%s
        """,
        (
            doctor_id,
            patient_id
        ))

        patient = cursor.fetchone()

        subject = "Prescription Added - Smart Hospital"

        body = f"""
Dear {patient[0]},

Your doctor has uploaded your prescription.

Doctor: Dr. {patient[2]}

Please log in to Smart Hospital and download your prescription.

Thank you for choosing Smart Hospital.

Regards,
Smart Hospital Team
"""

        send_email(
            patient[1],
            subject,
            body
        )

        return redirect("/doctor/appointments")

    return render_template("add_prescription.html")
# ==========================
# Patient Prescriptions
# ==========================
@app.route("/prescriptions")
def prescriptions():

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT
            pr.prescription_id,
            d.name,
            pr.diagnosis,
            pr.medicines,
            pr.dosage,
            pr.notes,
            pr.prescription_date

        FROM prescriptions pr

        JOIN doctors d
            ON pr.doctor_id = d.doctor_id

        WHERE pr.patient_id=%s

        ORDER BY pr.prescription_date DESC
    """,
    (
        session["patient_id"],
    ))

    prescriptions = cursor.fetchall()

    return render_template(
        "patient_prescriptions.html",
        prescriptions=prescriptions
    )
# ==========================
# Manage Doctor Schedules
# ==========================
@app.route("/admin/schedules")
def admin_schedules():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cursor.execute("""
        SELECT
            ds.schedule_id,
            d.name,
            ds.available_date,
            ds.start_time,
            ds.end_time,
            ds.status
        FROM doctor_schedule ds
        JOIN doctors d
        ON ds.doctor_id = d.doctor_id
        ORDER BY ds.available_date
    """)

    schedules = cursor.fetchall()

    return render_template(
        "admin_schedules.html",
        schedules=schedules
    )

# ==========================
# Add Doctor Schedule
# ==========================
@app.route("/admin/add_schedule", methods=["GET", "POST"])
def add_schedule():

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        doctor_id = request.form["doctor_id"]
        available_date = request.form["available_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        status = request.form["status"]

        cursor.execute("""
            INSERT INTO doctor_schedule
            (
                doctor_id,
                available_date,
                start_time,
                end_time,
                status
            )
            VALUES (%s,%s,%s,%s,%s)
        """,
        (
            doctor_id,
            available_date,
            start_time,
            end_time,
            status
        ))

        db.commit()

        return redirect("/admin/schedules")

    # Load doctors for dropdown
    cursor.execute("""
        SELECT doctor_id, name
        FROM doctors
        ORDER BY name
    """)

    doctors = cursor.fetchall()

    return render_template(
        "add_schedule.html",
        doctors=doctors
    )

@app.route("/download_prescription/<int:id>")
def download_prescription(id):

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT
            p.name,
            d.name,
            pr.diagnosis,
            pr.medicines,
            pr.dosage,
            pr.notes,
            pr.prescription_date

        FROM prescriptions pr

        JOIN patients p
            ON pr.patient_id = p.patient_id

        JOIN doctors d
            ON pr.doctor_id = d.doctor_id

        WHERE pr.prescription_id=%s
        AND pr.patient_id=%s
    """,
    (
        id,
        session["patient_id"]
    ))

    prescription = cursor.fetchone()

    if prescription is None:
        return "Prescription not found"

    filename = f"prescription_{id}.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>SMART HOSPITAL</b>", styles["Title"]))
    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(Paragraph(f"<b>Patient:</b> {prescription[0]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Doctor:</b> {prescription[1]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Diagnosis:</b> {prescription[2]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Medicines:</b> {prescription[3]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Dosage:</b> {prescription[4]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Notes:</b> {prescription[5]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {prescription[6]}", styles["Normal"]))
    story.append(Paragraph("<br/><br/>Doctor Signature: ____________________", styles["Normal"]))

    doc.build(story)

    return send_file(filename, as_attachment=True)

@app.route("/profile")
def profile():

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT
            patient_id,
            name,
            gender,
            age,
            phone,
            email,
            address
        FROM patients
        WHERE patient_id=%s
    """, (session["patient_id"],))

    patient = cursor.fetchone()

    return render_template(
        "profile.html",
        patient=patient
    )

@app.route("/notifications")
def notifications():

    if "patient_id" not in session:
        return redirect("/login")

    # Mark all as read
    cursor.execute("""
        UPDATE notifications
        SET status='Read'
        WHERE patient_id=%s
    """, (session["patient_id"],))

    db.commit()

    cursor.execute("""
        SELECT
            notification_id,
            message,
            status,
            created_at
        FROM notifications
        WHERE patient_id=%s
        ORDER BY created_at DESC
    """, (session["patient_id"],))

    notifications = cursor.fetchall()

    return render_template(
        "patient_notifications.html",
        notifications=notifications
    )

@app.route("/appointment_receipt/<int:appointment_id>")
def appointment_receipt(appointment_id):

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            d.name,
            a.appointment_date,
            a.appointment_time,
            a.status
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        WHERE a.appointment_id=%s
    """, (appointment_id,))

    appointment = cursor.fetchone()

    return render_template(
        "appointment_receipt.html",
        appointment=appointment
    )

@app.route("/appointment/pdf/<int:id>")
def appointment_pdf(id):

    if "patient_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            d.name,
            a.appointment_date,
            a.appointment_time,
            a.status
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        WHERE a.appointment_id=%s
    """, (id,))

    appointment = cursor.fetchone()

    if appointment is None:
        return "Appointment not found"

    pdf_path = os.path.join("static", f"appointment_{id}.pdf")

    doc = SimpleDocTemplate(pdf_path)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph("<b>Smart Hospital Appointment Receipt</b>", styles["Title"])
    )

    elements.append(Paragraph("<br/>", styles["Normal"]))

    data = [
        ["Appointment ID", appointment[0]],
        ["Patient", appointment[1]],
        ["Doctor", appointment[2]],
        ["Date", str(appointment[3])],
        ["Time", str(appointment[4])],
        ["Status", appointment[5]]
    ]

    table = Table(data, colWidths=[2.5*inch, 3*inch])

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.lightblue),
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("BOTTOMPADDING",(0,0),(-1,-1),8)
    ]))

    elements.append(table)

    qr_path = os.path.join(
        "static",
        "qr_codes",
        f"{id}.png"
    )

    if os.path.exists(qr_path):

        from reportlab.platypus import Image

        elements.append(Paragraph("<br/><b>Appointment QR Code</b><br/>", styles["Heading2"]))

        elements.append(
            Image(qr_path, width=2*inch, height=2*inch)
        )

    doc.build(elements)

    return send_file(
        pdf_path,
        as_attachment=True
    )

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)