from werkzeug.security import generate_password_hash

print(generate_password_hash("Chimivmc777@"))

print("Admin Password:")
print(generate_password_hash("admin123"))

print("\nDoctor Password:")
print(generate_password_hash("doctor123"))

print("\nPatient Password:")
print(generate_password_hash("123456"))