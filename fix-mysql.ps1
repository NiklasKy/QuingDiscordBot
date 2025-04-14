# PowerShell-Skript zur Behebung des MySQL-Berechtigungsproblems

# Umgebungsvariablen aus .env-Datei laden
$envContent = Get-Content -Path ".env" -ErrorAction SilentlyContinue
foreach ($line in $envContent) {
    if ($line -match "^([^=]+)=(.*)$") {
        $name = $matches[1]
        $value = $matches[2]
        if ($name -eq "MINECRAFT_MYSQL_ROOT_PASSWORD" -or $name -eq "MINECRAFT_MYSQL_PASSWORD") {
            # Entferne Anführungszeichen, falls vorhanden
            $value = $value.Trim('"''')
            Write-Host "Setze $name"
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$rootPassword = $env:MINECRAFT_MYSQL_ROOT_PASSWORD
$userPassword = $env:MINECRAFT_MYSQL_PASSWORD

Write-Host "Behebe MySQL-Berechtigungsproblem..."

# SQL-Befehle zusammenstellen
$sqlCommands = @"
CREATE USER IF NOT EXISTS 'minecraft'@'%' IDENTIFIED BY '$userPassword';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'%';

CREATE USER IF NOT EXISTS 'minecraft'@'172.19.0.1' IDENTIFIED BY '$userPassword';
GRANT ALL PRIVILEGES ON *.* TO 'minecraft'@'172.19.0.1' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON minecraft.* TO 'minecraft'@'172.19.0.1';

FLUSH PRIVILEGES;
"@

# SQL-Befehle in eine temporäre Datei schreiben
$tempSqlFile = "temp_mysql_commands.sql"
$sqlCommands | Out-File -FilePath $tempSqlFile -Encoding utf8

# SQL-Befehle ausführen
docker exec -i minecraft-mysql mysql -uroot -p"$rootPassword" < $tempSqlFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "MySQL-Berechtigungen wurden erfolgreich aktualisiert." -ForegroundColor Green
} else {
    Write-Host "Fehler beim Aktualisieren der MySQL-Berechtigungen." -ForegroundColor Red
}

# Temporäre Datei löschen
Remove-Item -Path $tempSqlFile -Force 