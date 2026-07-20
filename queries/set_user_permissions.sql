-- 1) Create the schema if missing
CREATE DATABASE IF NOT EXISTS File_Deduplification
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2) (Re)create user on ALL likely hosts
-- DROP USER IF EXISTS 'jarheads_0231'@'%';
-- DROP USER IF EXISTS 'jarheads_0231'@'localhost';
-- DROP USER IF EXISTS 'jarheads_0231'@'127.0.0.1';

-- IMPORTANT: use the **plaintext** password here (not URL-encoded)
-- CREATE USER 'jarheads_0231'@'%'          IDENTIFIED BY '<YOUR_PASSWORD_HERE>';
-- CREATE USER 'jarheads_0231'@'localhost'  IDENTIFIED BY '<YOUR_PASSWORD_HERE>';
-- CREATE USER 'jarheads_0231'@'127.0.0.1'  IDENTIFIED BY '<YOUR_PASSWORD_HERE>';

-- 3) Grant schema privileges on each host row
GRANT ALL PRIVILEGES ON File_Deduplification.* TO 'jarheads_0231'@'%';
GRANT ALL PRIVILEGES ON File_Deduplification.* TO 'jarheads_0231'@'localhost';
GRANT ALL PRIVILEGES ON File_Deduplification.* TO 'jarheads_0231'@'127.0.0.1';

FLUSH PRIVILEGES;

-- 4) Sanity check
SHOW GRANTS FOR 'jarheads_0231'@'%';
SHOW GRANTS FOR 'jarheads_0231'@'localhost';
SHOW GRANTS FOR 'jarheads_0231'@'127.0.0.1';
