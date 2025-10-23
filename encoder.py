import math
import time
import os
import json
import sen
import script

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
    
def detectarCruce(ang_prev, ang_curr, ListaTriggersxy):
    pass
"""    for trigger in ListaTriggersxy:

        mov = (ang_curr[0]-ang_prev[0], ang_curr[1]-ang_prev[1])   # vector de movimiento
        vec_trigger = (trigger[0]-ang_prev[0], trigger[1]-ang_prev[1])
        productox = mov[0]*vec_trigger[1] - mov[1]*vec_trigger[0]

        

        print(f"de trigger \t {trigger[0]:2f},{trigger[1]:2f}; el producto cruz es \t {productox}")
    print()
    print("\033[2J\033[H", end="")"""

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

def stateManager(umbralP = 120, umbralV = 0.15, intervalo = 0.015, Vflag = False, Pcounter = 0, Vcounter = 0):
    # Definir la cantidad de triggers/2 en los 360 grados.
    Notriggers = int(360/umbralP)
    ListaTriggersxy = []
    ListaTriggers = []

    if Pcounter%2 != 0:    
        for trigger in range(Notriggers):
            ListaTriggersxy.append(degtoxy(360/Notriggers*trigger + 180/Notriggers) )
            ListaTriggers.append(360/Notriggers*trigger + 180/Notriggers) 
            
    else:
        for trigger in range(Notriggers):
            ListaTriggersxy.append(degtoxy(360/Notriggers*trigger) )
            ListaTriggers.append(360/Notriggers*trigger)
    now = time.time()

    Vmaxima = 0
    Vminima = 0
    
    pendientePos = 0
    triggerscambiados = False            
    # Mientras este dentro del intervalo: (Dentro del intervalo lo unico que hago es modificar un carry: pendientePos.)
    while time.time() < now + intervalo: 
        anguloActual = ReadRawAngle() / 4096 * 360
        actualxy = degtoxy(anguloActual)
        velo, angulo_previo, angulo_actual = velocidad()
        
        Vmaxima=max(Vmaxima,velo)
        Vminima=min(Vminima,velo)

        detectarCruce(degtoxy(angulo_previo), degtoxy(angulo_actual), ListaTriggersxy)


        # Supere la velocidad maxima
        if Vmaxima > umbralV or Vminima < -umbralV:
            pendientePos = 0
        else:
            # Verificar si estoy en alguno de los triggersxy
            for trigger in ListaTriggersxy:
                if (abs(actualxy [0] - trigger[0]) < 0.03 and abs(actualxy [1] - trigger[1]) < 0.03):
                    if velo>0:
                        pendientePos+=1    
                    if velo<0: 
                        pendientePos-=1
                    if velo!=0:
                        ListaTriggersxy = []
                        ListaTriggers = []
                        ### Algo me dice que aqui hay un error. Estoy cambiando la posicion de los triggers,
                        ### sin realmente haber aplicado los cambios de aumentar/reducir Pcounter.

                        if Pcounter%2==0:    
                            for trigger in range(Notriggers):
                                ListaTriggersxy.append(degtoxy(360/Notriggers*trigger + 180/Notriggers) )
                                ListaTriggers.append(360/Notriggers*trigger + 180/Notriggers) 
                                
                        else :
                            for trigger in range(Notriggers):
                                ListaTriggersxy.append(degtoxy(360/Notriggers*trigger) )
                                ListaTriggers.append(360/Notriggers*trigger) 
                    
                                
    # Una vez termina el intervalo: (aplico los cambios en Pcounter)
    if Vmaxima < umbralV and Vminima > -umbralV: # si NO supere el umbral de velocidad.
        Pcounter+=pendientePos
        pendientePos=0
        Vflag = False
    else: # si SI supere el umbral de velocidad
        if Vmaxima > umbralV and Vminima < -umbralV:
            # Caso re tonto. no creo que se presente... (se supera el umbral en ambas direcciones, durante el mismo intervalo)
            print("el caso re tonto se presentoooooooooooooo!!!!!!!")
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
      
    #print("\033[2J\033[H", end="")
    #print( f"velo: {velo:3.4f}\t anguloActual: {anguloActual:3.2f}")
    #print( f"Pcounter: {Pcounter}\t Vcounter: {Vcounter}")   
    #graficar (anguloActual/360, negativo=False)
    #
    #if Pcounter%2==0:
    #    for trigger in range(Notriggers):
    #        graficar (360/Notriggers*trigger/360, negativo=False)
    #else:
    #    for trigger in range(Notriggers):
    #        graficar ((360/Notriggers*trigger + 180/Notriggers)/360, negativo=False)
    
        
    for i in range(len (ListaTriggers)-1):
        # valorNormalizado se obtiene con interpolacion lineal...
        if ListaTriggers[i] < anguloActual < ListaTriggers[i+1]:
            valorNormalizado = 2 * (anguloActual - ListaTriggers[i]) / (ListaTriggers[i+1] - ListaTriggers[i]) - 1
            #graficar (valorNormalizado, negativo=True)
            
        if i == len (ListaTriggers)-2 and anguloActual > ListaTriggers[len(ListaTriggers)-1]:
            valorNormalizado = 2 / (360+ListaTriggers[0] - ListaTriggers[len(ListaTriggers)-1]) * (anguloActual - ListaTriggers[len(ListaTriggers)-1])-1
            #graficar (valorNormalizado, negativo=True)
                       
        if i == 0 and anguloActual < ListaTriggers[i]:
            valorNormalizado = 2 / (360+ListaTriggers[0] - ListaTriggers[len(ListaTriggers)-1]) * (360 + anguloActual - ListaTriggers[len(ListaTriggers)-1])-1
            #graficar (valorNormalizado, negativo=True)
            

    return Pcounter, Vcounter, Vflag, valorNormalizado


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
    color=None
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
            # Revisar el encoder, para ver si me tengo que mover.
            # Actualizar contadores segun Encoder.   ENCODER
            Pcounter1, Vcounter1, Vflag1, valorNormalizado = stateManager(Pcounter=Pcounter1, Vcounter=Vcounter1, Vflag=Vflag1)


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
                # hay informacion por mostrar (siguiente entrar/salir de la carpeta), el display no esta actualizado.
                displayActualizado = False
            
            if Pcounter1 != PcounterViejo:
                # hay informacion por mostrar (me movi de carpeta), el display no esta actualizado.
                displayActualizado = False



            # Cambiar color del display, negro en la noche, blanco en el dia.
            if time.localtime()[3] >= 6 and time.localtime()[3] < 18:
                if color != "blanco":
                    sen.init_display([0xA7])
                    color="blanco"
            elif color !="negro":
                sen.init_display([0xA6])
                color="negro"



            # Display: 
            # Se actualiza el display cuando el display no este actualizado. lol
            # No estoy en una carpeta se quiere ejecutar un programa.

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
                    # Se envia el comando 81 + un valor entre 01 y FF
                    brillo = int((ReadRawAngle() * 255 / 4096 )) + 1
                    print(brillo)
                    sen.init_display([0x81,brillo])

                    if not inicializar['Brillo']:
                        sen.manage_space("Brillo: Ajuste el valor y espere: ", sen.calibri16, start_page=0, completarLinea=True, completarPaginas=7)
                        graficar (brillo/255, negativo=False, display=True)
                        inicializar["Brillo"]=True
                    else:
                        graficar (brillo/255, negativo=False, display=True)
                        
                    

                # Al final de dibujar "loquesea" en pantalla, revisar el encoder....
                Pcounter1, Vcounter1, Vflag1, valorNormalizado = stateManager(Pcounter=Pcounter1, Vcounter=Vcounter1, Vflag=Vflag1)


            # Mostrar en pantalla la lista de opciones: solo se muestran opciones si disponible es una lista.

            elif isinstance(disponibles, list) and not displayActualizado:   
                # ya no estoy en un string, voy a reiniciar los inicializadores+el ultimo minuto
                for inicializador in inicializar:
                    inicializar[inicializador]=None
                ultimoMinuto=None



                for indice in range(len(disponibles)):
                    
                    completarPagi = None
                    if indice == len(disponibles)-1:
                        completarPagi=7
                    else:
                        completarPagi=False
                    
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
                nowindicador = time.time()
                
                graficar (valorNormalizado, display=True)
                
            PcounterViejo = Pcounter1

