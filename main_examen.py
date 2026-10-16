import network, time, ujson
import urequests
from entrada_digital import Entrada_digital
from salida_digital import Salida_Digital
from salida_pwm import SalidaPWM
from entrada_analoga import SenalAnaloga
from htu21d import HTU21D

from machine import Pin, I2C

#pines 
PIN_BOTON = 33
PIN_LED_VERDE = 5
PIN_LED_ROJO = 6
PIN_LED_BLANCO = 7
PIN_RELE = 1
PIN_YL69 = 2

#htu21d 
PIN_SDA = 3
PIN_SCL = 4

#wifi 
WIFI_SSID = 'Redmi Note 13 Pro'
WIFI_PASS = 'chesterteamo123'
BACKEND = 'http://10.207.120.177:5000' 
URL_ENVIO = BACKEND + '/devices/insert'


YL69_SECO = 4095
YL69_MOJADO = 2250

TIEMPO_REBOTE = 50          
TIEMPO_PARPADEO = 500      
TIEMPO_TRANSMISION = 15000 
TIEMPO_LECTURA = 1000

#objetos 
boton = Entrada_digital(PIN_BOTON, modo_pull=Pin.PULL_DOWN)
led_verde = SalidaPWM(PIN_LED_VERDE)
led_rojo = Salida_Digital(PIN_LED_ROJO)
led_blanco = Salida_Digital(PIN_LED_BLANCO)
rele = Salida_Digital(PIN_RELE)
sensor_suelo = SenalAnaloga(PIN_YL69)

#i2c para htu21d
i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=100000)
sensor_ambiente= HTU21D(i2c)

#Esistema comienza en apagado 
sistema_encendido = False

#estado boton PARA ANTIRREBOTE  
boton_anterior = 0
boton_estable = 0
tiempo_cambio_boton = time.ticks_ms()

#estado led blanco PARA PARPADEO SIN SLEEP 
led_blanco_estado = 0
tiempo_led_blanco = time.ticks_ms()

#estado ventilador GUARDA ESTADO ANTERIOR DEL VENTILADOR 
ventilador_encendido = False

#tiempo transmisicion 
tiempo_ultima_transmision = time.ticks_ms()

######funciones 

def apagar_sistema(): #actuadores apagados, pwm del verde en 0 
    led_verde.escribir(0)
    led_rojo.apagar()
    led_blanco.apagar()
    rele.apagar()   

def convertir_humedad_suelo(valor_adc): #lectura adc del yl69 a porcentaje. YL69 ES RESISTIVO. SECO DA VALOR ALTO, MOJADO DA VALOR BAJO
    if YL69_SECO == YL69_MOJADO:
        return 0 # evita dividir por cero 
    
    porcentaje = ( YL69_SECO - valor_adc ) / (YL69_SECO - YL69_MOJADO) * 100
    if porcentaje < 0:
        porcentaje = 0

    if porcentaje > 100:
        porcentaje = 100 #recortan el resultado entre cero y uno 

    return porcentaje

def leer_sensores(): #htu21d duvuelve temperatura y humedad ambiente
    temperatura, humedad_ambiente = sensor_ambiente.measure()
    valor_suelo = sensor_suelo.leer_valor()
    humedad_suelo = convertir_humedad_suelo(valor_suelo)   #lee adc del suelo y lo convierte en %
    return temperatura, humedad_ambiente, humedad_suelo

def controlar_temperatura(temperatura): #control led verde, rojo y ventilador segun temperatura 
    global ventilador_encendido #usa global pq modifica una variable fuera de la funcion 
    if temperatura < 28:
        led_verde.escribir(30)
        led_rojo.apagar()

    elif temperatura < 35:
        led_verde.escribir(70)
        led_rojo.apagar()

    elif temperatura < 40:
        led_verde.escribir(100)
        led_rojo.apagar()

    else:
        led_verde.escribir(0)
        led_rojo.encender()

    #control del ventilador, si no entra en ninguno conserva su valor anterior 
    if temperatura >= 35:
        ventilador_encendido = True

    elif temperatura < 32:
        ventilador_encendido = False

    #aplicar fisicament estado ventilador 

    if ventilador_encendido:
        rele.encender()

    else:
        rele.apagar()

def controlar_humedad (humedad_ambiente, humedad_suelo): #control del led blanco segun humedad ambiente y suelo 
    global led_blanco_estado
    global tiempo_led_blanco

    if humedad_ambiente < 30 and humedad_suelo < 30: #exige las dos condiciones 
        led_blanco.encender()
        led_blanco_estado = 1

    elif humedad_ambiente >= 70 or humedad_suelo >= 70: #con una basta, led tiene que parpadear sin usar sleep 
        ahora = time.ticks_ms() #se toma la hora 

        if time.ticks_diff(ahora, tiempo_led_blanco) >= TIEMPO_PARPADEO: #si ya pasaron 500ms o mas desde el ultimo cambio 
            tiempo_led_blanco = ahora #guardo hora nueva 
            led_blanco_estado = not led_blanco_estado #invierto el estado 

            if led_blanco_estado:
                led_blanco.encender()
            else:
                led_blanco.apagar()

    else: #con cualquier otra condicion  
        led_blanco.apagar()
        led_blanco_estado = 0

def crear_json(temperatura, humedad_ambiente, humedad_suelo): #contruye datos que se enviaran al servidor 
    datos = {
        'sistema': 'ON',
        'temperatura': round(temperatura, 2),
        'humedad_ambiente': round(humedad_ambiente, 2),
        'humedad_suelo': round(humedad_suelo, 2),
        'led_verde_pwm': 0,
        'led_rojo': 0,
        'led_blanco': int(led_blanco_estado), #al parpadear queda como booleano 
        'ventilador': 0
    }

#determinar el pwm real del led verde 
    if temperatura < 28:

        datos["led_verde_pwm"] = 30

    elif temperatura < 35:

        datos["led_verde_pwm"] = 70

    elif temperatura < 40:

        datos["led_verde_pwm"] = 100

    else:

        datos["led_verde_pwm"] = 0

#led rojo 
    if temperatura >= 40:

        datos["led_rojo"] = 1


    # Ventilador
    if ventilador_encendido:

        datos["ventilador"] = 1


    return datos

def conectar_wifi(): #activa interfaz estacion STA IF y si no esta conectada hace CONNECT(SSID, PASS) y espera un while is not connected 
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    if not wifi.isconnected():
        print("Conectando a la red Wi-Fi...")
        wifi.connect(WIFI_SSID, WIFI_PASS)

        while not wifi.isconnected():
            time.sleep_ms(500)
        
    print("Conexión Wi-Fi establecida. Dirección IP:", wifi.ifconfig())
    return wifi

def enviar_datos(datos): #envia los dtos al servidor mediante POST a /devices/insert con header Content-Type: application/json y el body como ujson.dumps(datos)
    try:
        print("Enviando POST al servidor...")   
        respuesta = urequests.post(
            URL_ENVIO,
            data=ujson.dumps(datos),
            headers={"Content-Type": "application/json"}
        )

        print("Codigo HTTP:", respuesta.status_code)
        print("Respuesta del servidor:", respuesta.text)

        respuesta.close()

    except Exception as e:
        print("Error al enviar POST:", e)
# se usa try con ecept para que en caso de que halla un error en el post se imprime el problema y el programa se sigue corriendo
##  INICIALIZACION BUECLE PRINCIPAL 

#apagar todo el sistema al inicio 
apagar_sistema()
print("Sistema apagado.")
print('Estado: APAGADO')

#   conexion wifi
wifi = conectar_wifi()

# bucle principal 
while True:
    lectura_boton = boton.leer() #leer boton 
    ahora = time.ticks_ms() #tomar hora 

    if lectura_boton != boton_anterior: #si lectura distinta a la anterior 
        tiempo_cambio_boton = ahora #reincia cronometro 
        boton_anterior = lectura_boton #reincia boton, es decir la pulsacion actual es el nuevo punto de partida de la siguiente 

    if time.ticks_diff(ahora, tiempo_cambio_boton) >= TIEMPO_REBOTE: #si lectura lleva estable 50ms o mas
        if lectura_boton != boton_estable:
            boton_estable = lectura_boton #se acepta como un cambio real 

            if boton_estable == 1: #si es nuevo estado es 1, presionado 
                sistema_encendido = not sistema_encendido #cambia al estado contrario 

                if sistema_encendido:
                    print('Estado: ENCENDIDO')
                    tiempo_ultima_transmision = time.ticks_ms()  # Reiniciar el tiempo de transmisión al encender el sistema
                    tiempo_led_blanco = time.ticks_ms()  # Reiniciar el tiempo del LED blanco al encender el sistema

                else:
                    print('Estado: APAGADO')
                    ventilador_encendido = False
                    led_blanco_estado = 0
                    apagar_sistema()

    if not sistema_encendido: #si esta apagado, salta al inicio del bucle, no mide no controla no transmite 
        continue

#Si está encendido: lee sensores → controla temperatura → controla humedad → crea el JSON → lo imprime → si pasaron ≥ 15 s desde la última transmisión, lo envía y reinicia el cronómetro.

    temperatura, humedad_ambiente, humedad_suelo = leer_sensores()
    controlar_temperatura(temperatura)
    controlar_humedad(humedad_ambiente, humedad_suelo)
    datos = crear_json(temperatura, humedad_ambiente, humedad_suelo)
    print(ujson.dumps(datos))

    #verificar transmision info cada 15 seg 
    ahora = time.ticks_ms()
    if time.ticks_diff(ahora, tiempo_ultima_transmision) >= TIEMPO_TRANSMISION:
        enviar_datos(datos)
        tiempo_ultima_transmision = ahora