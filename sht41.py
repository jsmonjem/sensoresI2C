from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_sht.sht4x import Sht4xI2cDevice

_sensor = None  # estado global controlado

def inicializar():
    global _sensor
    if _sensor is None:
        transceiver = LinuxI2cTransceiver('/dev/i2c-1')
        connection = I2cConnection(transceiver)
        _sensor = Sht4xI2cDevice(connection)
    return _sensor

def medir():
    temperature, humidity = _sensor.single_shot_measurement()
    return temperature, humidity
