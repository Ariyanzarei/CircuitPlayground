# VL53L0X ToF laser → ESP32 → WiFi UDP → web visualizer

```
VL53L0X --I2C--> ESP32 --WiFi UDP broadcast :4210--> server.py --SSE--> browser (2D canvas)
```

## 1. Wiring (unplug USB first)

| VL53L0X pin | ESP32 pin | Purpose |
|---|---|---|
| VIN (VCC)   | 3V3    | Power (3.3 V) |
| GND         | GND    | Ground |
| SDA         | GPIO21 | I2C data |
| SCL         | GPIO22 | I2C clock |
| XSHUT, GPIO1 | not connected | Only needed for multiple sensors / interrupts |

Peel the protective film off the sensor window, or readings will be wrong.

## 2. Firmware (ESP32, C++)

Tools: PlatformIO CLI (`pio`), installed in `~/.platformio/penv`.

```bash
cd firmware
cp src/secrets.example.h src/secrets.h   # then set your 2.4 GHz WiFi name/password
pio run -t upload                        # compile + flash
pio device monitor                       # view serial output (Ctrl+C to quit)
```

## 3. Visualizer (PC)

```bash
cd visualizer
python3 server.py          # real sensor   (python3 server.py --demo for fake data)
```
Open http://localhost:8765. If no data arrives, allow UDP through the firewall: `sudo ufw allow 4210/udp`.

## Files
- `firmware/src/main.cpp`: reads the sensor, sends `{"mm":123,"valid":true}` as UDP packets
- `visualizer/server.py`: UDP listener + web server (browsers can't receive UDP)
- `visualizer/index.html`: 2D canvas: live beam gauge + distance-over-time chart
