import time
import os 
import Adafruit_BMP.BMP085 as BMP085
import RPi.GPIO as GPIO
import smbus
from PCF8591 import PCF8591

ADC = PCF8591(0x48)

# Configuration des GPIO
GPIO.setmode(GPIO.BCM)

# ======= 1️⃣ Capteur de pluie (Rain Detection) =======
class RainSensor:
    def __init__(self, do_pin=5, adc_channel=0):
        self.do_pin = do_pin
        self.adc_channel = adc_channel
        GPIO.setup(self.do_pin, GPIO.IN)

    def read(self):
        analog_value = ADC.read(self.adc_channel)
        digital_value = GPIO.input(self.do_pin)
        return {
            "analog": analog_value,
            "raining": digital_value == 0  # 0 = pluie détectée
        }

# ======= 2️⃣ Capteur de température DS18B20 =======
class DS18B20:
    def __init__(self):
        self.device_folder = self.find_device()

    def find_device(self):
        for device in os.listdir('/sys/bus/w1/devices'):
            if device.startswith("28-"):
                return f"/sys/bus/w1/devices/{device}/w1_slave"
        return None

    def read_temperature(self):
        if not self.device_folder:
            return None
        with open(self.device_folder, "r") as file:
            lines = file.readlines()
        temp_str = lines[1].split("t=")[-1]
        return float(temp_str) / 1000

# ======= 3️⃣ Capteur DHT11 (Humidité & Température) (Sans Adafruit_DHT) =======
import time
import RPi.GPIO as GPIO

class DHT11:
    def __init__(self, pin=17):
        """Initialisation du capteur DHT11 sur la broche spécifiée"""
        self.pin = pin
        GPIO.setwarnings(False)  # Désactive les warnings GPIO
        GPIO.setmode(GPIO.BCM)  # Mode BCM pour utiliser les numéros de GPIO
        GPIO.setup(self.pin, GPIO.OUT)  # Configuration en sortie pour initier le signal

    def read(self):
        """Lecture des données du capteur DHT11"""
        MAX_UNCHANGE_COUNT = 100
        STATE_INIT_PULL_DOWN = 1
        STATE_INIT_PULL_UP = 2
        STATE_DATA_FIRST_PULL_DOWN = 3
        STATE_DATA_PULL_UP = 4
        STATE_DATA_PULL_DOWN = 5

        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(0.02)
        GPIO.setup(self.pin, GPIO.IN, GPIO.PUD_UP)

        unchanged_count = 0
        last = -1
        data = []
        while True:
            current = GPIO.input(self.pin)
            data.append(current)
            if last != current:
                unchanged_count = 0
                last = current
            else:
                unchanged_count += 1
                if unchanged_count > MAX_UNCHANGE_COUNT:
                    break

        state = STATE_INIT_PULL_DOWN
        lengths = []
        current_length = 0

        for current in data:
            current_length += 1

            if state == STATE_INIT_PULL_DOWN:
                if current == GPIO.LOW:
                    state = STATE_INIT_PULL_UP
                else:
                    continue
            elif state == STATE_INIT_PULL_UP:
                if current == GPIO.HIGH:
                    state = STATE_DATA_FIRST_PULL_DOWN
                else:
                    continue
            elif state == STATE_DATA_FIRST_PULL_DOWN:
                if current == GPIO.LOW:
                    state = STATE_DATA_PULL_UP
                else:
                    continue
            elif state == STATE_DATA_PULL_UP:
                if current == GPIO.HIGH:
                    current_length = 0
                    state = STATE_DATA_PULL_DOWN
                else:
                    continue
            elif state == STATE_DATA_PULL_DOWN:
                if current == GPIO.LOW:
                    lengths.append(current_length)
                    state = STATE_DATA_PULL_UP
                else:
                    continue

        if len(lengths) != 40:
            return {"humidity": None, "temperature": None}

        shortest_pull_up = min(lengths)
        longest_pull_up = max(lengths)
        halfway = (longest_pull_up + shortest_pull_up) / 2
        bits = []
        the_bytes = []
        byte = 0

        for length in lengths:
            bit = 0
            if length > halfway:
                bit = 1
            bits.append(bit)

        for i in range(len(bits)):
            byte = byte << 1
            if bits[i]:
                byte = byte | 1
            if (i + 1) % 8 == 0:
                the_bytes.append(byte)
                byte = 0

        if len(the_bytes) != 5:
            return {"humidity": None, "temperature": None}

        checksum = (the_bytes[0] + the_bytes[1] + the_bytes[2] + the_bytes[3]) & 0xFF
        if the_bytes[4] != checksum:
            return {"humidity": None, "temperature": None}

        return {"humidity": the_bytes[0], "temperature": the_bytes[2]}

    def cleanup(self):
        """Libère les ressources GPIO"""
        GPIO.cleanup()

# ======= 4️⃣ Capteur de Pression BMP180 =======
class Barometer:
    def __init__(self):
        self.sensor = BMP085.BMP085(busnum=1)

    def read(self):
        return {
	    "temperature": self.sensor.read_temperature(),
            "pressure": self.sensor.read_pressure()
        }

import requests
import json

# URL de l'API externe
API_URL = "http://52.237.13.71:8000/add-data?bucket=station_meteo"  # Remplace avec l'URL de ton API

def send_to_api(data):
    """Envoie les données au serveur via une requête HTTP POST"""
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(API_URL, json=data, headers=headers, timeout=5)
        if response.status_code == 200:
            print("✅ Données envoyées avec succès !")
        else:
            print(f"⚠️ Erreur {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur d'envoi : {e}")

def main():
    print("🔎 Initialisation des capteurs...")

    # Initialisation des capteurs
    rain_sensor = RainSensor()
    ds18b20 = DS18B20()
    dht11 = DHT11()
    barometer = Barometer()

    try:
        while True:
            # Lecture des capteurs
            rain_data = rain_sensor.read()
            temp_ds18b20 = ds18b20.read_temperature()
            dht_data = dht11.read()
            barometer_data = barometer.read()

            # Construction des données à envoyer
            data = {
                "pluie": int(1 if rain_data["raining"] else 0),  # Convertir explicitement en int
                "temperature_DS18B20": float(temp_ds18b20) if temp_ds18b20 is not None else 0.0,
                "humidity_dht11": float(dht_data["humidity"]) if dht_data["humidity"] is not None else 0.0,
                "temperature_dht11": float(dht_data["temperature"]) if dht_data["temperature"] is not None else 0.0,
                "pressure": float(barometer_data["pressure"]) if barometer_data["pressure"] is not None else 101325.0,
                "temperature_bmp180": float(barometer_data["temperature"]) if barometer_data["temperature"] is not None else 0.0,
            }                  
            
            print("\n===== 🌡️ Données des Capteurs =====")
            print(json.dumps(data, indent=4))

            # Envoi des données à l'API
            send_to_api(data)

            time.sleep(5)  # Pause avant la prochaine lecture

    except KeyboardInterrupt:
        print("\nArrêt du programme. Nettoyage des GPIO...")
        GPIO.cleanup()

# ======= Démarrage du script =======
if __name__ == "__main__":
    main()