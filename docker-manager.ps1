# PowerShell-Skript für Docker-Management
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$Action
)

# Grundlegende Konfiguration
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Lade .env Datei
$envPath = Join-Path $PSScriptRoot ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "Warnung: .env Datei nicht gefunden!" -ForegroundColor Yellow
}

# Konfiguration
$backupPath = "C:\Backups\Docker"
$shutdownBackupPath = Join-Path $backupPath "Shutdown"
$date = Get-Date -Format "yyyy-MM-dd_HH-mm"

# Stelle sicher, dass wir im richtigen Verzeichnis sind
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir = Split-Path -Parent $scriptPath
Set-Location -Path $scriptDir

# Funktion zum Erstellen von Verzeichnissen
function Initialize-Directories {
    New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
    New-Item -ItemType Directory -Force -Path $shutdownBackupPath | Out-Null
}

# Funktion für PostgreSQL Backup
function Backup-Postgres {
    param (
        [string]$ContainerName,
        [string]$DbName,
        [string]$User,
        [string]$Password,
        [string]$BackupType = "regular"
    )
    
    $targetPath = if ($BackupType -eq "shutdown") { $shutdownBackupPath } else { $backupPath }
    Write-Host "Backup von $DbName..." -ForegroundColor Yellow
    $backupFile = Join-Path $targetPath "$DbName-$date.sql"
    
    # Entferne Anführungszeichen aus dem Passwort für die Kommandozeile
    $dbPassword = $Password -replace '"', ''
    
    docker exec $ContainerName pg_dump -U $User -d $DbName > $backupFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Backup erfolgreich: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "Fehler beim Backup von $DbName" -ForegroundColor Red
    }
}

# Funktion für Redis Backup
function Backup-Redis {
    param (
        [string]$BackupType = "regular"
    )
    
    $targetPath = if ($BackupType -eq "shutdown") { $shutdownBackupPath } else { $backupPath }
    Write-Host "Backup von Redis..." -ForegroundColor Yellow
    $backupFile = Join-Path $targetPath "redis-$date.rdb"
    
    docker exec minecraft-redis redis-cli SAVE
    docker cp minecraft-redis:/data/dump.rdb $backupFile
    
    if (Test-Path $backupFile) {
        Write-Host "Backup erfolgreich: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "Fehler beim Redis Backup" -ForegroundColor Red
    }
}

# Funktion für Bot-Konfiguration Backup
function Backup-BotConfig {
    param (
        [string]$BackupType = "regular"
    )
    
    $targetPath = if ($BackupType -eq "shutdown") { $shutdownBackupPath } else { $backupPath }
    Write-Host "Backup von QuingCraft Bot Konfiguration..." -ForegroundColor Yellow
    $backupFile = Join-Path $targetPath "quingcraft-bot-$date.env"
    
    docker cp quingcraft-bot:/app/.env $backupFile
    
    if (Test-Path $backupFile) {
        Write-Host "Backup erfolgreich: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "Fehler beim Backup der Bot-Konfiguration" -ForegroundColor Red
    }
}

# Funktion für MySQL Backup
function Backup-MySQL {
    param (
        [string]$BackupType = "regular"
    )
    
    $targetPath = if ($BackupType -eq "shutdown") { $shutdownBackupPath } else { $backupPath }
    Write-Host "Backup von MySQL..." -ForegroundColor Yellow
    $backupFile = Join-Path $targetPath "minecraft-mysql-$date.sql"
    
    # Entferne Anführungszeichen aus dem Passwort für die Kommandozeile
    $mysqlPassword = $env:MINECRAFT_MYSQL_ROOT_PASSWORD -replace '"', ''
    
    docker exec minecraft-mysql mysqldump -u root -p"$mysqlPassword" --all-databases > $backupFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Backup erfolgreich: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "Fehler beim MySQL Backup" -ForegroundColor Red
    }
}

# Funktion zum Wiederherstellen einer PostgreSQL-Datenbank
function Restore-Postgres {
    param (
        [string]$ContainerName,
        [string]$DbName,
        [string]$User,
        [string]$Password
    )
    
    $latestBackup = Get-ChildItem -Path $shutdownBackupPath -Filter "$DbName-*.sql" | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1
    
    if ($latestBackup) {
        Write-Host "Wiederherstelle $DbName aus $($latestBackup.Name)..." -ForegroundColor Yellow
        
        # Konvertiere Container-Namen zu Service-Namen für docker-compose
        $serviceName = switch ($ContainerName) {
            "luckperms-postgres" { "luckperms-db" }
            "husksync-postgres" { "husksync-db" }
            "quingcraft-postgres" { "quingcraft-db" }
            default { $ContainerName }
        }
        
        docker-compose up -d $serviceName
        Start-Sleep -Seconds 10
        
        # Entferne Anführungszeichen aus dem Passwort für die Kommandozeile
        $dbPassword = $Password -replace '"', ''
        
        Get-Content $latestBackup.FullName | docker exec -i $ContainerName psql -U $User -d $DbName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Wiederherstellung erfolgreich!" -ForegroundColor Green
        } else {
            Write-Host "Fehler bei der Wiederherstellung!" -ForegroundColor Red
        }
    } else {
        Write-Host "Kein Backup für $DbName gefunden. Starte mit leerer Datenbank." -ForegroundColor Yellow
        
        # Konvertiere Container-Namen zu Service-Namen für docker-compose
        $serviceName = switch ($ContainerName) {
            "luckperms-postgres" { "luckperms-db" }
            "husksync-postgres" { "husksync-db" }
            "quingcraft-postgres" { "quingcraft-db" }
            default { $ContainerName }
        }
        docker-compose up -d $serviceName
    }
}

# Funktion zum Wiederherstellen von Redis
function Restore-Redis {
    $latestBackup = Get-ChildItem -Path $shutdownBackupPath -Filter "redis-*.rdb" | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1
    
    if ($latestBackup) {
        Write-Host "Wiederherstelle Redis aus $($latestBackup.Name)..." -ForegroundColor Yellow
        docker-compose up -d redis
        Start-Sleep -Seconds 5
        docker cp $latestBackup.FullName minecraft-redis:/data/dump.rdb
        docker-compose restart redis
        Write-Host "Redis Wiederherstellung erfolgreich!" -ForegroundColor Green
    } else {
        Write-Host "Kein Redis Backup gefunden. Starte mit leerer Datenbank." -ForegroundColor Yellow
        docker-compose up -d redis
    }
}

# Funktion zum Wiederherstellen der Bot-Konfiguration
function Restore-BotConfig {
    $latestBackup = Get-ChildItem -Path $shutdownBackupPath -Filter "quingcraft-bot-*.env" | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1
    
    if ($latestBackup) {
        Write-Host "Wiederherstelle Bot-Konfiguration aus $($latestBackup.Name)..." -ForegroundColor Yellow
        docker-compose up -d quingcraft-bot
        Start-Sleep -Seconds 5
        docker cp $latestBackup.FullName quingcraft-bot:/app/.env
        docker-compose restart quingcraft-bot
        Write-Host "Bot-Konfiguration Wiederherstellung erfolgreich!" -ForegroundColor Green
    } else {
        Write-Host "Kein Bot-Konfigurations-Backup gefunden. Starte mit Standard-Konfiguration." -ForegroundColor Yellow
        docker-compose up -d quingcraft-bot
    }
}

# Funktion zum Wiederherstellen von MySQL
function Restore-MySQL {
    $latestBackup = Get-ChildItem -Path $shutdownBackupPath -Filter "minecraft-mysql-*.sql" | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1
    
    if ($latestBackup) {
        Write-Host "Wiederherstelle MySQL aus $($latestBackup.Name)..." -ForegroundColor Yellow
        docker-compose up -d minecraft-mysql
        Start-Sleep -Seconds 10
        
        # Entferne Anführungszeichen aus dem Passwort für die Kommandozeile
        $mysqlPassword = $env:MINECRAFT_MYSQL_ROOT_PASSWORD -replace '"', ''
        
        Get-Content $latestBackup.FullName | docker exec -i minecraft-mysql mysql -u root -p"$mysqlPassword"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "MySQL Wiederherstellung erfolgreich!" -ForegroundColor Green
        } else {
            Write-Host "Fehler bei der MySQL Wiederherstellung!" -ForegroundColor Red
        }
    } else {
        Write-Host "Kein MySQL Backup gefunden. Starte mit leerer Datenbank." -ForegroundColor Yellow
        docker-compose up -d minecraft-mysql
    }
}

# Funktion zum Erstellen von geplanten Aufgaben
function Create-ScheduledTask {
    param (
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$TriggerType,
        [string]$ActionType
    )
    
    try {
        $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Action $ActionType"
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
        
        # Verschiedene Trigger-Typen
        $trigger = switch ($TriggerType) {
            "startup" { 
                New-ScheduledTaskTrigger -AtStartup 
            }
            "shutdown" { 
                # Erstelle einen EventTrigger für Systemshutdown
                $CIMTriggerClass = Get-CimClass -ClassName MSFT_TaskEventTrigger -Namespace Root/Microsoft/Windows/TaskScheduler
                $trigger = New-CimInstance -CimClass $CIMTriggerClass -ClientOnly
                $trigger.Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">*[System[Provider[@Name=''User32''] and EventID=1074]]</Select></Query></QueryList>'
                $trigger.Enabled = $true
                $trigger
            }
            "daily" { 
                New-ScheduledTaskTrigger -Daily -At 3AM 
            }
            default { 
                New-ScheduledTaskTrigger -Daily -At 3AM 
            }
        }
        
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
        Write-Host "Aufgabe '$TaskName' wurde erfolgreich erstellt!" -ForegroundColor Green
    } catch {
        Write-Host "Fehler beim Erstellen der Aufgabe: $_" -ForegroundColor Red
    }
}

# Funktion zum Ausführen von Backups
function Invoke-Backup {
    param (
        [string]$BackupType = "regular"
    )
    
    Initialize-Directories
    Backup-Postgres -ContainerName "luckperms-postgres" -DbName "luckperms" -User "luckperms" -Password $env:LUCKPERMS_DB_PASSWORD -BackupType $BackupType
    Backup-Postgres -ContainerName "husksync-postgres" -DbName "husksync" -User "husksync" -Password $env:HUSKSYNC_DB_PASSWORD -BackupType $BackupType
    Backup-Postgres -ContainerName "quingcraft-postgres" -DbName "quingcraft" -User "quingcraft" -Password $env:QUINGCRAFT_DB_PASSWORD -BackupType $BackupType
    Backup-Redis -BackupType $BackupType
    Backup-BotConfig -BackupType $BackupType
    Backup-MySQL -BackupType $BackupType
}

# Funktion zum Starten mit Backup-Wiederherstellung
function Start-WithBackup {
    Initialize-Directories
    Restore-Postgres -ContainerName "luckperms-postgres" -DbName "luckperms" -User "luckperms" -Password $env:LUCKPERMS_DB_PASSWORD
    Restore-Postgres -ContainerName "husksync-postgres" -DbName "husksync" -User "husksync" -Password $env:HUSKSYNC_DB_PASSWORD
    Restore-Postgres -ContainerName "quingcraft-postgres" -DbName "quingcraft" -User "quingcraft" -Password $env:QUINGCRAFT_DB_PASSWORD
    Restore-Redis
    Restore-BotConfig
    Restore-MySQL
}

# Funktion zum Erstellen aller geplanten Aufgaben
function Create-AllTasks {
    $scriptPath = Join-Path $PSScriptRoot "docker-manager.ps1"
    
    # Tägliches Backup um 3 Uhr morgens
    Create-ScheduledTask -TaskName "Minecraft-Docker-Backup" -ScriptPath $scriptPath -TriggerType "daily" -ActionType "backup"
    
    # Backup beim System-Shutdown
    Create-ScheduledTask -TaskName "Minecraft-Docker-Shutdown-Backup" -ScriptPath $scriptPath -TriggerType "shutdown" -ActionType "shutdown-backup"
    
    # Wiederherstellung beim System-Start
    Create-ScheduledTask -TaskName "Minecraft-Docker-Startup-Backup" -ScriptPath $scriptPath -TriggerType "startup" -ActionType "startup-restore"
}

# Funktion zum Warten auf Docker
function Wait-ForDocker {
    $dockerPs = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) { return $true }
    
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { return $true }
    
    return $false
}

# Funktion zum Laden eines bestimmten Backups
function Restore-SpecificBackup {
    param (
        [string]$ContainerName,
        [string]$DbName,
        [string]$User,
        [string]$Password,
        [string]$BackupFile,
        [switch]$DropDatabase = $false
    )
    
    if (-not (Test-Path $BackupFile)) {
        Write-Host "Die angegebene Backup-Datei '$BackupFile' existiert nicht." -ForegroundColor Red
        return $false
    }
    
    Write-Host "Bereite Wiederherstellung von $DbName aus $BackupFile vor..." -ForegroundColor Yellow
    
    # Konvertiere Container-Namen zu Service-Namen für docker-compose
    $serviceName = switch ($ContainerName) {
        "luckperms-postgres" { "luckperms-db" }
        "husksync-postgres" { "husksync-db" }
        "quingcraft-postgres" { "quingcraft-db" }
        "minecraft-mysql" { "minecraft-mysql" }
        default { $ContainerName }
    }
    
    # Prüfe, ob der Container bereits läuft
    $containerRunning = docker ps --format "{{.Names}}" | Select-String -Pattern $ContainerName
    
    if (-not $containerRunning) {
        Write-Host "Starte $ContainerName..." -ForegroundColor Yellow
        docker-compose up -d $serviceName
        Start-Sleep -Seconds 10
    }
    
    # Wenn angefordert, lösche und erstelle die Datenbank neu
    if ($DropDatabase) {
        Write-Host "Lösche bestehende Datenbank $DbName..." -ForegroundColor Yellow
        
        # Verbindungen trennen und Datenbank löschen
        $dropSql = @"
-- Trenne alle Verbindungen zur Datenbank
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DbName'
AND pid <> pg_backend_pid();

-- Lösche die Datenbank
DROP DATABASE IF EXISTS $DbName;

-- Erstelle die Datenbank neu
CREATE DATABASE $DbName OWNER $User;
"@
        
        # SQL über temporäre Datei ausführen
        $dropSqlFile = "drop_temp.sql"
        $dropSql | Out-File -FilePath $dropSqlFile -Encoding utf8
        
        # Führe SQL aus im postgres-System (nicht die zu löschende Datenbank)
        Get-Content $dropSqlFile | docker exec -i $ContainerName psql -U $User -d postgres
        Remove-Item -Path $dropSqlFile -Force
        
        Write-Host "Datenbank $DbName neu erstellt." -ForegroundColor Green
    } else {
        # Alternativ nur die Tabellen leeren
        Write-Host "Leere bestehende Tabellen in $DbName..." -ForegroundColor Yellow
        
        # Erhalte alle Tabellennamen und lösche die Daten
        $truncateSql = @"
DO \$\$
DECLARE
    tabname text;
BEGIN
    FOR tabname IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
    LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(tabname) || ' CASCADE';
    END LOOP;
END \$\$;
"@
        
        # SQL über temporäre Datei ausführen
        $truncateSqlFile = "truncate_temp.sql"
        $truncateSql | Out-File -FilePath $truncateSqlFile -Encoding utf8
        
        # Lösche Daten aus allen Tabellen
        Get-Content $truncateSqlFile | docker exec -i $ContainerName psql -U $User -d $DbName
        Remove-Item -Path $truncateSqlFile -Force
        
        Write-Host "Tabellen in $DbName geleert." -ForegroundColor Green
    }
    
    # Führe die Wiederherstellung durch
    Write-Host "Stelle $DbName aus Backup wieder her..." -ForegroundColor Yellow
    Get-Content $BackupFile | docker exec -i $ContainerName psql -U $User -d $DbName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Wiederherstellung erfolgreich!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Fehler bei der Wiederherstellung!" -ForegroundColor Red
        return $false
    }
}

# Funktion zum manuellen Wiederherstellen eines LuckPerms-Backups
function Restore-LuckPermsBackup {
    param (
        [Parameter(Mandatory=$true)]
        [string]$BackupFile,
        [switch]$DropDatabase = $false
    )
    
    # Lade Umgebungsvariablen
    if (-not $env:LUCKPERMS_DB_PASSWORD) {
        Write-Host "Lade Umgebungsvariablen aus .env Datei..." -ForegroundColor Yellow
        $envPath = Join-Path $PSScriptRoot ".env"
        if (Test-Path $envPath) {
            Get-Content $envPath | ForEach-Object {
                if ($_ -match '^([^=]+)=(.*)$') {
                    $name = $matches[1]
                    $value = $matches[2]
                    # Entferne Anführungszeichen, falls vorhanden
                    $value = $value.Trim('"''')
                    [Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
    }
    
    # Rufe die Funktion zum Wiederherstellen auf
    Restore-SpecificBackup -ContainerName "luckperms-postgres" -DbName "luckperms" -User "luckperms" -Password $env:LUCKPERMS_DB_PASSWORD -BackupFile $BackupFile -DropDatabase:$DropDatabase
}

# Hauptmenü
function Show-Menu {
    Clear-Host
    Write-Host "Docker Manager für Minecraft Server" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    Write-Host "1. Backup erstellen"
    Write-Host "2. Container mit Backup-Wiederherstellung starten"
    Write-Host "3. Alle geplanten Aufgaben erstellen"
    Write-Host "4. LuckPerms-Backup wiederherstellen"
    Write-Host "5. Beenden"
    Write-Host "`nBitte wähle eine Option (1-5): " -NoNewline -ForegroundColor Yellow
}

# Funktion zum Anzeigen des Backup-Verzeichnisses
function Show-BackupFiles {
    param (
        [string]$Pattern = "*"
    )
    
    $files = Get-ChildItem -Path $backupPath -Filter $Pattern | 
             Sort-Object LastWriteTime -Descending
    
    if ($files.Count -eq 0) {
        Write-Host "Keine Backup-Dateien gefunden." -ForegroundColor Yellow
        return $null
    }
    
    Write-Host "Verfügbare Backup-Dateien:" -ForegroundColor Cyan
    for ($i = 0; $i -lt [Math]::Min($files.Count, 10); $i++) {
        Write-Host "$($i+1). $($files[$i].Name) ($(Get-Date $files[$i].LastWriteTime -Format 'yyyy-MM-dd HH:mm:ss'))"
    }
    
    return $files
}

# Hauptprogramm
if (-not (Wait-ForDocker)) {
    Write-Host "Docker ist nicht verfügbar. Bitte starte Docker Desktop manuell." -ForegroundColor Red
    exit 1
}

if ($Action) {
    switch ($Action) {
        "backup" { Invoke-Backup }
        "shutdown-backup" { Invoke-Backup -BackupType "shutdown" }
        "startup-restore" { Start-WithBackup }
        "create-tasks" { Create-AllTasks }
        "restore-luckperms" { 
            # Zeige verfügbare Backups an
            $files = Show-BackupFiles -Pattern "luckperms-*.sql"
            if ($files) {
                Write-Host "0. Zurück zum Hauptmenü"
                $fileChoice = Read-Host "Wähle ein Backup zur Wiederherstellung (1-$([Math]::Min($files.Count, 10)) oder 0 für Abbruch)"
                
                if ($fileChoice -match '^\d+$' -and [int]$fileChoice -gt 0 -and [int]$fileChoice -le $files.Count) {
                    $selectedFile = $files[[int]$fileChoice-1].FullName
                    $confirm = Read-Host "Möchtest du das Backup '$selectedFile' wirklich wiederherstellen? (j/n)"
                    
                    if ($confirm -eq "j") {
                        $dropDb = Read-Host "Datenbank komplett neu erstellen? Dies löscht alle bestehenden Daten! (j/n)"
                        $dropDatabase = $dropDb -eq "j"
                        
                        Restore-LuckPermsBackup -BackupFile $selectedFile -DropDatabase:$dropDatabase
                    }
                }
            }
        }
        default { Write-Host "Ungültige Aktion: $Action" -ForegroundColor Red }
    }
} else {
    do {
        Show-Menu
        $choice = Read-Host
        
        switch ($choice) {
            "1" { 
                Invoke-Backup 
                Write-Host "`nDrücke eine beliebige Taste zum Fortfahren..."
                $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            }
            "2" { 
                Start-WithBackup 
                Write-Host "`nDrücke eine beliebige Taste zum Fortfahren..."
                $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            }
            "3" { 
                Create-AllTasks 
                Write-Host "`nDrücke eine beliebige Taste zum Fortfahren..."
                $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            }
            "4" {
                $files = Show-BackupFiles -Pattern "luckperms-*.sql"
                if ($files) {
                    Write-Host "0. Zurück zum Hauptmenü"
                    $fileChoice = Read-Host "Wähle ein Backup zur Wiederherstellung (1-$([Math]::Min($files.Count, 10)) oder 0 für Abbruch)"
                    
                    if ($fileChoice -match '^\d+$' -and [int]$fileChoice -gt 0 -and [int]$fileChoice -le $files.Count) {
                        $selectedFile = $files[[int]$fileChoice-1].FullName
                        $confirm = Read-Host "Möchtest du das Backup '$selectedFile' wirklich wiederherstellen? (j/n)"
                        
                        if ($confirm -eq "j") {
                            $dropDb = Read-Host "Datenbank komplett neu erstellen? Dies löscht alle bestehenden Daten! (j/n)"
                            $dropDatabase = $dropDb -eq "j"
                            
                            Restore-LuckPermsBackup -BackupFile $selectedFile -DropDatabase:$dropDatabase
                        }
                    }
                }
                
                Write-Host "`nDrücke eine beliebige Taste zum Fortfahren..."
                $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            }
            "5" { return }
            default { 
                Write-Host "`nUngültige Auswahl!" -ForegroundColor Red 
                Start-Sleep -Seconds 2
            }
        }
    } while ($true)
} 