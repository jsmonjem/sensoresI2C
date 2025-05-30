from smbus2 import SMBus
import time

I2C_BUS = 1
AHT20_ADDR = 0x38  

bus = SMBus(I2C_BUS)

def init_aht20():

    # Send AHT20 initialization command
    bus.write_i2c_block_data(AHT20_ADDR, 0xBe, [0x08, 0x00])
    time.sleep(0.02)  # Esperar 10 ms para la inicialización
    print("Humidity sensor correctly initialized.")

def reset_aht20():
    # Envía el comando de soft Reset del AHT20
    bus.write_i2c_block_data(AHT20_ADDR, 0xBa,[])
    time.sleep(0.02)  # Esperar 20 ms para el soft reset.
    print("Sensor de humedad reiniciado.")

def check_status():
    # Lee el estado del sensor 
    status = bus.read_byte(AHT20_ADDR,0x71)
    return status
    

def measure():
    # Envía el comando de medición y espera 80ms para que el sensor realice la medición
    bus.write_i2c_block_data(AHT20_ADDR, 0xAC, [0x33, 0x00])
    time.sleep(0.08)  

    # Leer 6 bytes de datos
    status = bus.read_i2c_block_data(AHT20_ADDR, 0x00, 6)
    
    # Extraer humedad y temperatura de los bits recibidos
    raw_humidity = (status[1] << 12) | (status[2] << 4) | (status[3] >> 4)
    raw_temperature = ((status[3] & 0x0F) << 16) | (status[4] << 8) | status[5]

    humidity = (raw_humidity / (2**20)) * 100
    temperature = ((raw_temperature / (2**20)) * 200 )- 50

    return humidity, temperature


def get_humedad():
    # Obtiene la humedad y temperatura del sensor AHT20
    init_aht20()
    humidity, Htemperature = measure()
    if check_status() == 0x18:
        return humidity, Htemperature
    else:
        print("Error al leer el sensor AHT20")
        return None, None


if __name__ == "__main__":  
    while True:
        print(f"Sensor AHT20: {get_humedad()}")
        time.sleep(1)

