import sen
import presion
import humedad
import time
import sht41



def todo(inicializado):
    if not inicializado:
        # inicializar display
        sen.init_display(sen.commands)
        sen.clear_display()

        # inicializar sensor de presion
        presion.init_pressure()

        #inicializar sensor de humedad
        humedad.init_aht20()

        #inicializar sensor de humedad
        sht41.inicializar()

    # Realizar mediciones
    shttemperature, shthumidity = sht41.medir()

    # Sensor de humedad
    if humedad.check_status() == 0x18:
        humidity, Htemperature = humedad.measure()
    
    # Sensor de presion
    calib_data = presion.read_calibration_data()
    adc_P, adc_T = presion.read_raw_data()
    temperature, t_fine = presion.compensate_temperature(adc_T, calib_data)
    pressure = presion.compensate_pressure(adc_P, calib_data, t_fine)
    altitude = presion.calculate_altitude(pressure)
    
    #Enviar al display
    sen.manage_space(f"{time.localtime()[3]:02d}:{time.localtime()[4]:02d}", sen.calibri32, start_page=0, alignement="Center")
    sen.manage_space(f"Temp: {(temperature + Htemperature)/2:.1f} °C", sen.calibri16, start_page=4, alignement="Center")
    sen.manage_space(f"Hum: {shthumidity} ", sen.calibri16, start_page=6, alignement="Center")
        
def dibujarPresion(inicializado):
    if not inicializado:
        # inicializar display
        sen.init_display(sen.commands)
        sen.clear_display()

        # inicializar sensor de presion
        presion.init_pressure()

    # Realizar mediciones
    # Sensor de presion
    calib_data = presion.read_calibration_data()
    adc_P, adc_T = presion.read_raw_data()
    temperature, t_fine = presion.compensate_temperature(adc_T, calib_data)
    pressure = presion.compensate_pressure(adc_P, calib_data, t_fine)
    altitude = presion.calculate_altitude(pressure)
    
    #Enviar al display
    sen.manage_space(f"Presion: ", sen.calibri16, start_page=0, alignement="Center")
    sen.manage_space(f"{pressure:.1f} hPa", sen.calibri16, start_page=2, alignement="Center")
    sen.manage_space(f"Altura: ", sen.calibri16, start_page=4, alignement="Center")
    sen.manage_space(f"{altitude:.1f} msnm", sen.calibri16, start_page=6, alignement="Center")
        
def dibujarHumedad(inicializado):
    if not inicializado:
        # inicializar display
        sen.init_display(sen.commands)
        sen.clear_display()

        #inicializar sensor de humedad
        humedad.init_aht20()
        
        #inicializar sensor de humedad
        sht41.inicializar()

    shttemperature, shthumidity = sht41.medir()


    # Enviar al display
    sen.manage_space(f"Temperatura: ", sen.calibri16, start_page=0, alignement="Center")
    sen.manage_space(f"{shttemperature}", sen.calibri16, start_page=2, alignement="Center")
    sen.manage_space(f"Humedad: ", sen.calibri16, start_page=4, alignement="Center")
    sen.manage_space(f"{shthumidity}", sen.calibri16, start_page=6, alignement="Center")
          

if __name__ == "__main__":  
    todo(False)
    while True:
        try:
            todo(True)
        except KeyboardInterrupt:
            print("\nInterrupción por teclado - Deteniendo...")
            break