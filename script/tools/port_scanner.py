import socket
import threading
from queue import Queue
from ..shared_utils import Color

# A lock for printing to avoid garbled output from threads
print_lock = threading.Lock()

def scan_port(target, port):
    """
    Scans a single port on the target IP.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1) # 1 second timeout for connection attempt
            result = s.connect_ex((target, port))
            if result == 0:
                with print_lock:
                    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Port {port} is open")
    except socket.error as e:
        with print_lock:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error scanning port {port}: {e}")

def worker(target, port_queue):
    """
    Worker thread that takes ports from the queue and scans them.
    """
    while not port_queue.empty():
        port = port_queue.get()
        scan_port(target, port)
        port_queue.task_done()

def port_scanner_tool():
    """
    Provides options to scan for open ports on a target host.
    """
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Port Scanner")

    target_ip = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the target IP address or domain [localhost]: {Color.RESET}")
    if target_ip is None:
        return
    target_ip = target_ip.strip() or "127.0.0.1"

    try:
        # Resolve domain to IP
        target_ip = socket.gethostbyname(target_ip)
        print(f"{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Scanning target: {target_ip}")
    except socket.gaierror:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not resolve host: {target_ip}")
        return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan commonly used ports")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan a specific port range")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan a single port")

    mode = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Choose mode: {Color.RESET}").strip()

    ports_to_scan = []
    if mode == '1':
        ports_to_scan = [20, 21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080]
    elif mode == '2':
        try:
            port_range_str = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter port range (e.g., 1-100): {Color.RESET}").strip()
            start, end = map(int, port_range_str.split('-'))
            ports_to_scan = range(start, end + 1)
        except ValueError:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid range format.")
            return
    elif mode == '3':
        try:
            port = int(input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter port number: {Color.RESET}").strip())
            ports_to_scan = [port]
        except ValueError:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid port number.")
            return
    else:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Unknown mode.")
        return

    if not ports_to_scan:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No ports to scan.")
        return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Starting scan...")

    port_queue = Queue()
    for port in ports_to_scan:
        port_queue.put(port)

    # Start worker threads
    num_threads = min(100, len(ports_to_scan)) # Use up to 100 threads
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(target_ip, port_queue))
        thread.start()
        threads.append(thread)

    # Wait for the queue to be empty
    port_queue.join()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Port scan finished.")
