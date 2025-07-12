CREATE USER nextcloud_user WITH PASSWORD 'nextcloud_password';
CREATE DATABASE nextcloud;
GRANT ALL PRIVILEGES ON DATABASE nextcloud TO nextcloud_user;