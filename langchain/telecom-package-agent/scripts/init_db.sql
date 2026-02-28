-- 在 MySQL 中执行以下命令创建数据库并授权
-- 需要以 root 或有权限的用户执行
-- 请将 your_user 替换为实际使用的 MySQL 用户名

CREATE DATABASE IF NOT EXISTS telecom_package_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON telecom_package_agent.* TO 'your_user'@'%';
FLUSH PRIVILEGES;
