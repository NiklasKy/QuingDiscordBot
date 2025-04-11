# PowerShell-Skript für Docker-Management
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$Action
)

# Grundlegende Konfiguration
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

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
        docker-compose up -d $ContainerName
        Start-Sleep -Seconds 10
        Get-Content $latestBackup.FullName | docker exec -i $ContainerName psql -U $User -d $DbName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Wiederherstellung erfolgreich!" -ForegroundColor Green
        } else {
            Write-Host "Fehler bei der Wiederherstellung!" -ForegroundColor Red
        }
    } else {
        Write-Host "Kein Backup für $DbName gefunden. Starte mit leerer Datenbank." -ForegroundColor Yellow
        docker-compose up -d $ContainerName
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
}

# Funktion zum Starten mit Backup-Wiederherstellung
function Start-WithBackup {
    Initialize-Directories
    Restore-Postgres -ContainerName "luckperms-postgres" -DbName "luckperms" -User "luckperms" -Password $env:LUCKPERMS_DB_PASSWORD
    Restore-Postgres -ContainerName "husksync-postgres" -DbName "husksync" -User "husksync" -Password $env:HUSKSYNC_DB_PASSWORD
    Restore-Postgres -ContainerName "quingcraft-postgres" -DbName "quingcraft" -User "quingcraft" -Password $env:QUINGCRAFT_DB_PASSWORD
    Restore-Redis
    Restore-BotConfig
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

# Hauptmenü
function Show-Menu {
    Clear-Host
    Write-Host "Docker Manager für Minecraft Server" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    Write-Host "1. Backup erstellen"
    Write-Host "2. Container mit Backup-Wiederherstellung starten"
    Write-Host "3. Alle geplanten Aufgaben erstellen"
    Write-Host "4. Beenden"
    Write-Host "`nBitte wähle eine Option (1-4): " -NoNewline -ForegroundColor Yellow
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
            "4" { return }
            default { 
                Write-Host "`nUngültige Auswahl!" -ForegroundColor Red 
                Start-Sleep -Seconds 2
            }
        }
    } while ($true)
} 