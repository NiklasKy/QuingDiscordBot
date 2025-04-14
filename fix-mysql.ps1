# PowerShell-Skript zum Beheben der MySQL-Berechtigungen

# Die Passwörter werden aus Umgebungsvariablen gelesen
$rootPassword = $env:MINECRAFT_MYSQL_ROOT_PASSWORD
$mysqlPassword = $env:MINECRAFT_MYSQL_PASSWORD

Write-Host "MySQL-Berechtigungen werden aktualisiert..."

# SQL-Befehle direkt als Argument übergeben
$sqlCommands = @"
CREATE USER IF NOT EXISTS 'minecraft'@'%' IDENTIFIED BY '$mysqlPassword';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'%';

CREATE USER IF NOT EXISTS 'minecraft'@'172.19.0.1' IDENTIFIED BY '$mysqlPassword';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'172.19.0.1' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'172.19.0.1';

FLUSH PRIVILEGES;
"@

# SQL-Befehle über docker exec ausführen
docker exec -i minecraft-mysql mysql -uroot -p"$rootPassword" -e "$sqlCommands"

Write-Host "MySQL-Berechtigungen wurden aktualisiert." 