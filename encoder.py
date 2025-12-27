import math
import time
import os
import json
import sen
import script
from i2c_bus import bus


#=====================================================================
# Code to read AS5600.  
import smbus2

DEVICE_AS5600 = 0x36 # Default device I2C address
#bus = smbus2.SMBus(1)

def ReadRawAngle(): # Read angle (0-360 represented as 0-4096)
    read_bytes = bus.read_i2c_block_data(DEVICE_AS5600, 0x0C, 2)
    return ((read_bytes[0] << 8) | read_bytes[1]) & 0xFFF

def ReadAngle(): # Read angle (0-360 represented as 0-4096)
    read_bytes = bus.read_i2c_block_data(DEVICE_AS5600, 0x0E, 2)
    return (read_bytes[0]<<8) | read_bytes[1]

def degtoxy(degrees0360):
    rad = degrees0360*math.pi/180
    x=math.cos(rad)
    y=math.sin(rad)
    return (x,y)

def ReadMagnitude(): # Read magnetism magnitude
  read_bytes = bus.read_i2c_block_data(DEVICE_AS5600, 0x1B, 2)
  return (read_bytes[0]<<8) | read_bytes[1];

def configurarFiltros():
    bus.write_byte_data(DEVICE_AS5600, 0x07, 0x10)

def configurarOtros(comando):
    bus.write_byte_data(DEVICE_AS5600, 0x07, comando)
#=====================================================================

def MoveCursor(x,y):
        print("\033[%d;%dH"%(y,x),end="")   
    
def dibujarAngulo(adicional=False, angulo=0):
    xcenter = 40 # Assume center of text screen is 60 across, 30 down.
    ycenter = 16 # if your screen is 80x50, change to 40 and 25.
    
    histlen = 20
    hist_index = 0
    hist = [(0,0)] * histlen

    # Clear screen
    #print("\033[2J",end="")
    
    # Draw x and y axis on screen
    for a in range (-ycenter, ycenter):
        MoveCursor(xcenter, ycenter+a)
        print("|", end="")

    for a in range (-xcenter, xcenter):
        MoveCursor(xcenter+a, ycenter)
        print("-")

    raw_angle = ReadRawAngle()
    angle = raw_angle/4096*360
    rad = angle*math.pi/180
    magnitude = 0.8 #ReadMagnitude()/4096

    #MoveCursor(0,0)
    #print(f"Magnitude:{magnitude:6.4f}   Degrees:{angle:6.4f}")
    # Now plot X and Y position by graphing on the screen
    cx = int(xcenter + xcenter * magnitude * math.cos(rad))
    cy = int(ycenter + ycenter * magnitude * math.sin(rad))
    
    if adicional:
        cxa = int(xcenter + xcenter * magnitude * math.cos(angulo*math.pi/180))
        cya = int(ycenter + ycenter * magnitude * math.sin(angulo*math.pi/180))
        
    
    # Delete old mark (keep up to 400 on screen)
    oldpos = hist[hist_index]
    MoveCursor(*oldpos)
    if oldpos[0] == xcenter:
        print("|",end="")
    elif oldpos[1] == ycenter:
        print("-",end="")
    else:
        print(" ",end="")
    # Save new mark positon in array
    hist[hist_index] = (cx,cy)
    hist_index += 1;
    if hist_index >= histlen: hist_index = 0
    # Draw a '#' at the computed X,Y coordinate
    MoveCursor(cx,cy)
    print("#",end="")


def velocidad():
    now    = time.time()               # Momento 0
    angulo_previo  = ReadAngle()/4096*360   # Angulo  0
    
    now1   = time.time()               # Momento 0+t
    angulo_actual = ReadAngle()/4096*360   # Angulo  0+t
    
    deltaAngulo = angulo_actual - angulo_previo 
    deltaTiempo = now1 - now
    
    if abs(deltaAngulo)<180 :
        velocidad = deltaAngulo / deltaTiempo 
        return velocidad / 8000, angulo_previo, angulo_actual # El maximo esta apenas por debajo de 16k.
    else:
        return 0, angulo_previo, angulo_actual

def accel():
    now    = time.time()             # Momento 0
    vel, angulo_previo, angulo_actual  = velocidad()               # vel  0
    
    now1   = time.time()             # Momento 0+t
    vel1, angulo_previo, angulo_actual = velocidad()               # vel  0+t
    
    deltaVel = vel1 - vel 
    deltaTiempo = now1 - now
    
    accel = deltaVel / deltaTiempo 
    return accel / 200
    

def graficar (valorNormalizado, barras=40, negativo=True, display=False):
    if not display:
        if negativo:
            print(barras*"-", "|", barras*"-")
            if valorNormalizado<0:
                print(" "*int(barras*(1+valorNormalizado)),"#"*int(barras*-valorNormalizado),"|")
            else:
                print(" "*barras,"|","#"*int(barras*valorNormalizado))
        else:
            print(barras*2*"-")
            print(" "*int(2*barras*valorNormalizado),"#",)
    else:
        if negativo:
            if valorNormalizado >= 0:
                sen.manage_space("¢"*63+"§"*int(valorNormalizado*64), sen.font, start_page=7, completarLinea=True)
            else:
                sen.manage_space("¢"*int(64*(1+valorNormalizado))+"§"*(63-int(64*(1+valorNormalizado))), sen.font, start_page=7, completarLinea=True)
        else:
            sen.manage_space("§"*int(valorNormalizado*125), sen.font, start_page=7, completarLinea=True)


def stateManager(umbralP = 60, umbralV = 0.15, ventana_tiempo = 0.01, Vflag = False, Pcounter = 0, Vcounter = 0, pendientePos = 0, zona_pasada = 0):

    # Definir la cantidad de triggers en los 360 grados.
    Notriggers = int(360/umbralP)
    ListaTriggers = []

    # El primer trigger de la lista siempre es cero.
    for trigger in range(Notriggers):
        ListaTriggers.append(360/Notriggers*trigger) 
        
    tiempo_inicio = time.time()

    Vmaxima = 0
    Vminima = 0

    valorNormalizado = 0

    # Mientras este dentro de la ventana_tiempo: (Dentro de la ventana_tiempo lo unico que hago es modificar un carry: pendientePos.)
    while time.time() < tiempo_inicio + ventana_tiempo: 
        #print("estoy dentro de la ventana_tiempo")


        # NOTA: angulo_previo se está actualizando todo el tiempo...
        velo, angulo_previo, anguloActual = velocidad()

        Vmaxima = max(Vmaxima,velo)
        Vminima = min(Vminima,velo)

        # Supere la velocidad maxima
        if Vmaxima > umbralV or Vminima < -umbralV:
            # Descarto los cambios que haya hecho en pendientepos: no voy a aumentar la posicion, la velocidad tiene priodidad.

            # NOTA: me da la impresion de que debo salirme del while... no necesito quedarme dentro del intervalo que revisa posicion si no voy a aplicar cambios en posicion...
            pendientePos = 0
        else:
            # Identificar en cual zona estoy (en meddio de qué triggers) 
            # Asi mismo, calcular el valorNormalizado para graficar donde estoy con respecto al trigger.

            for i in range(len (ListaTriggers)-1): # Le resto 1, o me sale un index out of bounds cuando haga ListaTriggers[i+1]
                # valorNormalizado es una interpolacion lineal... es necesario que existan diferentes casos, para usar los valores correctos en la interpolacion.
                
                #Caso 1: Estoy dentro de 2 triggers.
                if ListaTriggers[i] <= anguloActual <= ListaTriggers[i+1]:
                    valorNormalizado = 2 * (anguloActual - ListaTriggers[i]) / (ListaTriggers[i+1] - ListaTriggers[i]) - 1
                    zona_actual = i+1
                    break
                
                #Caso 2: Estoy en el ultimo trigger. 
                if  i == len (ListaTriggers) - 2 and anguloActual >= ListaTriggers[- 1]: # if i == len (ListaTriggers) - 2 (ya llegue al ultimo item del rango)
                    valorNormalizado = 2 / (360 + ListaTriggers[0] - ListaTriggers[len(ListaTriggers) - 1]) * (anguloActual - ListaTriggers[len(ListaTriggers)-1])-1
                    zona_actual = i+2
                    break

                #Caso 3: Este caso nunca se presenta (pero puede ser util) porque el primer trigger de la lista siempre es cero (asi se crea la lista).
                #if i == 0 and anguloActual < ListaTriggers[i]:
                #    valorNormalizado = 2 / (360+ListaTriggers[0] - ListaTriggers[len(ListaTriggers)-1]) * (360 + anguloActual - ListaTriggers[len(ListaTriggers)-1])-1
            
            

            if zona_actual != zona_pasada:
                if zona_pasada == None:
                    zona_pasada = zona_actual
                else: 
                    pendientePos += (zona_actual - zona_pasada)
                    zona_pasada = zona_actual

                                
    # Una vez termina la ventana_tiempo: (aplico los cambios en Pcounter)
    #print("sali de la ventana_tiempo")
    if Vmaxima < umbralV and Vminima > -umbralV: # si NO supere el umbral de velocidad.
        Pcounter += pendientePos
        pendientePos = 0
        Vflag = False
    else: # si SÍ supere el umbral de velocidad
        if Vmaxima > umbralV and Vminima < -umbralV:
            # Caso re tonto. no creo que se presente... (se supera el umbral en ambas direcciones, durante el mismo ventana_tiempo)
            print("el caso re tonto se presentoooooooooooooo!!!!!!!")
            Vflag = False
            Vmaxima = 0
            Vminima = 0
            pendientePos = 0
        elif Vmaxima > umbralV and not Vflag:
            Vflag = True
            Vcounter += 1
            Vmaxima = 0
            Vminima = 0
            pendientePos = 0
        elif Vminima < -umbralV and not Vflag:
            Vflag = True
            Vcounter -= 1
            Vminima = 0
            Vmaxima = 0
            pendientePos = 0

    return Pcounter, Vcounter, Vflag, valorNormalizado, pendientePos, zona_pasada

def actualizar_estado():
    with open('menu.json') as f:
        myJson = json.load(f)
        # Entrar en la carpeta -> "carpetaActual" que se haya guardado en "path"  JSON
        carpetaActual = myJson # Partiendo desde el origen,
        for key in path: # Recorro las carpetas segun "path"
            carpetaActual = carpetaActual[key]
        # Listar opciones:  JSON
        # Si esa "carpetaActual" es un diccionario, puedo buscar los archivos (keys) de esa carpeta...
        if isinstance(carpetaActual, dict):
            disponibles = list(carpetaActual.keys())
        # No estoy en un diccionarrio, no tiene keys(), solo muestro el contenido...
        else:
            disponibles = carpetaActual
    return carpetaActual, disponibles

def leer_brillo():
    with open('config.json') as f:
        myJson = json.load(f)
        
    return myJson['display']['brillo']

def guardar_brillo(nuevo_brillo):
    with open('config.json', 'r') as f:
        config = json.load(f)

    config['display']['brillo'] = int(nuevo_brillo)

    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    
if __name__ == "__main__":

    configurarFiltros() 
    Pcounter1, Vcounter1, Vflag1, pendientePos1, zona_pasada1  = 0, 0 , False, 0, None
    path = []
    disponibles = None
    displayActualizado = False
    PcounterViejo = None
    color=None
    BrilloAntiguo=None
    inicializar={
    "Reloj":False,
    "Presion":False,
    "Humedad":False,
    "Brillo":False
    }


    ultimoMinuto=None
    
    print("Ejecutando...")
    
    # Inicializar display
    sen.init_display(sen.commands)
    sen.clear_display()
    
    
    # Carpeta actual es por definicion, algun "submenu" del JSON.
    # Path es la lista de carpetas a las que he entrado (breadcrumbs). 
    # Disponibles, es la lista de opciones de la carpeta actual.

    with open('menu.json') as f:
        myJson = json.load(f)
           
        while True:
            # La prioridad la tiene el encoder, no el display. siempre empiezo revisando el encoder, para ver si me tengo que mover.
            Pcounter1, Vcounter1, Vflag1, valorNormalizado, pendientePos1, zona_pasada1= stateManager(Pcounter=Pcounter1, Vcounter=Vcounter1, Vflag=Vflag1, pendientePos=pendientePos1, zona_pasada=zona_pasada1)



            # Actualizar los valores disponibles y la carpeta actual del json.
            carpetaActual, disponibles = actualizar_estado()
 
            # Accion! -> El encoder detecta actividad.
            if Vcounter1 != 0:
                if Vcounter1 > 0 and isinstance(disponibles, list):
                    path.append(disponibles[Pcounter1 % len(disponibles)])
                    carpetaActual, disponibles = actualizar_estado()
                elif Vcounter1 < 0 and len(path)>=1 :
                    path.pop()
                    
                    carpetaActual, disponibles = actualizar_estado()

                Vcounter1=0
                # Hay informacion por mostrar (Entre/sali de la carpeta), el display no esta actualizado.
                displayActualizado = False
            
            if Pcounter1 != PcounterViejo:
                # Hay informacion por mostrar (me movi de carpeta), el display no esta actualizado.
                displayActualizado = False



            # Cambiar color del display, negro en la noche, blanco en el dia.
            if time.localtime()[3] >= 6 and time.localtime()[3] < 18:
                if color != "blanco":
                    sen.send_command(0xA7)
                    color="blanco"
            elif color !="negro":
                sen.send_command(0xA6)
                color="negro"


            # Display: Funciones
            # Solo se actualiza el display cuando no esta actualizado. lol

            if isinstance(disponibles, str):

                if disponibles == "mostrar_hora":
                    if ultimoMinuto != time.localtime()[4]:
                        ultimoMinuto = time.localtime()[4]
                        if inicializar["Reloj"]:
                            script.todo(inicializado=True)
                        else:
                            script.todo(inicializado=False)
                            inicializar["Reloj"] = True
                
                if disponibles == "mostrar_presion":
                    if ultimoMinuto != time.localtime()[4]:
                        ultimoMinuto = time.localtime()[4]
                        if inicializar["Presion"]:
                            script.dibujarPresion(inicializado=True)
                        else:
                            script.dibujarPresion(inicializado=False)
                            inicializar["Presion"] = True
                
                if disponibles == "mostrar_humedad":
                    if ultimoMinuto != time.localtime()[4]:
                        ultimoMinuto = time.localtime()[4]
                        if inicializar["Humedad"]:
                            script.dibujarHumedad(inicializado=True)
                        else:
                            script.dibujarHumedad(inicializado=False)
                            inicializar["Humedad"] = True

                if disponibles == "cambiar_brillo":
                    # Se lee el angulo y se asigna a un valor 1-255
                    brilloActual = int((ReadRawAngle() * 255 / 4096 )) + 1
                    #print(brilloActual)
                    
                    if brilloActual != BrilloAntiguo:
                        # Se envia el brillo al displ ay 
                        sen.send_commands_sequence([0x81,brilloActual])
                        BrilloAntiguo = brilloActual
                        cuenta_regresiva_brillo = time.time()


                        if not inicializar['Brillo']:
                            # Si no he enviado nada al display:
                            sen.manage_space("Ajuste el valor y espere 5 segundos: ", sen.calibri16, start_page=0, completarLinea=True, completarPaginas=7)
                            graficar (brilloActual/255, negativo=False, display=True)
                            inicializar["Brillo"]=True
                            
                        else:
                            #En este escenario no escribo nada en display para ahorrar tiempo. sin embargo SI tengo que graficar...
                            graficar (brilloActual/255, negativo=False, display=True)


                    elif time.time() > cuenta_regresiva_brillo + 5:
                        # Solo escribo el brillo en el JSON cuando hayan pasado 5 segundos, y salgo de la carpeta... 
                        guardar_brillo(brilloActual)
                        path.pop()



            # Display: Navegacion por el menu
            # Mostrar en pantalla la lista de opciones: solo se muestran opciones si disponible es una lista.
            elif isinstance(disponibles, list) and not displayActualizado:
                # Ya no estoy en un string, voy a reiniciar los inicializadores+el ultimo minuto
                for inicializador in inicializar:
                    inicializar[inicializador] = None
                ultimoMinuto = None

                for indice in range(len(disponibles)):
                    
                    completarPagi = None
                    if indice == len(disponibles)-1:
                        completarPagi = 7
                    else:
                        completarPagi = False
                    
                    if indice < Pcounter1 % len(disponibles):
                        sen.manage_space(disponibles[indice], sen.calibri16, start_page=2*indice, 
                                        alignement="Left", completarLinea=True, completarPaginas = completarPagi)
                    elif indice == Pcounter1 % len(disponibles):
                        sen.manage_space(disponibles[indice], sen.calibri24, start_page=2*indice, 
                                        alignement="Left", completarLinea=True, completarPaginas = completarPagi)
                    else:
                        sen.manage_space(disponibles[indice], sen.calibri16, start_page=2*indice + 1,
                                        alignement="Left", completarLinea=True, completarPaginas = completarPagi)
                displayActualizado = True
            
            elif isinstance(disponibles, list):       
                graficar (valorNormalizado, display=True)
                
            PcounterViejo = Pcounter1
