import asyncio
import json
import logging
import socket
import time
import os
from datetime import datetime
from collections import deque

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Monitor] %(message)s',
    datefmt='%H:%M:%S'
)

HOST = '127.0.0.1'
PORT = 5001
MAX_HISTORY = 100
VERBOSE = False  # ← Cambia esto a True si quieres ver detalles de conexión

class MonitorVuelos:
    def __init__(self):
        self.vuelos_pendientes = {}
        self.vuelos_activos = {}
        self.vuelos_completados = {}
        self.historial = deque(maxlen=MAX_HISTORY)

        self.stats = {
            "tiempo_espera_promedio": 0,
            "operaciones_completadas": 0,
            "pistas_disponibles": 0,
            "pistas_totales": 0,
            "ultima_actualizacion": datetime.now().strftime("%H:%M:%S")
        }

        self.running = True
        self.lock_file = os.path.join(os.path.dirname(__file__), '.monitor_lock')
        logging.info("Monitor de vuelos iniciado")

    async def iniciar_servidor(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.setblocking(False)

        logging.info(f"Servidor del monitor iniciado en {HOST}:{PORT}")
        loop = asyncio.get_running_loop()
        asyncio.create_task(self._actualizar_ui())

        while self.running:
            try:
                client_socket, addr = await loop.sock_accept(server)
                if VERBOSE:
                    logging.info(f"Conexión aceptada desde {addr}")
                asyncio.create_task(self._manejar_conexion(client_socket))
            except Exception as e:
                logging.error(f"Error aceptando conexión: {e}")
                await asyncio.sleep(1)

        server.close()

    async def _manejar_conexion(self, client_socket):
        client_socket.setblocking(False)
        loop = asyncio.get_running_loop()

        try:
            while self.running:
                size_bytes = await loop.sock_recv(client_socket, 4)
                if not size_bytes:
                    break
                size = int.from_bytes(size_bytes, byteorder='big')
                data = b''
                while len(data) < size:
                    chunk = await loop.sock_recv(client_socket, size - len(data))
                    if not chunk:
                        break
                    data += chunk
                if len(data) == size:
                    self._procesar_actualizacion(data)
                else:
                    logging.error("Error recibiendo datos completos")
                    break
        except ConnectionResetError:
            if VERBOSE:
                logging.warning("Conexión cerrada por el lado remoto")
        except Exception as e:
            logging.error(f"Error manejando conexión: {e}")
        finally:
            client_socket.close()
            if VERBOSE:
                logging.info("Conexión cerrada")

    def _procesar_actualizacion(self, data):
        try:
            actualizacion = json.loads(data.decode())

            self.vuelos_pendientes = actualizacion.get('vuelos_pendientes', {})
            self.vuelos_activos = actualizacion.get('vuelos_activos', {})
            nuevos_completados = actualizacion.get('vuelos_completados', {})

            for id_vuelo, info in nuevos_completados.items():
                self.historial.append({
                    'id': id_vuelo,
                    'tipo': info.get('tipo', '---'),
                    'hora': datetime.now().strftime("%H:%M:%S"),
                    'duracion': round(info.get('duracion', 0), 2),
                    'espera': round(info.get('tiempo_espera', 0), 2),
                    'pista': info.get('pista', '---')
                })
                logging.info(f"Registro añadido al historial: {id_vuelo}")

            self.vuelos_completados.update(nuevos_completados)

            self.stats = {
                "tiempo_espera_promedio": actualizacion.get('estadisticas', {}).get('tiempo_espera_promedio', 0),
                "operaciones_completadas": actualizacion.get('estadisticas', {}).get('operaciones_completadas', 0),
                "pistas_disponibles": actualizacion.get('pistas_disponibles', 0),
                "pistas_totales": actualizacion.get('pistas_totales', 0),
                "ultima_actualizacion": actualizacion.get('timestamp', datetime.now().strftime("%H:%M:%S"))
            }

            self._guardar_historial_json()

        except Exception as e:
            logging.error(f"Error procesando actualización: {e}")

    def _guardar_historial_json(self):
        try:
            with open("historial_vuelos.json", "w", encoding="utf-8") as f:
                json.dump(list(self.historial), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando historial JSON: {e}")

    async def _actualizar_ui(self):
        while self.running:
            if os.path.exists(self.lock_file):
                try:
                    with open(self.lock_file, 'r') as f:
                        if f.read().strip() == 'pause':
                            await asyncio.sleep(1)
                            continue
                except:
                    pass

            # print("\033c", end="")  # Desactivado para mantener consola visible
            self._mostrar_encabezado()
            self._mostrar_estado_actual()
            self._mostrar_historial()

            await asyncio.sleep(1)

    def _mostrar_encabezado(self):
        print("=" * 80)
        print(f"  SISTEMA DE CONTROL AÉREO - MONITOR DE VUELOS")
        print(f"  Última actualización: {self.stats['ultima_actualizacion']}")
        print("=" * 80)
        print(f"\nESTADO DEL SISTEMA:")
        print(f"  • Pistas disponibles: {self.stats['pistas_disponibles']}/{self.stats['pistas_totales']}")
        print(f"  • Operaciones completadas: {self.stats['operaciones_completadas']}")
        print(f"  • Tiempo de espera promedio: {self.stats['tiempo_espera_promedio']:.2f}s")
        print("-" * 80)

    def _mostrar_estado_actual(self):
        print("\nOPERACIONES ACTIVAS:")
        if self.vuelos_activos:
            print(f"  {'ID VUELO':<10} {'OPERACIÓN':<12} {'PISTA':<6} {'TIEMPO':<8}")
            print("  " + "-" * 40)
            for id_vuelo, info in self.vuelos_activos.items():
                tipo = info['tipo'].capitalize()
                pista = info.get('pista', 'N/A')
                tiempo_activo = time.perf_counter() - info.get('hora_inicio', time.perf_counter())
                print(f"  {id_vuelo:<10} {tipo:<12} {pista:<6} {tiempo_activo:.2f}s")
        else:
            print("  No hay operaciones activas en este momento.")

        print("\nSOLICITUDES PENDIENTES:")
        if self.vuelos_pendientes:
            print(f"  {'ID VUELO':<10} {'OPERACIÓN':<12} {'ESTADO':<15} {'ESPERA':<8}")
            print("  " + "-" * 50)
            for id_vuelo, info in self.vuelos_pendientes.items():
                tipo = info['tipo'].capitalize()
                estado = info.get('estado', 'desconocido')
                tiempo_espera = time.perf_counter() - info.get('hora_solicitud', time.perf_counter())
                print(f"  {id_vuelo:<10} {tipo:<12} {estado:<15} {tiempo_espera:.2f}s")
        else:
            print("  No hay solicitudes pendientes en este momento.")

    def _mostrar_historial(self):
        print("\nOPERACIONES RECIENTES:")
        if self.historial:
            print(f"  {'ID VUELO':<10} {'OPERACIÓN':<12} {'PISTA':<6} {'DURACIÓN':<9} {'ESPERA':<8} {'HORA':<8}")
            print("  " + "-" * 60)
            for op in list(self.historial)[-10:]:
                print(f"  {op['id']:<10} {op['tipo']:<12} {op['pista']:<6} "
                      f"{op['duracion']:<9.2f}s {op['espera']:<8.2f}s {op['hora']}")
        else:
            print("  No hay operaciones completadas aún.")

async def main():
    monitor = MonitorVuelos()

    if os.path.exists(monitor.lock_file):
        try:
            os.remove(monitor.lock_file)
        except:
            pass

    try:
        await monitor.iniciar_servidor()
    except KeyboardInterrupt:
        monitor.running = False
        logging.info("Monitor detenido por el usuario")

    if os.path.exists(monitor.lock_file):
        try:
            os.remove(monitor.lock_file)
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitor detenido")