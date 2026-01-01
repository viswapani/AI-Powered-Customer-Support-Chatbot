-- Create MedEquip database
CREATE DATABASE IF NOT EXISTS medequip
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create application user (local only)
CREATE USER IF NOT EXISTS 'medequip_user'@'localhost'
    IDENTIFIED BY 'medequip123';

-- Grant privileges on the medequip database
GRANT ALL PRIVILEGES ON medequip.* TO 'medequip_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;