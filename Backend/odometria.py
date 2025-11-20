import time
import struct
import numpy as np
import smbus2 as smbus
import math

# ============================================================================
# CONFIGURACION CON MANEJO DE ERRORES
# ============================================================================

def inicializar_bus():
    """Inicializa el bus I2C con manejo de errores"""
    try:
        bus = smbus.SMBus(1)
        bus.write_byte_data(0x34, 0x14, 3)
        time.sleep(0.1)
        bus.write_byte_data(0x34, 0x15, 0)
        time.sleep(0.1)
        return bus
    except Exception as e:
        print(f"\nâŒ ERROR al inicializar I2C: {e}")
        print("\nSOLUCIONES:")
        print("1. Desconecta y reconecta la bateria")
        print("2. Ejecuta: python3 resetear_i2c.py")
        print("3. Reinicia el robot: sudo reboot")
        return None

bus = inicializar_bus()
if bus is None:
    exit(1)

DIRECCION = 0x34
PULSOS_POR_REV = 1560

# Parametros cinematicos
R = 0.048
l1 = 0.097
l2 = 0.109

W = (1 / R) * np.array([
    [1, -1, (l1 + l2)],
    [1,  1, (l1 + l2)],
    [1,  1, -(l1 + l2)],
    [1, -1, -(l1 + l2)]
])

# Matriz cinematica directa (para odometrÃ­a)
W_inv = np.linalg.pinv(W)

V_MAX = 50
PWM_MAX = 100
TIEMPO_MIN_I2C = 0.02

# ============================================================================
# FUNCIONES I2C CON REINTENTOS Y PROTECCION
# ============================================================================

ultimo_tiempo_i2c = time.time()

def esperar_i2c():
    """Asegura tiempo mÃ­nimo entre comandos I2C"""
    global ultimo_tiempo_i2c
    tiempo_transcurrido = time.time() - ultimo_tiempo_i2c
    if tiempo_transcurrido < TIEMPO_MIN_I2C:
        time.sleep(TIEMPO_MIN_I2C - tiempo_transcurrido)
    ultimo_tiempo_i2c = time.time()

def escribir_i2c_seguro(registro, datos, max_intentos=2):
    """Escribe en I2C con reintentos y protecciÃ³n contra saturaciÃ³n"""
    esperar_i2c()
    
    for intento in range(max_intentos):
        try:
            if isinstance(datos, list):
                bus.write_i2c_block_data(DIRECCION, registro, datos)
            else:
                bus.write_byte_data(DIRECCION, registro, datos)
            return True
        except Exception as e:
            if intento < max_intentos - 1:
                time.sleep(0.05)
            else:
                if intento == max_intentos - 1:
                    print(f"\nâš ï¸ Error I2C: {e}")
                return False
    return False

def leer_i2c_seguro(registro, longitud, max_intentos=2):
    """Lee de I2C con reintentos y protecciÃ³n"""
    esperar_i2c()
    
    for intento in range(max_intentos):
        try:
            return bus.read_i2c_block_data(DIRECCION, registro, longitud)
        except Exception as e:
            if intento < max_intentos - 1:
                time.sleep(0.05)
            else:
                if intento == max_intentos - 1:
                    print(f"\nâš ï¸ Error I2C: {e}")
                return None
    return None

# ============================================================================
# ODOMETRIA
# ============================================================================

class Odometria:
    """Sistema de odometrÃ­a usando encoders de 4 ruedas"""
    def _init_(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        
        self.tiempo_anterior = time.time()
        self.habilitada = False  # Deshabilitada por defecto
        
    def habilitar(self):
        """Habilita odometrÃ­a"""
        self.habilitada = True
        self.reset()
        
    def deshabilitar(self):
        """Deshabilita odometrÃ­a"""
        self.habilitada = False
        
    def actualizar(self, vel_reales):
        """Actualiza posiciÃ³n usando velocidades de ruedas
        
        Args:
            vel_reales: [FL, FR, RL, RR] en rad/s
        """
        if not self.habilitada:
            return False
            
        tiempo_actual = time.time()
        dt = tiempo_actual - self.tiempo_anterior
        
        if dt <= 0 or dt > 1.0:
            self.tiempo_anterior = tiempo_actual
            return False
        
        # CinemÃ¡tica directa: velocidades ruedas -> velocidades robot
        vel_robot = np.dot(W_inv, vel_reales)
        # Invertir solo X e Y (adelante y derecha estaban negativos)
        vx = -vel_robot[1]
        vy = -vel_robot[0]
        omega = vel_robot[2]
        
        # Filtrar valores absurdos
        if abs(vx) > 2.0 or abs(vy) > 2.0 or abs(omega) > 10.0:
            self.tiempo_anterior = tiempo_actual
            return False
        
        # Integrar velocidades (marco global)
        self.x += (vx * math.cos(self.theta) - vy * math.sin(self.theta)) * dt
        self.y += (vx * math.sin(self.theta) + vy * math.cos(self.theta)) * dt
        self.theta += omega * dt
        
        # Normalizar theta a [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
        
        self.tiempo_anterior = tiempo_actual
        return True
    
    def reset(self, x=0, y=0, theta=0):
        """Reinicia odometrÃ­a"""
        self.x = x
        self.y = y
        self.theta = theta
        self.tiempo_anterior = time.time()
    
    def get_pose(self):
        """Retorna posiciÃ³n actual"""
        return self.x, self.y, self.theta

# ============================================================================
# CONTROLADOR PID
# ============================================================================

class PIDController:
    """Controlador PID para una rueda"""
    def _init_(self, kp=1.2, ki=0.4, kd=0.05, limite=100):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limite = limite
        
        self.error_anterior = 0
        self.integral = 0
        self.tiempo_anterior = time.time()
        
    def calcular(self, setpoint, medicion):
        """Calcula salida PID"""
        tiempo_actual = time.time()
        dt = tiempo_actual - self.tiempo_anterior
        
        if dt <= 0:
            dt = 0.01
        
        error = setpoint - medicion
        
        P = self.kp * error
        
        self.integral += error * dt
        self.integral = np.clip(self.integral, -30, 30)
        I = self.ki * self.integral
        
        derivada = (error - self.error_anterior) / dt
        D = self.kd * derivada
        
        salida = P + I + D
        salida = np.clip(salida, -self.limite, self.limite)
        
        self.error_anterior = error
        self.tiempo_anterior = tiempo_actual
        
        return salida
    
    def reset(self):
        """Reinicia el controlador"""
        self.error_anterior = 0
        self.integral = 0
        self.tiempo_anterior = time.time()


class ControladorVelocidad:
    """Sistema de control de velocidad con 4 PIDs y odometrÃ­a integrada"""
    def _init_(self):
        self.pids = [
            PIDController(kp=1.2, ki=0.4, kd=0.05),  # FL
            PIDController(kp=1.2, ki=0.4, kd=0.05),  # FR
            PIDController(kp=1.2, ki=0.4, kd=0.05),  # RL
            PIDController(kp=1.2, ki=0.4, kd=0.05)   # RR
        ]
        
        # Inicializar con valores reales de encoders
        datos_iniciales = leer_i2c_seguro(0x3C, 16)
        if datos_iniciales:
            self.enc_anterior = list(struct.unpack('iiii', bytes(datos_iniciales)))
        else:
            self.enc_anterior = [0, 0, 0, 0]
        
        self.tiempo_anterior = time.time()
        self.activo = True
        self.contador_lecturas = 0
        
        # OdometrÃ­a integrada
        self.odometria = Odometria()
        
    def leer_velocidades_reales(self):
        """Lee velocidades reales de las ruedas"""
        datos = leer_i2c_seguro(0x3C, 16)
        if datos is None:
            self.activo = False
            return [0, 0, 0, 0]
        
        try:
            enc_actual = list(struct.unpack('iiii', bytes(datos)))
            tiempo_actual = time.time()
            dt = tiempo_actual - self.tiempo_anterior
            
            # Si dt es muy pequeÃ±o o muy grande, usar valor anterior pero actualizar tiempo
            if dt <= 0:
                dt = 0.01
            elif dt > 1.0:
                # Primera lectura o tiempo muy largo, usar encoders actuales
                self.enc_anterior = enc_actual
                self.tiempo_anterior = tiempo_actual
                return [0, 0, 0, 0]
            
            velocidades = []
            for i in range(4):
                delta = enc_actual[i] - self.enc_anterior[i]
                vel_rad_s = (delta / dt) * (2 * np.pi / PULSOS_POR_REV)
                if abs(vel_rad_s) > 200:
                    vel_rad_s = 0
                velocidades.append(vel_rad_s)
            
            self.enc_anterior = enc_actual
            self.tiempo_anterior = tiempo_actual
            self.contador_lecturas += 1
            
            # Actualizar odometrÃ­a si estÃ¡ habilitada
            self.odometria.actualizar(velocidades)
            
            return velocidades
        except Exception as e:
            print(f"\nâš ï¸ Error procesando encoders: {e}")
            return [0, 0, 0, 0]
    
    def calcular_velocidades_deseadas(self, vx, vy, omega):
        """Cinematica inversa"""
        V = np.array([vx, vy, omega])
        velocidades = np.dot(W, V)
        
        factor = np.max(np.abs(velocidades)) / V_MAX if np.max(np.abs(velocidades)) > V_MAX else 1
        if factor > 1:
            velocidades /= factor
        
        return velocidades
    
    def controlar(self, vx, vy, omega):
        """Control PID completo"""
        if not self.activo:
            return [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]
        
        # Calcular velocidades deseadas
        vel_deseadas = self.calcular_velocidades_deseadas(vx, vy, omega)
        
        # Leer velocidades reales
        vel_reales = self.leer_velocidades_reales()
        
        # Calcular PWM base (feedforward)
        velocidades = vel_deseadas.copy()
        velocidades[1] *= -1
        velocidades[2] *= -1
        pwm_base = (velocidades / V_MAX) * PWM_MAX
        pwm_base = np.clip(pwm_base, -PWM_MAX, PWM_MAX)
        
        # Aplicar PID (feedback)
        pwm_final = []
        for i in range(4):
            vel_deseada = vel_deseadas[i]
            if i == 1 or i == 2:
                vel_deseada *= -1
            
            correccion = self.pids[i].calcular(vel_deseada, vel_reales[i])
            pwm = pwm_base[i] + correccion
            pwm = int(np.clip(pwm, -PWM_MAX, PWM_MAX))
            pwm_final.append(pwm)
        
        return pwm_final, vel_deseadas, vel_reales
    
    def enviar_pwm(self, pwm):
        """Envia PWM de forma segura"""
        if not self.activo:
            return False
        return escribir_i2c_seguro(0x33, pwm)
    
    def reset(self):
        """Reinicia PIDs y odometrÃ­a"""
        for pid in self.pids:
            pid.reset()
        datos = leer_i2c_seguro(0x3C, 16)
        if datos:
            self.enc_anterior = list(struct.unpack('iiii', bytes(datos)))
        self.tiempo_anterior = time.time()
        self.contador_lecturas = 0
        
        # Resetear odometrÃ­a si estÃ¡ habilitada
        if self.odometria.habilitada:
            self.odometria.reset()

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parar():
    """Detiene motores de forma segura"""
    for intento in range(3):
        if escribir_i2c_seguro(0x33, [0, 0, 0, 0]):
            return True
        time.sleep(0.1)
    return False

def leer_bateria():
    """Lee bateria de forma segura"""
    datos = leer_i2c_seguro(0x00, 2)
    if datos:
        voltaje = (datos[0] + (datos[1] << 8)) / 1000.0
        if 5.0 < voltaje < 15.0:
            return voltaje
    return 0.0

# ============================================================================
# PROGRAMA PRINCIPAL
# ============================================================================

controlador = ControladorVelocidad()

print("\nInicializando sistema...")
time.sleep(0.2)
controlador.reset()
time.sleep(0.2)

bateria_inicial = leer_bateria()

print("\n" + "="*90)
print("              CONTROL PID + ODOMETRIA - ROBOT OMNIDIRECCIONAL")
print("="*90)
print("\nCARACTERISTICAS:")
print("  âœ“ Valores PID: Kp=1.2, Ki=0.4, Kd=0.05")
print("  âœ“ ProtecciÃ³n I2C anti-saturaciÃ³n")
print("  âœ“ Direcciones CORREGIDAS: A=Izq âœ“, D=Der âœ“")
print("  âœ“ OdometrÃ­a integrada (deshabilitada por defecto)")
print(f"\nðŸ”‹ BaterÃ­a: {bateria_inicial:.2f}V", end="")
if bateria_inicial < 10.5:
    print(" âš ï¸  BATERIA BAJA - Carga recomendada")
elif bateria_inicial < 11.0:
    print(" âš¡ BaterÃ­a media")
else:
    print(" âœ“ BaterÃ­a OK")
print("="*90)
print("\nCOMANDOS:")
print("  W=Adelante  S=Atras  A=Izqâœ“  D=Derâœ“  Q=Giroâ†º  E=Giroâ†»")
print("  1=Lento(0.3)  2=Medio(0.5)  3=Rapido(0.7)")
print("  P=Ajustar PID  I=Info  O=Odom ON/OFF  R=Reset Pose  H=Ir a HOME  X=STOP  Z=SALIR")
print("="*90)

velocidad = 0.5
intervalo_display = 0.15

try:
    while True:
        if not controlador.activo:
            print("\nâŒ Controlador desactivado por errores I2C")
            print("SOLUCION: Desconecta y reconecta la bateria")
            break
        
        cmd = input("\nComando: ").strip().lower()
        
        if cmd == 'z':
            break
        elif cmd == 'o':
            # Toggle odometrÃ­a
            if controlador.odometria.habilitada:
                controlador.odometria.deshabilitar()
                print("ðŸ“ OdometrÃ­a DESHABILITADA")
            else:
                controlador.odometria.habilitar()
                print("ðŸ“ OdometrÃ­a HABILITADA")
                x, y, theta = controlador.odometria.get_pose()
                print(f"   PosiciÃ³n inicial: x={x:.3f}m, y={y:.3f}m, Î¸={math.degrees(theta):.1f}Â°")
            continue
        elif cmd == 'r':
            # Reset odometrÃ­a
            if controlador.odometria.habilitada:
                controlador.odometria.reset()
                print("ðŸ“ OdometrÃ­a RESETEADA a (0, 0, 0Â°)")
            else:
                print("âš ï¸  OdometrÃ­a deshabilitada. Usa 'O' para habilitar.")
            continue
        elif cmd == 'h':
            # Ir a home (0, 0)
            if not controlador.odometria.habilitada:
                print("âš ï¸  OdometrÃ­a deshabilitada. Habilita con 'O' primero.")
                continue
            
            x_actual, y_actual, theta_actual = controlador.odometria.get_pose()
            print(f"\nðŸ  Regresando a HOME (0, 0)")
            print(f"   PosiciÃ³n actual: x={x_actual:.3f}m, y={y_actual:.3f}m")
            print(f"   Distancia: {math.sqrt(x_actual*2 + y_actual*2):.3f}m")
            
            # Calcular direcciÃ³n al origen
            distancia = math.sqrt(x_actual*2 + y_actual*2)
            
            if distancia < 0.05:
                print("   âœ“ Ya estÃ¡s en HOME")
                continue
            
            # Navegar hacia el origen
            print("\n   Navegando...")
            tiempo_inicio = time.time()
            timeout = 60  # 60 segundos mÃ¡ximo
            
            # Reset PIDs pero NO odometrÃ­a
            for pid in controlador.pids:
                pid.reset()
            time.sleep(0.1)
            
            tolerancia = 0.1  # 10cm
            
            while time.time() - tiempo_inicio < timeout:
                x_actual, y_actual, theta_actual = controlador.odometria.get_pose()
                distancia = math.sqrt(x_actual*2 + y_actual*2)
                
                if distancia < tolerancia:
                    print(f"\n   âœ“ HOME alcanzado!")
                    parar()
                    break
                
                # Calcular velocidades hacia el origen
                # Velocidad proporcional a la distancia
                vel_mag = min(0.3, distancia * 0.5)  # Max 0.3 m/s
                
                # DirecciÃ³n hacia origen en marco global
                angulo_objetivo = math.atan2(-y_actual, -x_actual)
                
                # Velocidades en marco del robot
                vx = vel_mag * math.cos(angulo_objetivo - theta_actual)
                vy = vel_mag * math.sin(angulo_objetivo - theta_actual)
                omega = 0  # Sin rotaciÃ³n
                
                # Limitar velocidades
                vx = np.clip(vx, -0.3, 0.3)
                vy = np.clip(vy, -0.3, 0.3)
                
                # Aplicar control
                pwm, _, _ = controlador.controlar(vx, vy, omega)
                if not controlador.enviar_pwm(pwm):
                    print("\n   âŒ Error I2C")
                    break
                
                # Mostrar progreso cada segundo
                if int(time.time() - tiempo_inicio) != int(time.time() - tiempo_inicio - 0.1):
                    print(f"\r   Distancia restante: {distancia*100:.1f}cm", end='', flush=True)
                
                time.sleep(0.1)
            else:
                print(f"\n   âš ï¸  Timeout - no alcanzÃ³ HOME")
            
            parar()
            x_final, y_final, theta_final = controlador.odometria.get_pose()
            print(f"   PosiciÃ³n final: x={x_final:.3f}m, y={y_final:.3f}m, Î¸={math.degrees(theta_final):.1f}Â°")
            continue
        elif cmd == 'p':
            # Ajustar PID
            print("\n" + "="*60)
            print("  AJUSTE MANUAL DE PID")
            print("="*60)
            print(f"\n  Valores actuales:")
            print(f"    Kp = {controlador.pids[0].kp}")
            print(f"    Ki = {controlador.pids[0].ki}")
            print(f"    Kd = {controlador.pids[0].kd}")
            print("\n  Sugerencias:")
            print("    - Error alto? â†’ Aumentar Kp")
            print("    - No llega? â†’ Aumentar Ki")
            print("    - Oscila? â†’ Reducir Kp, aumentar Kd")
            print("    - Presiona Enter para mantener valor")
            print()
            
            try:
                kp_input = input(f"  Nuevo Kp (actual {controlador.pids[0].kp}): ").strip()
                ki_input = input(f"  Nuevo Ki (actual {controlador.pids[0].ki}): ").strip()
                kd_input = input(f"  Nuevo Kd (actual {controlador.pids[0].kd}): ").strip()
                
                nuevo_kp = float(kp_input) if kp_input else controlador.pids[0].kp
                nuevo_ki = float(ki_input) if ki_input else controlador.pids[0].ki
                nuevo_kd = float(kd_input) if kd_input else controlador.pids[0].kd
                
                for pid in controlador.pids:
                    pid.kp = nuevo_kp
                    pid.ki = nuevo_ki
                    pid.kd = nuevo_kd
                
                print(f"\n  âœ“ PID actualizado:")
                print(f"    Kp = {nuevo_kp}")
                print(f"    Ki = {nuevo_ki}")
                print(f"    Kd = {nuevo_kd}")
                print("="*60)
                
                controlador.reset()
                
            except ValueError:
                print("  âŒ Valores invÃ¡lidos")
            
            continue
        elif cmd == 'i':
            # Info del sistema
            print("\n" + "="*60)
            print("  ðŸ“Š INFORMACION DEL SISTEMA")
            print("="*60)
            print(f"\n  PID:")
            print(f"    Kp = {controlador.pids[0].kp:.3f}")
            print(f"    Ki = {controlador.pids[0].ki:.3f}")
            print(f"    Kd = {controlador.pids[0].kd:.3f}")
            print(f"\n  Estado PIDs:")
            nombres = ["FL", "FR", "RL", "RR"]
            for i, pid in enumerate(controlador.pids):
                print(f"    {nombres[i]}: I={pid.integral:.2f}, E_ant={pid.error_anterior:.2f}")
            print(f"\n  Lecturas: {controlador.contador_lecturas} ciclos")
            bat = leer_bateria()
            print(f"  ðŸ”‹ BaterÃ­a: {bat:.2f}V")
            
            if controlador.odometria.habilitada:
                x, y, theta = controlador.odometria.get_pose()
                print(f"\n  ðŸ“ OdometrÃ­a: HABILITADA")
                print(f"    x = {x:.3f} m")
                print(f"    y = {y:.3f} m")
                print(f"    Î¸ = {math.degrees(theta):.1f}Â°")
            else:
                print(f"\n  ðŸ“ OdometrÃ­a: DESHABILITADA (usa 'O')")
            print("="*60)
            continue
        elif cmd == 'x':
            parar()
            # NO resetear odometrÃ­a, solo PIDs
            for pid in controlador.pids:
                pid.reset()
            print(">>> DETENIDO")
            if controlador.odometria.habilitada:
                x, y, theta = controlador.odometria.get_pose()
                print(f"    PosiciÃ³n actual: x={x:.3f}m, y={y:.3f}m, Î¸={math.degrees(theta):.1f}Â°")
            continue
        elif cmd == '1':
            velocidad = 0.3
            print(f">>> Velocidad: {velocidad} m/s (Lento)")
            continue
        elif cmd == '2':
            velocidad = 0.5
            print(f">>> Velocidad: {velocidad} m/s (Medio)")
            continue
        elif cmd == '3':
            velocidad = 0.7
            print(f">>> Velocidad: {velocidad} m/s (RÃ¡pido)")
            continue
        
        # DIRECCIONES CORREGIDAS âœ“
        movimientos = {
            'w': (velocidad, 0, 0, "ADELANTE"),
            's': (-velocidad, 0, 0, "ATRAS"),
            'a': (0, -velocidad, 0, "IZQUIERDA âœ“"),  # CORREGIDO
            'd': (0, velocidad, 0, "DERECHA âœ“"),      # CORREGIDO
            'q': (0, 0, -2.0, "GIRO â†º"),
            'e': (0, 0, 2.0, "GIRO â†»"),
        }
        
        if cmd not in movimientos:
            print("Comando invalido")
            continue
        
        vx, vy, omega, nombre = movimientos[cmd]
        print(f"\n>>> {nombre} (vx={vx:.2f}, vy={vy:.2f}, Ï‰={omega:.2f})")
        
        # Reset PIDs pero NO odometrÃ­a
        for pid in controlador.pids:
            pid.reset()
        time.sleep(0.1)
        
        # Header dinÃ¡mico segÃºn odometrÃ­a
        if controlador.odometria.habilitada:
            print("\n  FL: Des|Real | FR: Des|Real | RL: Des|Real | RR: Des|Real | Odom(x,y,Î¸)")
        else:
            print("\n  FL: Des|Real | FR: Des|Real | RL: Des|Real | RR: Des|Real | Bat  ")
        print("  " + "-" * 85)
        
        errores = [[], [], [], []]
        ultimo_display = time.time()
        bateria_cache = bateria_inicial
        
        for i in range(50):
            pwm, vel_des, vel_real = controlador.controlar(vx, vy, omega)
            
            if not controlador.enviar_pwm(pwm):
                print("\n\nâŒ Error PWM")
                break
            
            if i % 10 == 0:
                bat_nueva = leer_bateria()
                if bat_nueva > 0:
                    bateria_cache = bat_nueva
            
            vd = [vel_des[0], -vel_des[1], -vel_des[2], vel_des[3]]
            
            if i > 10:
                for j in range(4):
                    error = abs(vd[j] - vel_real[j])
                    if error < 50:
                        errores[j].append(error)
            
            tiempo_actual = time.time()
            if tiempo_actual - ultimo_display >= intervalo_display:
                info = f"  {vd[0]:4.1f}|{vel_real[0]:4.1f} | {vd[1]:4.1f}|{vel_real[1]:4.1f} | "
                info += f"{vd[2]:4.1f}|{vel_real[2]:4.1f} | {vd[3]:4.1f}|{vel_real[3]:4.1f} | "
                
                if controlador.odometria.habilitada:
                    x, y, theta = controlador.odometria.get_pose()
                    info += f"{x:.2f},{y:.2f},{math.degrees(theta):.0f}Â°"
                else:
                    info += f"{bateria_cache:.1f}V"
                
                print(f'\r{info}', end='', flush=True)
                ultimo_display = tiempo_actual
            
            time.sleep(0.1)
        
        print("\n")
        if any(len(e) > 0 for e in errores):
            print("  ðŸ“Š ESTADISTICAS:")
            nombres = ["FL", "FR", "RL", "RR"]
            for j in range(4):
                if errores[j] and len(errores[j]) > 5:
                    error_medio = np.mean(errores[j])
                    error_max = np.max(errores[j])
                    
                    if error_medio < 2:
                        estado = "âœ“ EXCELENTE"
                    elif error_medio < 4:
                        estado = "âœ“ BUENO"
                    elif error_medio < 8:
                        estado = "âš  ACEPTABLE"
                    else:
                        estado = "âŒ REVISAR"
                    
                    print(f"     {nombres[j]}: Error={error_medio:.2f} rad/s (max:{error_max:.2f}) {estado}")
        
        # Mostrar pose final si odometrÃ­a activa
        if controlador.odometria.habilitada:
            x, y, theta = controlador.odometria.get_pose()
            print(f"\n  ðŸ“ Pose final: x={x:.3f}m, y={y:.3f}m, Î¸={math.degrees(theta):.1f}Â°")
        print()

except KeyboardInterrupt:
    print("\n\nâš ï¸ Interrumpido")

finally:
    print("\nDeteniendo motores...")
    parar()
    time.sleep(0.2)
    bateria_final = leer_bateria()
    print("\n" + "="*90)
    print("âœ“ Robot detenido")
    if bateria_final > 0:
        print(f"ðŸ”‹ BaterÃ­a final: {bateria_final:.2f}V")
        if bateria_inicial > 0 and bateria_final > 0:
            caida = bateria_inicial - bateria_final
            if caida > 2.0:
                print(f"âš ï¸  CaÃ­da alta ({caida:.1f}V) - Revisar baterÃ­a")
    
    if controlador.odometria.habilitada:
        x, y, theta = controlador.odometria.get_pose()
        print(f"ðŸ“ Pose final: x={x:.3f}m, y={y:.3f}m, Î¸={math.degrees(theta):.1f}Â°")
    
    print("="*90)