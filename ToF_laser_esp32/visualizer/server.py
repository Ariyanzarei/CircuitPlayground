"""UDP -> browser bridge.

Browsers can't receive UDP, so this script:
  1. listens for the ESP32's UDP packets on port 4210
  2. serves index.html on http://localhost:8765
  3. pushes every packet to the page via Server-Sent Events (/events)
Standard library only.  Run:  python3 server.py   (or  --demo  for fake data)
"""
import math, queue, socket, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UDP_PORT, HTTP_PORT = 4210, 8765
clients: set[queue.Queue] = set()   # one queue per open browser tab
lock = threading.Lock()


def publish(msg: str):
    with lock:
        for q in clients:
            try:
                q.put_nowait(msg)
            except queue.Full:      # slow tab: drop the reading
                pass


def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", UDP_PORT))       # "" = all interfaces, also catches broadcasts
    print(f"Listening for UDP on :{UDP_PORT}")
    while True:
        data, addr = sock.recvfrom(256)
        publish(data.decode(errors="ignore").strip())


def demo_generator():               # fake sensor for testing without hardware
    while True:
        mm = int(600 + 450 * math.sin(time.time()))
        publish(f'{{"mm":{mm},"valid":true}}')
        time.sleep(0.033)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        if self.path != "/events":
            return super().do_GET()         # static files (index.html)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q = queue.Queue(maxsize=50)
        with lock:
            clients.add(q)
        try:
            while True:
                self.wfile.write(f"data: {q.get()}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass                            # tab closed
        finally:
            with lock:
                clients.discard(q)

    def log_message(self, *args):           # keep the console quiet
        pass


if __name__ == "__main__":
    source = demo_generator if "--demo" in sys.argv else udp_listener
    threading.Thread(target=source, daemon=True).start()
    print(f"Open http://localhost:{HTTP_PORT}")
    ThreadingHTTPServer(("", HTTP_PORT), Handler).serve_forever()
