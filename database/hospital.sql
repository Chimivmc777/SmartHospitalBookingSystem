CREATE DATABASE smart_hospital;

USE smart_hospital;

CREATE TABLE departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    description VARCHAR(255)
);

INSERT INTO departments (department_name, description)
VALUES
('General Medicine', 'General health consultation'),
('Cardiology', 'Heart and blood vessel treatment'),
('Orthopedics', 'Bone and joint treatment'),
('Pediatrics', 'Children healthcare'),
('Dermatology', 'Skin treatment'),
('Neurology', 'Brain and nervous system'),
('Gynecology', 'Women healthcare');