# KY-038 microphone → ESP32 → WiFi UDP → browser speaker

```
KY-038 --analog--> ESP32 ADC (8 kHz) --WiFi UDP :4211--> server.py --SSE--> browser (Web Audio)
```

## 1. Wiring (unplug USB first)

| KY-038 pin | ESP32 pin | Purpose |
|---|---|---|
| +  | 3V3    | Power. Use 3.3 V, not 5 V, so the output stays inside the ESP32's ADC range |
| -  | GND    | Ground |
| AO | GPIO34 | Analog audio signal |
| DO | not connected | Digital "loud / quiet" output (threshold set by the blue potentiometer) |

## 2. Firmware

```bash
cd firmware
cp src/secrets.example.h src/secrets.h   # set WiFi (already copied from ToF project)
pio run -t upload
pio device monitor     # prints "sample: N" each second; should sit roughly mid-scale and move when you talk
```
If the sample is stuck near 0 or 4095, turn the blue potentiometer until it sits in the middle.

## 3. Visualizer

```bash
cd visualizer
python3 server.py      # or --demo for a test beep
```
Open http://localhost:8766, click the speaker, then adjust **Gain**. If no data arrives: `sudo ufw allow 4211/udp`.

## Files
- `firmware/src/main.cpp`: samples at 8 kHz on core 1, sends 256-sample UDP packets from core 0
- `visualizer/server.py`: UDP listener + web server (base64-encodes packets for SSE)
- `visualizer/index.html`: removes DC offset, applies gain, plays via Web Audio; waves light up with loudness

## Troubleshooting
- **Monitor prints only dots:** WiFi isn't connecting. Check the name/password in `secrets.h` (2.4 GHz only).
- **`sample:` stuck at 0:** AO isn't connected or is at 0 V. Touch the GPIO34 wire to 3V3 (should read ~4095), then turn the multi-turn knob, which can take many turns.
- **Distorted sound:** turn the knob until the resting `sample:` is ~2000. The ESP32 ADC gets inaccurate above ~3000.
- **Sound plays slow or doubled:** the PC receives each broadcast once per network interface (e.g. WiFi + Ethernet). `server.py` drops duplicates using the packet number.
