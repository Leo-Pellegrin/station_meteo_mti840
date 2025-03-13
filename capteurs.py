import time
import os
import Adafruit_DHT
import Adafruit_BMP.BMP085 as BMP085
import RPi.GPIO as GPIO
import smbus
import PCF8591 as ADC

# Configuration des GPIO
GPIO.setmode(GPIO.BCM)

# ======= 1️⃣ Capteur de pluie (Rain Detection) =======
class RainSensor:
    def __init__(self, do_pin=5, adc_channel=0):
        self.do_pin = do_pin
        self.adc_channel = adc_channel
        GPIO.setup(self.do_pin, GPIO.IN)
        ADC.setup(0x48)

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

# ======= 3️⃣ Capteur DHT11 (Humidité & Température) =======
class DHT11:
    def __init__(self, pin=17):
        self.pin = pin

    def read(self):
        humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, self.pin)
        return {
            "humidity": humidity,
            "temperature": temperature
        }

# ======= 4️⃣ Capteur de Pression BMP180 =======
class Barometer:
    def __init__(self):
        self.sensor = BMP085.BMP085()

    def read(self):
        return {
            "temperature": self.sensor.read_temperature(),
            "pressure": self.sensor.read_pressure()
        }

# ======= 🔄 Boucle principale =======
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

            # Affichage des résultats
            print("\n===== 🌡️ Données des Capteurs =====")
            print(f"🌧️ Pluie : {'Oui' if rain_data['raining'] else 'Non'} (Analog: {rain_data['analog']})")
            print(f"🔥 Température DS18B20 : {temp_ds18b20:.2f}°C")
            print(f"💧 Humidité DHT11 : {dht_data['humidity']}%")
            print(f"🌡️ Température DHT11 : {dht_data['temperature']}°C")
            print(f"🌍 Pression BMP180 : {barometer_data['pressure']} Pa")
            print(f"🌡️ Température BMP180 : {barometer_data['temperature']}°C")
            
            time.sleep(2)  # Pause de 2 secondes entre chaque lecture

    except KeyboardInterrupt:
        print("\nArrêt du programme. Nettoyage des GPIO...")
        GPIO.cleanup()

# ======= Démarrage du script =======
if __name__ == "__main__":
    main()