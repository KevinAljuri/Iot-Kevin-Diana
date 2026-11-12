
# Sistema IoT para el control de entradas y salidas en aulas de clase

**Unidades Tecnológicas de Santander (UTS)**

**Asignatura:** Internet de las Cosas (IoT)  
**Grupo:** B192  
**Integrantes:** Kevin David Aljuri Moncada y Diana Marcela Beltrán Suárez  
**Docente:** Eliecer Montero Ojeda  
**Año:** 2026

## 1. Descripción del proyecto

El proyecto consiste en un sistema IoT para el control de entradas y salidas de personas en un aula de clase, utilizando un ESP32 y diferentes sensores.

El sistema permite medir temperatura, humedad, luminosidad y cantidad de personas presentes. Además, utiliza un LED verde, un LED rojo y un buzzer para indicar las condiciones del aforo.

Durante la semana 13 se implementó la comunicación con Adafruit IO y las automatizaciones mediante IFTTT. En la semana 14 se amplió el proyecto incorporando almacenamiento avanzado con InfluxDB, visualización histórica con Grafana y alertas inteligentes mediante correo electrónico.

## 2. Objetivo

Implementar un sistema de almacenamiento local que permita conservar y consultar las mediciones enviadas por el ESP32 a Adafruit IO, utilizando Python e InfluxDB para almacenar los datos y Grafana para visualizar su comportamiento histórico.

## 3. Materiales utilizados

- ESP32 DevKit.
- Sensor DHT11 para temperatura y humedad.
- Sensor LDR para luminosidad.
- Dos sensores infrarrojos para entradas y salidas.
- LED verde y LED rojo.
- Buzzer.
- Protoboard y cables de conexión.
- Computador con Windows.
- Conexión WiFi.

## 4. Herramientas utilizadas

**Adafruit IO:** recibe los datos enviados por el ESP32 mediante MQTT.

**Python:** consulta los feeds de Adafruit IO y almacena las mediciones en InfluxDB.

**InfluxDB:** base de datos local utilizada para conservar registros históricos con su fecha y hora.

**Grafana:** permite visualizar indicadores, gráficas históricas, tablas estadísticas y configurar alertas.

**Docker Desktop:** permite ejecutar InfluxDB y Grafana mediante contenedores.

**Gmail:** recibe las notificaciones generadas por las alertas de Grafana.

## 5. Funcionamiento del sistema

El funcionamiento general es:

ESP32 → Adafruit IO → Python → InfluxDB → Grafana

El ESP32 publica los datos ambientales aproximadamente cada 15 segundos en Adafruit IO. El conteo de personas se publica cuando se registra una entrada o salida y al reconectar MQTT.

Posteriormente, un script de Python consulta los feeds y almacena las lecturas en InfluxDB, conservando el valor, la fecha, la hora, el sensor y el aula.

Grafana consulta esta base de datos para representar la información y analizar su comportamiento a lo largo del tiempo.

Los controles del LED rojo y el buzzer continúan funcionando desde Adafruit IO.

## 6. Variables almacenadas

Se utilizan cuatro feeds principales:

| Variable | Sensor | Unidad |
|---|---|---|
| Temperatura | DHT11 | °C |
| Humedad | DHT11 | % |
| Luminosidad | LDR | ADC (0–4095) |
| Personas | Sensores IR | Personas |

En InfluxDB los registros se almacenan en el bucket `aulas`, utilizando la etiqueta `AULA-101` para identificar el espacio monitorizado.

## 7. Instalación y configuración

Para ejecutar el proyecto se necesita Python y Docker Desktop.

### 7.1. Configurar las credenciales

Crear un archivo `.env` a partir de `.env.example`.

En este archivo se configuran las credenciales privadas de Adafruit IO, InfluxDB y Grafana.

Las credenciales reales no se incluyen en el repositorio por seguridad.

### 7.2. Iniciar Docker

Abrir Docker Desktop y posteriormente PowerShell en la carpeta donde se encuentra `compose.yaml`.

Ejecutar:

```powershell
docker compose up -d
```

Verificar los servicios:

```powershell
docker compose ps
```

Los servicios se pueden consultar desde:

- InfluxDB: http://localhost:8086
- Grafana: http://localhost:3000

### 7.3. Instalar las dependencias de Python

En PowerShell:

```powershell
py -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Estos comandos se utilizan durante la instalación inicial.

### 7.4. Ejecutar el almacenamiento

Para realizar una sincronización de prueba:

```powershell
.\.venv\Scripts\python.exe scripts\ejecutar.py --una-vez
```

Para ejecutar la sincronización continua:

```powershell
.\.venv\Scripts\python.exe scripts\ejecutar.py
```

El programa consulta las cuatro variables y almacena sus lecturas en InfluxDB. También calcula periódicamente el umbral dinámico de temperatura.

La terminal debe permanecer abierta mientras se utilice el sistema.

## 8. Verificación del almacenamiento

En InfluxDB se utiliza Data Explorer para consultar las mediciones guardadas.

Se comprueba que los registros de temperatura, humedad, luminosidad y personas se encuentran almacenados en el bucket `aulas`.

Para demostrar la persistencia se reinicia el servicio con:

```powershell
docker compose restart influxdb
```

Después del reinicio se vuelve a consultar la base de datos y se verifica que las mediciones anteriores permanecen almacenadas.

Los volúmenes de Docker permiten conservar la información al detener o reiniciar los contenedores.

## 9. Dashboard de Grafana

Se creó un dashboard llamado:

**Control Inteligente de Aula B192 - Semana 14**

El dashboard incluye:

- Indicador de temperatura actual.
- Indicador de humedad.
- Indicador de luminosidad.
- Indicador de personas presentes.
- Gráficas históricas de las cuatro variables.
- Tendencia de temperatura de las últimas 24 horas.
- Tabla de promedio, mínimo y máximo diario.
- Panel preparado para comparar temperaturas entre aulas.

Actualmente se dispone de mediciones de AULA-101. La comparación con otra aula queda pendiente hasta contar con una segunda serie de datos reales.

El dashboard exportado se encuentra en la carpeta `dashboards/`.

## 10. Alertas inteligentes

Se implementó un script de Python que calcula un umbral dinámico de temperatura a partir del histórico disponible de la última semana.

La fórmula utilizada es:

**Umbral = Promedio + 2 × Desviación estándar**

También se calcula:

**Exceso = Temperatura actual - Umbral**

Cuando el exceso es mayor que cero, Grafana puede activar una alerta.

La regla de temperatura fue configurada con una evaluación cada minuto y un contacto de correo electrónico mediante Gmail.

Durante las pruebas se comprobó la activación de la alerta y la recepción de correos.

El sistema también permite configurar reglas adicionales de humedad, luminosidad y aforo, utilizando los datos que ya están almacenados en InfluxDB.

Las reglas de alerta y las credenciales del servicio de correo se configuran localmente en Grafana. No forman parte automáticamente del JSON exportado del dashboard.

## 11. Evidencias

En la carpeta `docs/` se incluyen capturas de:

1. Servicios de InfluxDB y Grafana ejecutándose en Docker.
2. Script de Python procesando las cuatro variables.
3. Registros almacenados en InfluxDB.
4. Persistencia de los datos después del reinicio.
5. Dashboard de Grafana.
6. Alerta de temperatura activada.
7. Correo recibido desde Grafana.

Estas evidencias permiten comprobar el funcionamiento del almacenamiento y la visualización del sistema.

## 12. Limitaciones encontradas

Durante el desarrollo se presentaron dificultades en la configuración inicial de las contraseñas de InfluxDB y en la conexión entre las herramientas.

También se observaron algunas lecturas atípicas de temperatura durante las pruebas, por lo que es importante revisar la calidad de los datos antes de interpretar los promedios y las alertas.

El sistema utiliza actualmente un solo prototipo y registra mediciones identificadas como AULA-101.

Además, para mantener la sincronización con InfluxDB, el computador debe estar encendido y el programa de Python en ejecución.

## 13. Cómo iniciar nuevamente el proyecto

Después de encender el computador:

1. Abrir Docker Desktop.
2. Conectar y encender el ESP32.
3. Abrir PowerShell en la carpeta del proyecto.
4. Ejecutar:

```powershell
docker compose up -d
```

5. Iniciar Python:

```powershell
.\.venv\Scripts\python.exe scripts\ejecutar.py
```

6. Abrir Grafana en http://localhost:3000 y consultar el dashboard.

No es necesario volver a instalar las dependencias ni crear el dashboard.

## 14. Cómo detener el proyecto

Para detener Python se utiliza `Ctrl + C` en su terminal.

Después se ejecuta:

```powershell
docker compose stop
```

Este procedimiento detiene los servicios sin borrar los datos guardados.

No se debe utilizar `docker compose down -v`, debido a que esta opción elimina los volúmenes del proyecto.

## 15. Conclusiones

Se logró integrar el sistema IoT desarrollado anteriormente con una base de datos local para conservar las mediciones obtenidas por los sensores.

El uso de Python e InfluxDB permitió almacenar los datos de temperatura, humedad, luminosidad y personas, mientras que Grafana facilitó su visualización mediante indicadores, gráficas y tablas históricas.

También se implementó una alerta dinámica de temperatura con notificación por correo electrónico, permitiendo identificar condiciones que se desvían del comportamiento registrado.

Finalmente, se comprobó que los datos permanecen almacenados después de reiniciar InfluxDB, cumpliendo el objetivo principal de almacenamiento avanzado de la semana 14.
