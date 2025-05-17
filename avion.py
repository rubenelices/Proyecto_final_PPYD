"""
avion.py - Cliente de avión para sistema de control aéreo distribuido
"""

import asyncio
import json
import logging
import socket
import sys
import time
import uuid
from random import choice, randint

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Avión %(id_vuelo)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Constantes
HOST = '127.0.0.1'
PORT = 5000


class Avion:
    """Cliente que simula un avión solicitando operaciones a la torre de control"""
    
    def __init__(self, id_vuelo=None, tipo_operacion=None):
        """
        Inicializa un nuevo avión
        
        Args:
            id_vuelo: Identificador único del vuelo (si es None, se genera uno aleatorio)
            tipo_operacion: Tipo de operación a realizar ('aterrizaje' o 'despegue')
        """
        # Si no se especifica el ID, generamos uno aleatorio
        self.id_vuelo = id_vuelo or self._generar_id_vuelo()
        
        # Si no se especifica el tipo de operación, elegimos uno aleatorio
        self.tipo_operacion = tipo_operacion or choice(['aterrizaje', 'despegue'])
        
        # Variables para medir tiempos
        self.tiempo_inicio = None
        self.tiempo_autorizacion = None
        self.tiempo_completado = None
        
        # Identificador extra para aerolíneas (para mejor visualización)
        self.aerolinea = choice(['IB', 'AA', 'DL', 'UA', 'BA', 'LH', 'AF'])
        
        # Configurar logging con el ID del vuelo
        self.logger = logging.getLogger(f"Avion-{self.id_vuelo}")
        self.logger.handlers = []
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - [Avión %(id_vuelo)s] %(message)s',
            '%H:%M:%S'
        ))
        self.logger.addHandler(handler)
        
        self.log_info(f"Iniciando vuelo - Operación: {self.tipo_operacion}")
    
    def _generar_id_vuelo(self):
        """Genera un ID de vuelo aleatorio"""
        aerolineas = ['IB', 'AA', 'DL', 'UA', 'BA', 'LH', 'AF']
        return f"{choice(aerolineas)}{randint(1000, 9999)}"
    
    def log_info(self, mensaje):
        """Método auxiliar para logging con el ID del vuelo"""
        self.logger.info(mensaje, extra={'id_vuelo': self.id_vuelo})
    
    def log_error(self, mensaje):
        """Método auxiliar para logging de errores con el ID del vuelo"""
        self.logger.error(mensaje, extra={'id_vuelo': self.id_vuelo})
    
    async def iniciar_operacion(self):
        """Método principal para iniciar la operación del avión"""
        try:
            # Establecer conexión con la torre de control
            reader, writer = await asyncio.open_connection(HOST, PORT)
            
            # Marcar tiempo de inicio
            self.tiempo_inicio = time.perf_counter()
            
            # Preparar y enviar solicitud
            solicitud = {
                'id': self.id_vuelo,
                'tipo': self.tipo_operacion,
                'aerolinea': self.aerolinea,
                'timestamp': time.time()
            }
            
            self.log_info(f"Enviando solicitud de {self.tipo_operacion} a la torre")
            writer.write(json.dumps(solicitud).encode())
            await writer.drain()
            
            # Esperar respuesta de la torre
            data = await reader.read(1024)
            if data:
                respuesta = json.loads(data.decode())
                self.tiempo_autorizacion = time.perf_counter()
                tiempo_espera = self.tiempo_autorizacion - self.tiempo_inicio
                
                status = respuesta.get('status')
                pista = respuesta.get('pista')
                
                if status == 'autorizado':
                    self.log_info(f"Autorización recibida para {self.tipo_operacion} "
                                 f"en pista {pista} (espera: {tiempo_espera:.2f}s)")
                    
                    # Simular tiempo de operación
                    tiempo_operacion = 5 if self.tipo_operacion == 'aterrizaje' else 3
                    self.log_info(f"Iniciando {self.tipo_operacion} en pista {pista}...")
                    await asyncio.sleep(tiempo_operacion)
                    
                    # Completar operación
                    self.tiempo_completado = time.perf_counter()
                    tiempo_total = self.tiempo_completado - self.tiempo_inicio
                    
                    self.log_info(f"{self.tipo_operacion.capitalize()} completado "
                                 f"(tiempo total: {tiempo_total:.2f}s)")
                elif status == 'en_espera':
                    self.log_info(f"Solicitud en espera: {respuesta.get('mensaje', 'Sin información')}")
                    # Podríamos implementar un bucle de reintento aquí si fuera necesario
                    # Por ahora, simplemente esperamos a que la torre nos procese
                    await asyncio.sleep(2)
                    self.log_info(f"Esperando autorización...")
                    
                    # Para este escenario simplificado, asumimos que la torre nos procesará
                    # eventualmente sin necesidad de reenviar la solicitud
                    self.tiempo_completado = time.perf_counter()
                    tiempo_total = self.tiempo_completado - self.tiempo_inicio
                    self.log_info(f"{self.tipo_operacion.capitalize()} completado después de espera")
                else:
                    self.log_error(f"Solicitud rechazada: {respuesta.get('mensaje', 'Sin información')}")
            else:
                self.log_error("No se recibió respuesta de la torre")
            
            # Cerrar conexión
            writer.close()
            await writer.wait_closed()
            
        except ConnectionRefusedError:
            self.log_error("No se pudo conectar con la torre de control. Verifica que esté en ejecución.")
        except Exception as e:
            self.log_error(f"Error durante la operación: {e}")


async def main():
    """Función principal para iniciar el avión desde línea de comandos"""
    # Procesar argumentos de línea de comandos
    id_vuelo = None
    tipo_operacion = None
    
    if len(sys.argv) > 1:
        id_vuelo = sys.argv[1]
    
    if len(sys.argv) > 2:
        tipo_operacion = sys.argv[2].lower()
        if tipo_operacion not in ['aterrizaje', 'despegue']:
            print("Tipo de operación no válido. Debe ser 'aterrizaje' o 'despegue'")
            sys.exit(1)
    
    # Crear y ejecutar el avión
    avion = Avion(id_vuelo, tipo_operacion)
    await avion.iniciar_operacion()


async def generar_trafico(num_aviones):
    """Genera tráfico simulado con múltiples aviones"""
    tareas = []
    
    print(f"\nIniciando simulación de {num_aviones} aviones...")
    print("Cada avión se mostrará en la interfaz del monitor al ser procesado.")
    
    # Crear aviones con un pequeño retardo entre ellos para evitar la congestión
    for i in range(num_aviones):
        # Retardo aleatorio para escalonar las solicitudes
        retardo = random_delay()
        print(f"Programando avión {i+1}/{num_aviones} - lanzamiento en {retardo:.1f}s")
        await asyncio.sleep(retardo)
        
        # Crear un avión con parámetros aleatorios
        avion = Avion()
        tareas.append(asyncio.create_task(avion.iniciar_operacion()))
    
    # Esperar a que todas las tareas se completen
    await asyncio.gather(*tareas)
    
    print(f"\n✅ Simulación completada: {num_aviones} aviones procesados correctamente.")


def random_delay():
    """Genera un retardo aleatorio para escalonar las solicitudes"""
    # Retardos entre 0.5 y 2 segundos para que la simulación sea dinámica
    # pero con suficiente tiempo entre aviones para ver lo que sucede
    return randint(5, 20) / 10


if __name__ == "__main__":
    try:
        # Verificar si se proporciona un número como argumento para simulación
        if len(sys.argv) == 2 and sys.argv[1].isdigit():
            num_aviones = int(sys.argv[1])
            print(f"Iniciando simulación con {num_aviones} aviones...")
            asyncio.run(generar_trafico(num_aviones))
        # Si se dan argumentos específicos para un avión, ejecutar un solo avión
        elif len(sys.argv) > 1:
            asyncio.run(main())
        # Sin argumentos, generar tráfico aleatorio por defecto
        else:
            num_aviones = 15
            print(f"Iniciando simulación con {num_aviones} aviones por defecto...")
            asyncio.run(generar_trafico(num_aviones))
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")