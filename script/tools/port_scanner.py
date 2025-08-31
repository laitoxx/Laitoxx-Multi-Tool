import nmap
import socket
from ..shared_utils import Color

def scan_target(target, ports):
    """
    Scans target using nmap with specified ports
    """
    nm = nmap.PortScanner()
    try:
        # Use nmap to scan the target
        nm.scan(target, ports, arguments='-sV -T4')
        
        for host in nm.all_hosts():
            print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Scan results for {host}:")
            
            for proto in nm[host].all_protocols():
                print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Protocol: {proto}")
                
                ports = sorted(nm[host][proto].keys())
                for port in ports:
                    state = nm[host][proto][port]['state']
                    service = nm[host][proto][port].get('name', 'unknown')
                    version = nm[host][proto][port].get('version', '')
                    
                    if state == 'open':
                        print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Port {port}: {service} {version}")
                    else:
                        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Port {port}: {state}")
                        
    except nmap.PortScannerError as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Nmap scan failed: {e}")
    except Exception as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error during scan: {e}")

def port_scanner_tool():
    """
    Provides advanced port scanning using nmap.
    """
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Advanced Port Scanner")

    target_ip = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the target IP address or domain [localhost]: {Color.RESET}")
    if target_ip is None:
        return
    target_ip = target_ip.strip() or "127.0.0.1"

    try:
        # Resolve domain to IP
        target_ip = socket.gethostbyname(target_ip)
        print(f"{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Target resolved to: {target_ip}")
    except socket.gaierror:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not resolve host: {target_ip}")
        return
        
    # Get port range from user
    port_range = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter port range (e.g. 20-100) or specific ports (e.g. 80,443) [1-1000]: {Color.RESET}")
    if port_range is None:
        return
    port_range = port_range.strip() or "1-1000"
    
    print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Starting nmap scan of {target_ip} ports {port_range}...")
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} This may take a few moments...")
    
    try:
        scan_target(target_ip, port_range)
    except KeyboardInterrupt:
        print(f"\n{Color.DARK_GRAY}[{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW} Scan interrupted by user")
    except Exception as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Scan failed: {e}")
        
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Scan complete.")

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan commonly used ports")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan a specific port range")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan a single port")

    mode = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Choose mode: {Color.RESET}").strip()

    ports_to_scan = []

