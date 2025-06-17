import multiprocessing
import time

def stress():
    while True:
        pass  

if __name__ == "__main__":
    cpu_count = multiprocessing.cpu_count()
    print(f"Spawning {cpu_count} stress processes. Press Ctrl+C to stop.")
    procs = []
    for _ in range(cpu_count):
        p = multiprocessing.Process(target=stress)
        p.start()
        procs.append(p)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping stress test...")
        for p in procs:
            p.terminate()
