CREATE DATABASE IF NOT EXISTS community_hospital_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE community_hospital_db;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Visits;
DROP TABLE IF EXISTS Appointments;
DROP TABLE IF EXISTS Schedules;
DROP TABLE IF EXISTS Staff;
DROP TABLE IF EXISTS Rooms;
DROP TABLE IF EXISTS Departments;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE Departments (
    dept_id INT PRIMARY KEY AUTO_INCREMENT,
    dept_name VARCHAR(50) NOT NULL UNIQUE,
    location VARCHAR(100) COMMENT '科室楼层/位置'
) ENGINE=InnoDB;

CREATE TABLE Rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_no VARCHAR(20) NOT NULL UNIQUE,
    dept_id INT NOT NULL,
    room_type ENUM('General', 'Special', 'Consultation') DEFAULT 'General',
    status ENUM('Available', 'Occupied', 'Maintenance') DEFAULT 'Available',
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
) ENGINE=InnoDB;

CREATE TABLE Staff (
    staff_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    role ENUM('Doctor', 'Nurse', 'Admin', 'Cashier') NOT NULL,
    dept_id INT,
    title VARCHAR(50) COMMENT '职称: 如主任医师',
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE COMMENT '1为在职, 0为离职',
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
) ENGINE=InnoDB;

CREATE TABLE Schedules (
    schedule_id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    room_no VARCHAR(20) NOT NULL,
    shift_date DATE NOT NULL,
    shift_time ENUM('Morning', 'Afternoon') NOT NULL,
    UNIQUE KEY unique_doctor_shift (doctor_id, shift_date, shift_time),
    UNIQUE KEY unique_room_shift (room_no, shift_date, shift_time),
    FOREIGN KEY (doctor_id) REFERENCES Staff(staff_id),
    FOREIGN KEY (room_no) REFERENCES Rooms(room_no)
) ENGINE=InnoDB;

CREATE TABLE Appointments (
    appt_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_name VARCHAR(50) NOT NULL,
    id_card VARCHAR(18) NOT NULL, 
    phone VARCHAR(20) NOT NULL,
    dept_id INT NOT NULL,
    appt_date DATE NOT NULL,
    expected_arrival_time TIME,
    status ENUM('Pending', 'Completed', 'Cancelled') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id),
    INDEX idx_id_card (id_card) 
) ENGINE=InnoDB;

CREATE TABLE Visits (
    visit_id INT PRIMARY KEY AUTO_INCREMENT,
    appt_id INT NULL,                      -- 如果是预约转入，记录原ID
    patient_name VARCHAR(50) NOT NULL,
    id_card VARCHAR(18) NOT NULL,
    phone VARCHAR(20),
    gender ENUM('M', 'F') NOT NULL,
    dept_id INT NOT NULL,
    doctor_id INT NOT NULL,
    room_no VARCHAR(20) NOT NULL,
    status ENUM('Waiting', 'Consulting', 'ToPay', 'Finished') DEFAULT 'Waiting',
    total_fee DECIMAL(10, 2) DEFAULT 0.00,
    visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finish_time TIMESTAMP NULL,             -- 结算时间
    FOREIGN KEY (appt_id) REFERENCES Appointments(appt_id),
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id),
    FOREIGN KEY (doctor_id) REFERENCES Staff(staff_id)
) ENGINE=InnoDB;


-- 初始化演示数据

-- 插入科室
INSERT INTO Departments (dept_name, location) VALUES 
('内科', '门诊楼2F-A区'),
('外科', '门诊楼3F-B区'),
('儿科', '住院楼1F-C区'),
('中医科', '综合楼4F-D区');

-- 插入诊室
INSERT INTO Rooms (room_no, dept_id) VALUES 
('201', 1), ('202', 1), 
('301', 2), ('302', 2),
('101', 3), 
('401', 4);

-- 插入初始员工
INSERT INTO Staff (name, role, dept_id, title, phone, is_active) VALUES 
('张主任', 'Doctor', 1, '主任医师', '13811112222', 1),
('李医生', 'Doctor', 1, '副主任医师', '13833334444', 1),
('王外科', 'Doctor', 2, '主治医师', '13955556666', 1),
('赵儿科', 'Doctor', 3, '主任医师', '13777778888', 1);