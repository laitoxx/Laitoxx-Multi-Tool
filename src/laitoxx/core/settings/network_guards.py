"""DNS and raw-socket guards used while a SOCKS proxy is active."""

import ipaddress
import socket


class NetworkGuards:
    def __init__(self, state: dict, originals: dict):
        self.state = state
        self.originals = originals
        self.dns_installed = False
        self.socket_installed = False

    def allowed_host(self, host: str) -> bool:
        if not host:
            return True
        normalized = str(host).strip().strip("[]").lower()
        proxy_host = str(self.state.get("proxy_host", "")).strip().strip("[]").lower()
        if normalized in {proxy_host, "localhost"}:
            return True
        try:
            return ipaddress.ip_address(normalized).is_loopback
        except ValueError:
            return False

    def install_dns(self) -> None:
        if self.dns_installed:
            return

        def getaddrinfo(host, port, *args, **kwargs):
            if self.allowed_host(host):
                return self.originals["getaddrinfo"](host, port, *args, **kwargs)
            raise OSError(f"[NetworkManager] DNS resolution of '{host}' blocked while SOCKS proxy is active")

        def gethostbyname(host):
            if self.allowed_host(host):
                return self.originals["gethostbyname"](host)
            raise OSError(f"[NetworkManager] DNS resolution of '{host}' blocked while SOCKS proxy is active")

        def gethostbyname_ex(host):
            if self.allowed_host(host):
                return self.originals["gethostbyname_ex"](host)
            raise OSError(f"[NetworkManager] DNS resolution of '{host}' blocked while SOCKS proxy is active")

        socket.getaddrinfo = getaddrinfo
        socket.gethostbyname = gethostbyname
        socket.gethostbyname_ex = gethostbyname_ex
        self.dns_installed = True

    def remove_dns(self) -> None:
        socket.getaddrinfo = self.originals["getaddrinfo"]
        socket.gethostbyname = self.originals["gethostbyname"]
        socket.gethostbyname_ex = self.originals["gethostbyname_ex"]
        self.dns_installed = False

    def install_socket(self) -> None:
        if self.socket_installed:
            return

        def create_connection(address, *args, **kwargs):
            host = address[0] if address else ""
            if self.allowed_host(host):
                return self.originals["create_connection"](address, *args, **kwargs)
            raise OSError(f"[NetworkManager] Direct TCP connection to '{host}' blocked while proxy is active")

        def socket_connect(sock, address):
            host = address[0] if isinstance(address, tuple) and address else ""
            if self.allowed_host(host):
                return self.originals["socket_connect"](sock, address)
            raise OSError(f"[NetworkManager] Direct socket connection to '{host}' blocked while proxy is active")

        socket.create_connection = create_connection
        socket.socket.connect = socket_connect
        self.socket_installed = True

    def remove_socket(self) -> None:
        socket.create_connection = self.originals["create_connection"]
        socket.socket.connect = self.originals["socket_connect"]
        self.socket_installed = False
