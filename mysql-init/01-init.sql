-- Erlaube Remote-Verbindungen für den minecraft-Benutzer
CREATE USER IF NOT EXISTS 'minecraft'@'%' IDENTIFIED BY 'aD[,T)P7^*yv_1e{';
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'%';

-- Erlaube Verbindungen vom Docker-Netzwerk (172.19.0.0/16)
CREATE USER IF NOT EXISTS 'minecraft'@'172.19.0.%' IDENTIFIED BY 'aD[,T)P7^*yv_1e{';
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'172.19.0.%';

-- Erlaube Verbindungen vom Host und localhost
CREATE USER IF NOT EXISTS 'minecraft'@'172.19.0.1' IDENTIFIED BY 'aD[,T)P7^*yv_1e{';
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'172.19.0.1';

-- Aktualisiere die Root-Benutzerberechtigungen
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

-- Aktualisiere Berechtigungen
FLUSH PRIVILEGES; 