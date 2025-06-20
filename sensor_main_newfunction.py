import os
import time
import datetime
import csv
import json
import atexit

import board
import adafruit_dht
from gpiozero import Button
from gpiozero.pins.rpigpio import RPiGPIOFactory

# ============================== Config and Setup ==============================

# Define ANSI color codes
class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"

def load_config():
    config_path = os.getenv('CONFIG_PATH', './config.json')
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"{Color.RED}Failed to load config.json: {e}{Color.END}")
        exit(1)

config = load_config()

folder_path = config.get("folder_path", "./data")
os.makedirs(folder_path, exist_ok=True)

dht_pin = board.D4
door_switch_pin = 11  # GPIO 0 = pin 11 (BCM mode)

# =========================== Door Status Functions ===========================

def door_close():
    global door_status
    door_status = 0
    print(f"{Color.BLUE}Door Closed{Color.END}")

def door_open():
    global door_status
    door_status = 1
    print(f"{Color.YELLOW}Door Opened{Color.END}")

# ============================= Sensor Functions ==============================

def initialize_sensors(sensor_count, pin):
    sensors = []
    for i in range(sensor_count):
        sensors.append(adafruit_dht.DHT22(pin))
    return sensors

def read_sensor(sensor, sensor_id):
    try:
        temperature_c = sensor.temperature
        humidity = sensor.humidity
        if temperature_c is not None and humidity is not None:
            print(f"{Color.GREEN}Sensor {sensor_id+1}: Temp = {temperature_c:.1f}°C, Humidity = {humidity:.1f}%{Color.END}")
            return temperature_c, humidity
    except Exception as e:
        print(f"{Color.RED}Sensor {sensor_id+1} read error: {e}{Color.END}")
    return None, None

def write_csv(filename, timestamp, sensor_id, temperature, humidity, door_status):
    try:
        file_exists = os.path.isfile(filename)
        with open(filename, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Timestamp", "Sensor ID", "Temperature (C)", "Humidity (%)", "Door Status"])
            writer.writerow([timestamp, sensor_id, temperature, humidity, door_status])
    except Exception as e:
        print(f"{Color.RED}Failed to write to CSV: {e}{Color.END}")

# ============================== Main Function ================================

def main():
    print(f"{Color.CYAN}Starting Temperature Monitoring System in Docker...{Color.END}")

    global door_status
    door_status = 1  # Assume door is open initially

    # GPIO setup with error handling
    try:
        factory = RPiGPIOFactory()
        door_switch = Button(door_switch_pin, pin_factory=factory)
        door_switch.when_pressed = door_close
        door_switch.when_released = door_open
    except Exception as e:
        print(f"{Color.RED}GPIO setup failed: {e}{Color.END}")
        door_switch = None  # fallback if GPIO is not available

    sensor_count = config.get("sensor_count", 10)
    sensors = initialize_sensors(sensor_count, dht_pin)

    def cleanup():
        for sensor in sensors:
            sensor.exit()
    atexit.register(cleanup)

    while True:
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        filename = os.path.join(folder_path, f"{date_str}.csv")

        for i, sensor in enumerate(sensors):
            temperature, humidity = read_sensor(sensor, i)
            if temperature is not None and humidity is not None:
                write_csv(filename, timestamp, i + 1, temperature, humidity, door_status)

        time.sleep(30)

# =============================== Entry Point ================================

if __name__ == "__main__":
    main()
