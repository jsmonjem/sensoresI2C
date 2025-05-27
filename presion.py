from smbus2 import SMBus
import struct
import math

I2C_BUS = 1
BMP280_ADDR = 0x77
bus = SMBus(I2C_BUS)

def init_pressure():
    t_sb = 4       # 100 -> 500 ms entre mediciones
    filter = 4     # 100 -> Filtro x16
    osrs_t = 2     # 010 -> Oversampling x2 (temperatura)
    osrs_p = 5     # 101 -> Oversampling x16 (presión)

    bus.write_byte_data(BMP280_ADDR, 0xF5, (t_sb << 5) | (filter << 2))
    bus.write_byte_data(BMP280_ADDR, 0xF4, (osrs_t << 5) | (osrs_p << 2) | 3)  # Mode = 11 (normal)
    print("Sensor de presión inicializado correctamente.")

def read_raw_data():
    press_raw = bus.read_i2c_block_data(BMP280_ADDR, 0xF7, 3)
    temp_raw = bus.read_i2c_block_data(BMP280_ADDR, 0xFA, 3)
    adc_P = (press_raw[0] << 12) | (press_raw[1] << 4) | (press_raw[2] >> 4)
    adc_T = (temp_raw[0] << 12) | (temp_raw[1] << 4) | (temp_raw[2] >> 4)
    return adc_P, adc_T

def read_calibration_data():
    calib = bus.read_i2c_block_data(BMP280_ADDR, 0x88, 24)
    return {
        'dig_T1': struct.unpack('<H', bytes(calib[0:2]))[0],
        'dig_T2': struct.unpack('<h', bytes(calib[2:4]))[0],
        'dig_T3': struct.unpack('<h', bytes(calib[4:6]))[0],
        'dig_P1': struct.unpack('<H', bytes(calib[6:8]))[0],
        'dig_P2': struct.unpack('<h', bytes(calib[8:10]))[0],
        'dig_P3': struct.unpack('<h', bytes(calib[10:12]))[0],
        'dig_P4': struct.unpack('<h', bytes(calib[12:14]))[0],
        'dig_P5': struct.unpack('<h', bytes(calib[14:16]))[0],
        'dig_P6': struct.unpack('<h', bytes(calib[16:18]))[0],
        'dig_P7': struct.unpack('<h', bytes(calib[18:20]))[0],
        'dig_P8': struct.unpack('<h', bytes(calib[20:22]))[0],
        'dig_P9': struct.unpack('<h', bytes(calib[22:24]))[0],
    }

def compensate_temperature(adc_T, calib):
    var1 = (((adc_T >> 3) - (calib['dig_T1'] << 1)) * calib['dig_T2']) >> 11
    var2 = (((((adc_T >> 4) - calib['dig_T1']) * ((adc_T >> 4) - calib['dig_T1'])) >> 12) * calib['dig_T3']) >> 14
    t_fine = var1 + var2
    temperature = (t_fine * 5 + 128) >> 8
    return temperature / 100.0, t_fine

def compensate_pressure(adc_P, calib, t_fine):
    var1 = (t_fine >> 1) - 64000
    var2 = (((var1 >> 2) * (var1 >> 2)) >> 11) * calib['dig_P6']
    var2 += ((var1 * calib['dig_P5']) << 1)
    var2 = (var2 >> 2) + (calib['dig_P4'] << 16)
    var1 = (((calib['dig_P3'] * ((var1 >> 2) * (var1 >> 2)) >> 13) >> 3) + ((calib['dig_P2'] * var1) >> 1)) >> 18
    var1 = ((32768 + var1) * calib['dig_P1']) >> 15
    if var1 == 0:
        return 0  # Evitar división por cero
    p = ((1048576 - adc_P) - (var2 >> 12)) * 3125
    p = (p << 1) // var1
    var1 = (calib['dig_P9'] * ((p >> 3) * (p >> 3)) >> 13) >> 12
    var2 = ((p >> 2) * calib['dig_P8']) >> 13
    pressure = p + ((var1 + var2 + calib['dig_P7']) >> 4)
    return pressure / 100.0  # Convertir a hPa

def calculate_altitude(pressure, P0=1028.11):
    T0 = 288.15
    L = 0.0065
    R = 287.05
    g = 9.80665
    altitude = (T0 / L) * (1 - (pressure / P0) ** (L * R / g))
    return altitude

if __name__ == "__main__":
    init_pressure()
    calib_data = read_calibration_data()
    adc_P, adc_T = read_raw_data()
    temperature, t_fine = compensate_temperature(adc_T, calib_data)
    pressure = compensate_pressure(adc_P, calib_data, t_fine)
    altitude = calculate_altitude(pressure)
    
    print(f"Temperatura: {temperature:.2f} °C")
    print(f"Presión: {pressure:.2f} hPa")
    print(f"Altitud estimada: {altitude:.2f} m")
