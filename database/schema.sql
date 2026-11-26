CREATE DATABASE IF NOT EXISTS foodbridge;
USE foodbridge;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    role ENUM('admin','donor','ngo') NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ngos (
    ngo_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    ngo_name VARCHAR(150) NOT NULL,
    ngo_type VARCHAR(100),
    people_served INT DEFAULT 0,
    storage_capacity INT DEFAULT 0,
    location VARCHAR(255),
    food_preferences VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    organization_name VARCHAR(150),
    location VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE food_listings (
    food_id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT,
    food_name VARCHAR(150) NOT NULL,
    food_category VARCHAR(100),
    quantity INT NOT NULL,
    prepared_at DATETIME,
    expiry_time DATETIME,
    pickup_location VARCHAR(255),
    status ENUM('Available','Reserved','Distributed','Expired')
        DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES donors(donor_id)
);

CREATE TABLE ngo_demand (
    demand_id INT AUTO_INCREMENT PRIMARY KEY,
    ngo_id INT,
    demand_date DATE NOT NULL,
    food_category VARCHAR(100),
    required_quantity INT,
    current_stock INT DEFAULT 0,
    donations_received INT DEFAULT 0,
    people_served INT,
    FOREIGN KEY (ngo_id) REFERENCES ngos(ngo_id)
);

CREATE TABLE food_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    ngo_id INT,
    food_id INT,
    requested_quantity INT,
    request_status ENUM('Pending','Approved','Rejected','Completed')
        DEFAULT 'Pending',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ngo_id) REFERENCES ngos(ngo_id),
    FOREIGN KEY (food_id) REFERENCES food_listings(food_id)
);

CREATE TABLE allocations (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    food_id INT,
    ngo_id INT,
    allocated_quantity INT,
    predicted_demand INT,
    priority_score FLOAT,
    allocation_status ENUM(
        'Recommended','Approved','Picked Up','Delivered','Cancelled'
    ) DEFAULT 'Recommended',
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_id) REFERENCES food_listings(food_id),
    FOREIGN KEY (ngo_id) REFERENCES ngos(ngo_id)
);

CREATE TABLE feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT,
    quantity_received INT,
    quantity_consumed INT,
    quantity_wasted INT,
    satisfaction_rating INT,
    feedback_text TEXT,
    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (allocation_id) REFERENCES allocations(allocation_id)
);