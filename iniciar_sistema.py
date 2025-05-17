import asyncio
import os
import signal
import subprocess
import sys
import time
import json

def mostrar_banner():
    banner = """
  ╔════════════════════════════════════════════════════════════╗
  ║                                                            ║
  ║   SISTEMA DE CONTROL AÉREO DISTRIBUIDO Y CONCURRENTE       ║
  ║                                                            ║
  ╚════════════════════════════════════════════════════════════╝

    Componentes del sistema:
    1. Monitor de vuelos - Visualización en tiempo real
    2. Torre de control - Gestión del tráfico aéreo
    3. Simulación de tráfico aéreo - Modo automático o manual

    Presione Ctrl+C en cualquier momento para detener todos los componentes
    """
    print(banner)

def mostrar_tabla_final():
    try:
        with open("historial_vuelos.json", "r", encoding="utf-8") as f:
            historial = json.load(f)
        if not historial:
            print("No hay vuelos registrados.")
            return

        print("\n╔════════════════════════════════════════════════════════════╗")
        print("║                  HISTORIAL DE VUELOS GESTIONADOS           ║")
        print("╠════════════════╦════════════╦═══════╦═════════╦════════════╣")
        print("║   ID VUELO     ║  OPERACIÓN ║ PISTA ║ TIEMPO  ║   HORA     ║")
        print("╠════════════════╬════════════╬═══════╬═════════╬════════════╣")
        for vuelo in historial[:]:
            idv = vuelo.get("id", "---").ljust(14)
            tipo = vuelo.get("tipo", "---").ljust(10)
            pista = str(vuelo.get("pista", "---")).center(5)
            duracion = f'{vuelo.get("duracion", 0):.2f}s'.rjust(7)
            hora = vuelo.get("hora", "--:--:--")[-8:]
            print(f"║ {idv} ║ {tipo:^10} ║ {pista} ║ {duracion} ║ {hora:^10} ║")
        print("╚════════════════╩════════════╩═══════╩═════════╩════════════╝\n")

    except FileNotFoundError:
        print("[!] No se encontró el historial de vuelos (historial_vuelos.json).")
    except Exception as e:
        print(f"[!] Error al leer historial: {e}")

async def iniciar_componentes(ruta_monitor, ruta_torre, ruta_avion, simular_trafico, num_aviones):
    procesos = []

    mensaje_simulacion = """
╔════════════════════════════════════════════════════════════╗
║  ✅ SIMULACIÓN COMPLETADA: {num_aviones} AVIONES GESTIONADOS           ║
╚════════════════════════════════════════════════════════════╝

¿Qué desea hacer ahora?
1. Simular más aviones
2. Modo manual (lanzar aviones individuales desde otra terminal)
3. Salir del sistema

"""

    try:
        print("[+] Iniciando monitor de vuelos...")
        monitor_proceso = subprocess.Popen([sys.executable, ruta_monitor])
        procesos.append(("Monitor", monitor_proceso))

        await asyncio.sleep(2)

        print("[+] Iniciando torre de control...")
        torre_proceso = subprocess.Popen([sys.executable, ruta_torre])
        procesos.append(("Torre de Control", torre_proceso))

        await asyncio.sleep(3)

        sistema_activo = True

        while sistema_activo:
            if simular_trafico:
                print(f"[+] Iniciando simulación con {num_aviones} aviones...")
                simulador_proceso = subprocess.Popen([sys.executable, ruta_avion, str(num_aviones)])
                procesos.append(("Simulación de Aviones", simulador_proceso))

                while simulador_proceso.poll() is None:
                    await asyncio.sleep(1)

                await asyncio.sleep(3)

                monitor_lock = os.path.join(os.path.dirname(__file__), ".monitor_lock")
                with open(monitor_lock, "w") as f:
                    f.write("pause")

                await asyncio.sleep(2)  # Espera para asegurar que el historial esté actualizado

                mostrar_tabla_final()

                print(mensaje_simulacion.format(num_aviones=num_aviones))
                opcion = input("Seleccione una opción (1-3): ").strip()

                try:
                    os.remove(monitor_lock)
                except:
                    pass

                if opcion == "1":
                    num_input = input("Número de aviones a simular: ").strip()
                    if num_input.isdigit() and int(num_input) > 0:
                        num_aviones = int(num_input)
                    else:
                        print("Número no válido, usando 15 aviones por defecto.")
                        num_aviones = 15
                    simular_trafico = True
                elif opcion == "2":
                    print("\nModo manual: ejecuta manualmente aviones desde otra terminal.")
                    print(f"Ejemplo: python {ruta_avion} IB3456 aterrizaje")
                    input("Presiona Enter para continuar...")
                    simular_trafico = False
                elif opcion == "3":
                    raise KeyboardInterrupt
                else:
                    print("Opción inválida. Volviendo al menú principal.")
                    simular_trafico = False
            else:
                print("\nMODO MANUAL")
                print("1. Iniciar simulación con múltiples aviones")
                print("2. Seguir en modo manual")
                print("3. Salir del sistema")
                opcion = input("Seleccione una opción (1-3): ").strip()

                if opcion == "1":
                    num_input = input("Número de aviones a simular: ").strip()
                    if num_input.isdigit() and int(num_input) > 0:
                        num_aviones = int(num_input)
                    else:
                        print("Número no válido, usando 15 aviones por defecto.")
                        num_aviones = 15
                    simular_trafico = True
                elif opcion == "2":
                    print("\nPuede lanzar aviones con:")
                    print(f"python {ruta_avion} IB3456 aterrizaje")
                    input("Presiona Enter para continuar...")
                    simular_trafico = False
                elif opcion == "3":
                    raise KeyboardInterrupt
                else:
                    print("Opción inválida. Volviendo al menú principal.")

            for nombre, proceso in procesos[:2]:
                if proceso.poll() is not None:
                    print(f"[!] El proceso {nombre} ha terminado inesperadamente.")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        print("\n\n[!] Deteniendo componentes...")

        for nombre, proceso in reversed(procesos):
            print(f"[*] Deteniendo {nombre}...")
            try:
                if sys.platform == "win32":
                    proceso.terminate()
                else:
                    proceso.send_signal(signal.SIGINT)
                proceso.wait(timeout=5)
            except:
                proceso.kill()

        print("[+] Sistema detenido correctamente.")

if __name__ == "__main__":
    mostrar_banner()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_monitor = os.path.join(base_dir, "monitor.py")
    ruta_torre = os.path.join(base_dir, "torre.py")
    ruta_avion = os.path.join(base_dir, "avion.py")

    print("\n¿Desea iniciar una simulación automática?")
    print("1. Sí")
    print("2. No, usaré modo manual")
    opcion = input("Seleccione una opción (1-2): ").strip()

    simular_trafico = opcion == "1"
    num_aviones = 15

    if simular_trafico:
        num_input = input("Número de aviones a simular (por defecto 15): ").strip()
        if num_input.isdigit():
            num_aviones = int(num_input)

    try:
        asyncio.run(iniciar_componentes(ruta_monitor, ruta_torre, ruta_avion, simular_trafico, num_aviones))
    except Exception as e:
        print(f"[!] Error: {e}")