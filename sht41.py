from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_sht.sht4x import Sht4xI2cDevice

def inicializar():
    transceiver = LinuxI2cTransceiver('/dev/i2c-1')
    connection = I2cConnection(transceiver)
    sensor = Sht4xI2cDevice(connection)
    return sensor

def medir(sensor):
    temperature, humidity = sensor.single_shot_measurement()
    return temperature, humidity

if __name__ == "__main__":
    sensor = inicializar()
    temperature, humidity = medir(sensor)
    print(temperature)
    print(humidity)
    