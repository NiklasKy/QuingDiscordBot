# PowerShell-Skript zum Beheben der MySQL-Berechtigungen

# Stoppe und entferne den bestehenden MySQL-Container
Write-Host "Stoppe und entferne bestehende Container..." -ForegroundColor Yellow
docker-compose down

# Lösche das MySQL-Volume, um von vorne zu beginnen
Write-Host "Lösche MySQL-Volume..." -ForegroundColor Yellow
docker volume rm minecraft-mysql-data

# Erstelle und starte den MySQL-Container neu
Write-Host "Starte Container neu..." -ForegroundColor Yellow
docker-compose up -d

# Warte auf MySQL
Write-Host "Warte auf MySQL-Start (30 Sekunden)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Verbindungsdetails für die Anwendung anzeigen
Write-Host "MySQL-Verbindungsdetails für deine Anwendung:" -ForegroundColor Green
Write-Host "Host: minecraft-mysql (innerhalb von Docker) oder localhost/127.0.0.1 (extern)" -ForegroundColor Green
Write-Host "Port: 3306" -ForegroundColor Green
Write-Host "Datenbank: minecraft" -ForegroundColor Green
Write-Host "Benutzer: minecraft" -ForegroundColor Green
Write-Host "Passwort: $env:MINECRAFT_MYSQL_PASSWORD" -ForegroundColor Green

Write-Host "MySQL-Setup abgeschlossen." -ForegroundColor Green 