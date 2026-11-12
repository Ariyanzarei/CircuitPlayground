"""UDP audio -> browser bridge.

  1. listens for the ESP32's UDP audio packets on port 4211
  2. serves index.html on http://localhost:8766
  3. pushes each packet to the page via Server-Sent Events (/events)
SSE is text-only, so the binary packet is base64-encoded.
Standard library only.  Run:  python3 server.py   (or  --demo  for a test tone)
"""
import base64, math, queue, socket, struct, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UDP_PORT, HTTP_PORT = 4211, 8766
SAMPLE_RATE, SAMPLES_PER_PACKET = 8000, 256
clients: set[queue.Queue] = set()   # one queue per open browser tab
lock = threading.Lock()


def publish(packet: bytes):
    msg = base64.b64encode(packet).decode()
    with lock:
        for q in clients:
            try:
                q.put_nowait(msg)
            except queue.Full:      # slow tab: drop the packet
                pass


def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", UDP_PORT))
    print(f"Listening for UDP on :{UDP_PORT}")
    last_seq = None
    while True:
        packet, _ = sock.recvfrom(2048)
        # 4-byte packet number + samples. A PC with several network interfaces on the same
        # LAN receives each broadcast once per interface, so skip packets we've already seen.
        seq = struct.unpack_from("<I", packet)[0]
        if seq == last_seq:
            continue
        last_seq = seq
        publish(packet[4:])


def demo_generator():
    """Fake mic: a 440 Hz beep that turns on/off every second, centred at 2048 like the ADC."""
    t = 0
    while True:
        samples = []
        for _ in range(SAMPLES_PER_PACKET):
            on = (t // SAMPLE_RATE) % 2 == 0
            samples.append(int(2048 + (60 * math.sin(2 * math.pi * 440 * t / SAMPLE_RATE) if on else 0)))
            t += 1
        publish(struct.pack(f"<{SAMPLES_PER_PACKET}H", *samples))
        time.sleep(SAMPLES_PER_PACKET / SAMPLE_RATE)


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

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    source = demo_generator if "--demo" in sys.argv else udp_listener
    threading.Thread(target=source, daemon=True).start()
    print(f"Open http://localhost:{HTTP_PORT}")
    ThreadingHTTPServer(("", HTTP_PORT), Handler).serve_forever()
