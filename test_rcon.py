import mcrcon
import os
from dotenv import load_dotenv

def test_rcon_connection():
    load_dotenv()
    
    # RCON-Verbindungsdaten mit Host-IP für Docker
    host = "host.docker.internal"  # Spezielle DNS für den Host aus Docker
    port = int(os.getenv("RCON_PORT", "25575"))
    password = os.getenv("RCON_PASSWORD")
    
    print(f"Versuche Verbindung zu {host}:{port} herzustellen...")
    
    try:
        # Verbindung herstellen
        rcon = mcrcon.MCRcon(host, password, port)
        rcon.connect()
        print("Verbindung erfolgreich hergestellt!")
        
        # Test-Befehl senden
        print("Sende Test-Befehl: help")
        response = rcon.command("help")
        print(f"Antwort:\n{response}")
        
        # VPW-Befehl testen
        print("\nSende VPW-Befehl: vpw")
        response = rcon.command("vpw")
        print(f"Antwort:\n{response}")
        
        # Teste glist-send Befehl
        print("\nSende glist-send Befehl: glist-send lobby:vpw")
        response = rcon.command("glist-send lobby:vpw")
        print(f"Antwort:\n{response}")
        
        rcon.disconnect()
        print("Verbindung erfolgreich geschlossen.")
        
    except ConnectionRefusedError:
        print("Fehler: Verbindung abgelehnt. Läuft der Minecraft-Server?")
    except TimeoutError:
        print("Fehler: Verbindungs-Timeout. Ist der Server erreichbar?")
    except Exception as e:
        print(f"Fehler: {str(e)}")

if __name__ == "__main__":
    test_rcon_connection() 