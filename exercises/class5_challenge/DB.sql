CREATE TABLE M_UNIT (
    unit_id     INT PRIMARY KEY,
    unit_name   VARCHAR(100) NOT NULL,
    location    VARCHAR(150)
);
 
CREATE TABLE UNIT (
    sub_unit_id   INT PRIMARY KEY,
    unit_id_fk    INT NOT NULL REFERENCES M_UNIT(unit_id),
    sub_unit_name VARCHAR(100) NOT NULL,
    type          VARCHAR(50)
);
 
CREATE TABLE ROOMS (
    room_id           INT PRIMARY KEY,
    sub_unit_id_fk    INT NOT NULL REFERENCES UNIT(sub_unit_id),
    room_number       VARCHAR(20) NOT NULL,
    capacity          INT
);
 
CREATE TABLE PATIENT (
    patient_id  INT PRIMARY KEY,
    mrn         VARCHAR(30) UNIQUE NOT NULL,
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    dob         DATE
);
 
CREATE TABLE CASES (
    case_id            INT PRIMARY KEY,
    patient_id_fk      INT NOT NULL REFERENCES PATIENT(patient_id),
    primary_diagnosis  VARCHAR(200),
    admit_date         DATE
);
 
CREATE TABLE FINANCE (
    transaction_id  INT PRIMARY KEY,
    case_id_fk      INT NOT NULL UNIQUE REFERENCES CASES(case_id),  
    amount          NUMERIC(10,2),
    date            DATE,
    status          VARCHAR(30)
);
 
CREATE TABLE REPORTS (
    report_id           INT PRIMARY KEY,
    transaction_id_fk   INT NOT NULL REFERENCES FINANCE(transaction_id),
    report_type         VARCHAR(50),
    text_data           TEXT
);
 
CREATE TABLE INSURANCE (
    insurance_id        INT PRIMARY KEY,
    transaction_id_fk   INT NOT NULL REFERENCES FINANCE(transaction_id),
    provider            VARCHAR(100),
    policy_number       VARCHAR(50)
);
 
CREATE TABLE EPISODE (
    episode_id    INT PRIMARY KEY,
    case_id_fk    INT NOT NULL REFERENCES CASES(case_id),
    type          VARCHAR(50),
    date          DATE,
    notes         TEXT
);
 
CREATE TABLE STAFF (
    staff_id    INT PRIMARY KEY,
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    role        VARCHAR(50)
);
 
CREATE TABLE SHIFT (
    shift_id       INT PRIMARY KEY,
    staff_id_fk    INT NOT NULL REFERENCES STAFF(staff_id),
    start_time     TIME,
    end_time       TIME,
    role_in_shift  VARCHAR(50)
);

CREATE TABLE STAFF_EPISODE (
    staff_episode_id  INT PRIMARY KEY,
    staff_id_fk       INT NOT NULL REFERENCES STAFF(staff_id),
    episode_id_fk     INT NOT NULL REFERENCES EPISODE(episode_id),
    UNIQUE (staff_id_fk, episode_id_fk) 
);
 