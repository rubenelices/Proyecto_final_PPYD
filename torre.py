import asyncio
import json
import socket
import time
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5000
MONITOR_PORT = 5001
MAX_PISTAS = 2

class TorreControl:
    def __init__(self):
        self.vuelos_pendientes = {}    # ID -> info
        self.vuelos_activos = {}       # ID -> info
        self.vuelos_completados = {}   # ID -> info

        self.pistas_ocupadas = 0
        self.operaciones_completadas = 0
        self.tiempo_espera_total = 0

    async def iniciar(self):
        asyncio.create_task(self.enviar_actualizaciones_monitor())

        server = await asyncio.start_server(self.manejar_conexion, HOST, PORT)
        print(f"[TORRE] Torre de control escuchando en {HOST}:{PORT}")
        async with server:
            await server.serve_forever()

    async def manejar_conexion(self, reader, writer):
        datos = await reader.read(1024)
        
        try:
            # Procesamos el mensaje como JSON (formato desde avion.py)
            solicitud = json.loads(datos.decode())
            
            id_vuelo = solicitud.get('id')
            operacion = solicitud.get('tipo')
            
            if not id_vuelo or operacion not in ['aterrizaje', 'despegue']:
                print(f"[TORRE] Solicitud inválida: {solicitud}")
                writer.write(json.dumps({
                    'status': 'rechazado',
                    'mensaje': 'Formato de solicitud inválido'
                }).encode())
                await writer.drain()
                writer.close()
                return
                
            # Creamos la información del vuelo
            vuelo_info = {
                "tipo": operacion,
                "estado": "pendiente",
                "hora_solicitud": time.perf_counter(),
                "aerolinea": solicitud.get('aerolinea', 'N/A')
            }

            # Registramos la solicitud como pendiente
            self.vuelos_pendientes[id_vuelo] = vuelo_info
            print(f"[TORRE] Solicitud recibida: {id_vuelo} quiere {operacion}")
            
            # Si hay pistas disponibles, autorizamos inmediatamente
            if self.pistas_ocupadas < MAX_PISTAS:
                pista_asignada = self._asignar_pista()
                
                # Respondemos al avión con la autorización
                respuesta = {
                    'status': 'autorizado',
                    'pista': pista_asignada,
                    'mensaje': f'{operacion.capitalize()} autorizado en pista {pista_asignada}'
                }
                writer.write(json.dumps(respuesta).encode())
                await writer.drain()
                
                # Procesamos el vuelo
                asyncio.create_task(self.procesar_vuelo(id_vuelo))
            else:
                # Si no hay pistas, ponemos en espera
                respuesta = {
                    'status': 'en_espera',
                    'mensaje': 'Todas las pistas están ocupadas, en espera de autorización'
                }
                writer.write(json.dumps(respuesta).encode())
                await writer.drain()
                
                # Programamos el procesamiento para cuando haya una pista libre
                asyncio.create_task(self.procesar_vuelo(id_vuelo))
        
        except json.JSONDecodeError:
            print("[TORRE] Error decodificando JSON:", datos.decode())
            writer.write(json.dumps({
                'status': 'error',
                'mensaje': 'Formato de mensaje inválido'
            }).encode())
            await writer.drain()
        except Exception as e:
            print(f"[TORRE] Error procesando solicitud: {e}")
            writer.write(json.dumps({
                'status': 'error',
                'mensaje': f'Error en la torre: {str(e)}'
            }).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def procesar_vuelo(self, id_vuelo):
        # Esperamos a que se libere una pista si todas están ocupadas
        while self.pistas_ocupadas >= MAX_PISTAS:
            await asyncio.sleep(0.5)

        # Movemos el vuelo de pendiente a activo
        vuelo = self.vuelos_pendientes.pop(id_vuelo, None)
        if not vuelo:
            print(f"[TORRE] Error: El vuelo {id_vuelo} ya no está pendiente")
            return
            
        vuelo["estado"] = "activo"
        vuelo["hora_inicio"] = time.perf_counter()
        vuelo["pista"] = self._asignar_pista()
        self.vuelos_activos[id_vuelo] = vuelo
        self.pistas_ocupadas += 1

        print(f"[TORRE] {id_vuelo} comienza {vuelo['tipo']} en pista {vuelo['pista']}")

        # Simulamos el tiempo de operación
        tiempo_operacion = 2 + (1 if vuelo["tipo"] == "aterrizaje" else 0.5)
        await asyncio.sleep(tiempo_operacion)

        # Completamos la operación
        vuelo = self.vuelos_activos.pop(id_vuelo)
        hora_fin = time.perf_counter()
        vuelo["duracion"] = hora_fin - vuelo["hora_inicio"]
        vuelo["tiempo_espera"] = vuelo["hora_inicio"] - vuelo["hora_solicitud"]
        self.vuelos_completados[id_vuelo] = vuelo
        self.operaciones_completadas += 1
        self.tiempo_espera_total += vuelo["tiempo_espera"]
        self.pistas_ocupadas -= 1

        print(f"[TORRE] {id_vuelo} finalizó su {vuelo['tipo']} en pista {vuelo['pista']}")

    def _asignar_pista(self):
        return (self.operaciones_completadas % MAX_PISTAS) + 1

    async def enviar_actualizaciones_monitor(self):
        while True:
            await asyncio.sleep(1)

            try:
                with socket.create_connection((HOST, MONITOR_PORT), timeout=1) as s:
                    # Creamos una copia del diccionario de vuelos completados
                    vuelos_finalizados = dict(self.vuelos_completados)
                    
                    # Limpiamos el diccionario después de cada envío al monitor
                    # para no enviar los mismos vuelos repetidamente
                    self.vuelos_completados = {}

                    estado = {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "pistas_disponibles": MAX_PISTAS - self._pistas_en_uso(),
                        "pistas_totales": MAX_PISTAS,
                        "vuelos_pendientes": self.vuelos_pendientes,
                        "vuelos_activos": self.vuelos_activos,
                        "vuelos_completados": vuelos_finalizados,
                        "estadisticas": {
                            "tiempo_espera_promedio": (
                                self.tiempo_espera_total / self.operaciones_completadas
                                if self.operaciones_completadas > 0 else 0
                            ),
                            "operaciones_completadas": self.operaciones_completadas
                        }
                    }

                    mensaje = json.dumps(estado).encode()
                    longitud = len(mensaje).to_bytes(4, byteorder='big')
                    s.sendall(longitud + mensaje)

            except (ConnectionRefusedError, socket.timeout):
                print("[TORRE] No se pudo conectar con el monitor.")
            except Exception as e:
                print(f"[TORRE] Error al enviar actualización: {e}")

    def _pistas_en_uso(self):
        return self.pistas_ocupadas

if __name__ == "__main__":
    try:
        torre = TorreControl()
        asyncio.run(torre.iniciar())
    except KeyboardInterrupt:
        print("\n[TORRE] Torre de control detenida.")