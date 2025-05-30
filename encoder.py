import math
import time
import os
import json
import sen

#=====================================================================
# Code to read AS5600.  
import smbus2
DEVICE_AS5600 = 0x36 # Default device I2C address
bus = smbus2.SMBus(1)

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
    angle  = ReadAngle()/4096*360   # Angulo  0
    
    now1   = time.time()               # Momento 0+t
    angle1 = ReadAngle()/4096*360   # Angulo  0+t
    
    deltaAngulo = angle1 - angle 
    deltaTiempo = now1 - now
    
    if abs(deltaAngulo)<180 :
        velocidad = deltaAngulo / deltaTiempo 
        return velocidad / 8000 # El maximo esta apenas por debajo de 16k.
    else:
        return 0

def accel():
    now    = time.time()             # Momento 0
    vel  = velocidad()               # vel  0
    
    now1   = time.time()             # Momento 0+t
    vel1 = velocidad()               # vel  0+t
    
    deltaVel = vel1 - vel 
    deltaTiempo = now1 - now
    
    accel = deltaVel / deltaTiempo 
    return accel / 200
    


def graficar (valorNormalizado, barras=40, negativo=True):
    if negativo:
        print(barras*"-", "|", barras*"-")
        if valorNormalizado<0:
            print(" "*int(barras*(1+valorNormalizado)),"#"*int(barras*-valorNormalizado),"|")
        else:
            print(" "*barras,"|","#"*int(barras*valorNormalizado))
    else:
        print(barras*2*"-")
        #print("#"*int(2*barras*valorNormalizado))
        print(" "*int(2*barras*valorNormalizado),"#",)
        

def stateManager(umbralP = 120, umbralV = 0.15, intervalo = 0.05, Vflag=False, Pcounter = 0, Vcounter = 0):
    # Definir la cantidad de triggers/2 en los 365 grados.
    Notriggers = int(360/umbralP)
    ListaTriggers = []

    if Pcounter%2!=0:    
        for trigger in range(Notriggers):
            ListaTriggers.append(degtoxy(360/Notriggers*trigger + 180/Notriggers) )
    else :
        for trigger in range(Notriggers):
            ListaTriggers.append(degtoxy(360/Notriggers*trigger) )
    now = time.time()

    Vmaxima=0
    Vminima=0
    
    pendientePos=0
                    
    # Mientras este dentro del intervalo: (dentro, lo unico que hago es modificar pendientePos.)
    while time.time() < now + intervalo: 
        anguloActual = ReadRawAngle() / 4096 * 360
        actualxy = degtoxy(anguloActual)
        velo = velocidad()
        
        Vmaxima=max(Vmaxima,velo)
        Vminima=min(Vminima,velo)
        
        # Supere la velocidad maxima
        if Vmaxima > umbralV or Vminima < -umbralV:
            pendientePos = 0
        else:
            # Verificar si estoy en alguno de los triggers
            for trigger in ListaTriggers:
                if (abs(actualxy [0] - trigger[0]) < 0.02 and abs(actualxy [1] - trigger[1]) < 0.02):
                    if velo>0:
                        pendientePos+=1    
                    elif velo<0: 
                        pendientePos-=1
                    if velo!=0:
                        ListaTriggers = []

                        ### Algo me dice que aqui hay un error. Estoy cambiando la posicion de los triggers,
                        ### sin realmente haber aplicado los cambios de aumentar/reducir Pcounter.
                        if Pcounter%2==0:    
                            for trigger in range(Notriggers):
                                ListaTriggers.append(degtoxy(360/Notriggers*trigger + 180/Notriggers) )
                        else :
                            for trigger in range(Notriggers):
                                ListaTriggers.append(degtoxy(360/Notriggers*trigger) )
                                
    # Una vez termina el intervalo: (aplico los cambios en Pcounter)
    if Vmaxima < umbralV and Vminima > -umbralV: # si NO supere el umbral de velocidad.
        Pcounter+=pendientePos
        pendientePos=0
        Vflag = False
    else: # si SI supere el umbral de velocidad
        if Vmaxima > umbralV and Vminima < -umbralV:
            # Caso re tonto. no creo que se presente... (se supera el umbral en ambas direcciones, durante el mismo intervalo)
            Vflag = False
            Vmaxima=0
            Vminima=0
            pendientePos=0
        elif Vmaxima > umbralV and not Vflag:
            Vflag = True
            Vcounter+=1
            Vmaxima=0
            Vminima=0
            pendientePos=0
        elif Vminima < -umbralV and not Vflag:
            Vflag = True
            Vcounter-=1
            Vminima=0
            Vmaxima=0
            pendientePos=0
    return Pcounter, Vcounter, Vflag

    """   
    print("\033[2J\033[H", end="")
    print( f"velo: {velo:3.4f}\t anguloActual: {anguloActual:3.2f}")
    print( f"Pcounter: {Pcounter}\t Vcounter: {Vcounter}")   
    graficar (anguloActual/360, negativo=False)
    if Pcounter%2==0:
        for trigger in range(Notriggers):
            graficar (360/Notriggers*trigger/360, negativo=False)
    else:
        for trigger in range(Notriggers):
            graficar ((360/Notriggers*trigger + 180/Notriggers)/360, negativo=False)
    """

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


    
if __name__ == "__main__":
    configurarFiltros() 
    Pcounter1, Vcounter1, Vflag1 = 0, 0 , False
    path = []
    disponibles = None
    displayActualizado = False
    PcounterViejo = 0
    
    print("Ejecutando...")
    
    # Inicializar display
    sen.init_display(sen.commands)
    sen.clear_display()
    
    
    # Carpeta actual es por definicion, algun "submenu" del JSON.
    # Path es la lista de carpetas a las que he entrado.
    # Disponibles, es la lista de opciones de la carpeta actual.

    with open('menu.json') as f:
        myJson = json.load(f)
           
        while True:

            # Actualizar contadores segun Encoder.   ENCODER
            Pcounter1, Vcounter1, Vflag1 = stateManager(Pcounter=Pcounter1, Vcounter=Vcounter1, Vflag=Vflag1)


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
                #sen.clear_display()
                displayActualizado = False
            if Pcounter1 != PcounterViejo:
                #sen.clear_display()
                displayActualizado = False


            # Display:
            if isinstance(disponibles, str) and displayActualizado == False: 
                if disponibles=="mostrar_hora":
                    sen.manage_space(f"{time.localtime()[3]:02d}:{time.localtime()[4]:02d}", sen.calibri32, start_page=0, alignement="Center", completar=True)
                    displayActualizado = False
                    Pcounter1, Vcounter1, Vflag1 = stateManager(Pcounter=Pcounter1, Vcounter=Vcounter1, Vflag=Vflag1)
                elif disponibles=="mostrar_temperatura":
                    displayActualizado = True
                    
            elif isinstance(disponibles, list) and displayActualizado == False:
                for indice in range(len(disponibles)):
                    
                    if indice < Pcounter1 % len(disponibles):
                        sen.manage_space(disponibles[indice], sen.calibri16, start_page=2*indice, alignement="Left", completar=True)
                    elif indice == Pcounter1 % len(disponibles):
                        sen.manage_space(disponibles[indice], sen.calibri24, start_page=2*indice, alignement="Left", completar=True)
                    else:
                        sen.manage_space(disponibles[indice], sen.calibri16, start_page=2*indice + 1 , alignement="Left", completar=True)
                    
                    displayActualizado = True

            PcounterViejo = Pcounter1


   