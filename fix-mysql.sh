#!/bin/bash

# Ein Skript, um das MySQL-Berechtigungsproblem zu beheben

# 1. Befehl zum manuellen Hinzufügen der Berechtigungen für alle Hosts
docker exec -it minecraft-mysql mysql -uroot -p"${MINECRAFT_MYSQL_ROOT_PASSWORD}" -e "
CREATE USER IF NOT EXISTS 'minecraft'@'%' IDENTIFIED BY '${MINECRAFT_MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'%';

CREATE USER IF NOT EXISTS 'minecraft'@'172.19.0.1' IDENTIFIED BY '${MINECRAFT_MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'172.19.0.1' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'172.19.0.1';

FLUSH PRIVILEGES;
"

echo "MySQL-Berechtigungen wurden aktualisiert." 