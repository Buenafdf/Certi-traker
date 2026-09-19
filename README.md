# Certi-Tracker | Gestor de Cursos

Aplicacion web personal para **registrar, clasificar y dar seguimiento a los cursos** en los que el usuario se encuentra inscrito (gratuitos o de pago), llevar el control de su estado y conservar el enlace directo a cada certificado una vez finalizado.

Toda la informacion se almacena de forma local en **Microsoft SQL Server**.

---

## Objetivo

Centralizar el historial de formacion de un estudiante o profesional en una unica herramienta: evitar la perdida de enlaces, conocer en que cursos se esta participando y conservar la evidencia de los certificados obtenidos. El proyecto esta pensado como un punto de partida limpio y funcional, utilizable por otras personas y exportable al portafolio publico.

## Funcionalidades

- **Registro de cursos:** titulo, plataforma, tipo (Gratuito / De pago), enlace del curso y del certificado.
- **Clasificacion por estado:** `Por iniciar`, `En curso` y `Completado`.
- **Enlaces directos:** al curso y al certificado (PDF, Credly, LinkedIn, etc.).
- **Resumen estadistico:** total de cursos, por iniciar, en curso y completados.
- **Edicion y eliminacion** de cursos desde la lista, con registro obligatorio del **motivo de eliminacion**.
- **Historial de eliminaciones:** queda documentado que curso se elimino, por que motivo y en que fecha.
- **Acceso desde multiples dispositivos** en la red local o a traves de Tailscale (PC, laptop y movil).
- **Persistencia local** en SQL Server.

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python + Flask | Backend y rutas web |
| pyodbc | Conexion a SQL Server |
| Microsoft SQL Server (SSMS) | Base de datos local |
| HTML / CSS | Interfaz (sin frameworks frontend) |

## Requisitos previos

1. Python 3.9 o superior.
2. Microsoft SQL Server local con SQL Server Management Studio (SSMS).
3. ODBC Driver 17 para SQL Server.

## Preparacion de la base de datos

1. Abrir SSMS y ejecutar el script incluido en el repositorio:

   ```
   database/script_sql.sql
   ```

2. El script crea la base de datos `GestorCursos` y las tablas:

   - `cursos_certificados`: registros de cursos.
   - `registro_eliminaciones`: historial con el motivo de cada eliminacion.

## Puesta en marcha

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicacion
python app.py
```

Accede en el navegador a **http://127.0.0.1:5000**.

> La aplicacion escucha en `0.0.0.0`, por lo que es accesible desde otros dispositivos de la red.

## Acceso desde otros dispositivos

### Opcion A: misma red Wi-Fi (LAN)

1. Obtener la IP local del equipo: `ipconfig` (ejemplo: `192.168.1.10`).
2. Desde el dispositivo conectado a la misma red, abrir `http://192.168.1.10:5000`.

### Opcion B: Tailscale (funciona fuera de la red local)

Tailscale crea una red privada (VPN) exclusiva entre los dispositivos de una misma cuenta. Con la red configurada:

| Dispositivo | Nodo Tailscale | IP Tailscale | Acceso a la aplicacion |
|---|---|---|---|
| Servidor (SQL Server + Flask) | `alvarosv14` | `100.70.90.19` | `http://127.0.0.1:5000` |
| Laptop | `alvaro14` | `100.105.54.80` | `http://100.70.90.19:5000` |
| Movil | `a04-de-alvaro` | `100.79.76.1` | `http://100.70.90.19:5000` |

Los valores indicados corresponden al despliegue de referencia de este documento; en cada instalacion las direcciones pueden variar.

Consideraciones:

- No es necesario configurar reglas en el firewall de Windows: Tailscale administra sus propias politicas de red y restringe el acceso exclusivamente a miembros de la Tailnet.
- El servidor Flask se ejecuta en el mismo equipo que aloja SQL Server; desde la laptop y el movil se accede por la IP Tailscale de dicho servidor.

## Configuracion de la conexion a SQL Server

Los parametros de conexion se definen como constantes al inicio de `app.py`:

```python
SERVER = "ALVAROSV14"             # nombre del host donde reside SQL Server
DATABASE = "GestorCursos"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
```

Valores alternativos segun el escenario:

- `"ALVAROSV14"`: nombre del host en la red local (escenario actual).
- `"100.70.90.19"`: IP Tailscale del servidor que aloja la base de datos.
- `"localhost"`: si la aplicacion se ejecuta en el mismo equipo que SQL Server.
- `"ALVAROSV14,1433"`: nombre de host con puerto explicito.

La conexion emplea autenticacion de Windows (`Trusted_Connection=yes`).

Nota: si la aplicacion se ejecuta desde otro nodo apuntando al SQL Server remoto por Tailscale, la autenticacion de Windows puede fallar al intentar validar la cuenta contra el equipo remoto; en ese caso se recomienda una cuenta SQL (UID/PWD). El codigo alternativo se encuentra documentado en `app.py`.

## Diseno e interfaz

La interfaz adopta una estetica de terminal de datos, inspirada en plataformas de analisis de mercados y finanzas:

- Tema oscuro con paleta de datos: cian, indigo, verde y ambar.
- Tipografia monoespaciada para numeros, fechas y etiquetas.
- Fondo animado con graficos de velas, linea de tendencia y cinta de cotizaciones decorativa.
- Tabla de registros con formato de consola y resumen estadistico tipo panel.
- Diseno responsivo para movil y compatibilidad con la preferencia del sistema de reducir movimiento.

## Estructura del proyecto

```
gestor-cursos/
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
├── database/
│   └── script_sql.sql
├── static/
│   ├── favicon.svg
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── nuevo_curso.html
    └── historial.html
```

## Capturas de pantalla

Pendiente: incorporar imagenes de la aplicacion en funcionamiento.

## Contribuciones

Proyecto desarrollado con fines de aprendizaje y portafolio personal. Libre de clonar, adaptar o extender segun las necesidades de cada usuario.

## Licencia

Sin licencia especifica. Proyecto personal con fines educativos.