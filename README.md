# PROYECTO CONTROL AEREO RUBÉN ELICES

# Simulación de Control Aéreo Distribuido y Concurrente

Este proyecto es una simulación del tráfico aéreo diseñada en Python, utilizando técnicas de concurrencia y programación distribuida. Permite gestionar operaciones de aterrizaje y despegue en un entorno con pistas limitadas, simulando el comportamiento real de un aeropuerto.

## Objetivo

El sistema tiene como objetivo demostrar el uso de múltiples procesos concurrentes que se comunican mediante sockets, gestionan recursos compartidos (pistas de aterrizaje/despegue) y actualizan el estado del sistema en tiempo real.

## Componentes del sistema

- `iniciar_sistema.py`: Script principal que lanza todos los componentes y orquesta la simulación.
- `torre.py`: Proceso central que actúa como torre de control. Coordina pistas y vuelos.
- `avion.py`: Representa cada vuelo como un proceso independiente que solicita aterrizar o despegar.
- `monitor.py`: Muestra el estado del sistema en tiempo real y guarda un historial de operaciones.

## Tecnologías utilizadas

- `multiprocessing` y `subprocess` para ejecución concurrente.
- `socket` para comunicación entre procesos.
- `asyncio` para asincronía en el monitor.
- `json` para guardar el historial de vuelos.

## Cómo ejecutar el sistema

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/control-aereo-concurrente.git
   cd control-aereo-concurrente
2. Ejecuta el sistema:
   python iniciar_sistema.py
3. Elige un modo:

  Modo automático: se simulan múltiples aviones con operaciones aleatorias.

  Modo manual: puedes lanzar aviones individualmente desde otra terminal.

## Ejemplo de ejecución
El monitor mostrará información como esta en tiempo real:
OPERACIONES ACTIVAS:
  ID VUELO   OPERACIÓN     PISTA  TIEMPO  
  IB3456     Aterrizaje    2      4.02s

OPERACIONES RECIENTES:
  ID VUELO   OPERACIÓN     PISTA  DURACIÓN  ESPERA    HORA
  IB3456     Aterrizaje    2      5.01s     0.00s     12:34:56
Al finalizar una simulación, se muestra un resumen:
SIMULACIÓN COMPLETADA: 10 AVIONES GESTIONADOS
¿Qué desea hacer ahora?
1. Simular más aviones
2. Modo manual
3. Salir
   
## Historial
Las operaciones completadas se guardan automáticamente en el archivo historial_vuelos.json.

Características destacadas
Uso real de exclusión mutua y semáforos.

Comunicación TCP entre procesos mediante sockets.

Gestión de múltiples procesos independientes con orquestación.

Pausa de la interfaz para mostrar resultados de forma legible.
   
