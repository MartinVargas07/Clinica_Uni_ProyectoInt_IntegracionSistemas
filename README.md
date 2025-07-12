# Proyecto de Integración de Sistemas: Clínica Universitaria

Este repositorio contiene la solución completa para el proyecto de integración de sistemas de la Clínica Universitaria. El objetivo es resolver problemas críticos de interoperabilidad, eficiencia y seguridad mediante la integración de sistemas heterogéneos de código abierto.

## 1. Resumen del Proyecto

### 1.1. El Problema: Una Clínica Fragmentada

La Clínica Universitaria, a pesar de su prestigio, operaba con sistemas de información aislados ("silos"). Cada departamento (admisiones, registros médicos, facturación, soporte) utilizaba su propia aplicación, resultando en:

* **Ineficiencia Operativa:** El personal debía ingresar los mismos datos de un paciente en múltiples sistemas, un proceso manual lento y propenso a errores de transcripción.
* **Experiencia de Usuario Deficiente:** Médicos y administradores necesitaban recordar y gestionar múltiples credenciales para acceder a diferentes sistemas, perdiendo tiempo valioso y aumentando la fatiga de contraseñas.
* **Inseguridad y Falta de Trazabilidad:** Documentos críticos como resultados de laboratorio se compartían por canales inseguros (ej. email) y no quedaban vinculados de forma auditable al historial clínico electrónico del paciente.

### 1.2. La Solución: Un Ecosistema Integrado

Este proyecto diseña, implementa y valida una arquitectura de solución que desmantela estos silos, creando un ecosistema tecnológico cohesivo y seguro. La solución se enfoca en tres pilares:

1.  **Centralización de la Identidad:** Implementando un sistema de **Single Sign-On (SSO)**, donde un usuario tiene una única identidad para acceder a todos los servicios autorizados.
2.  **Automatización del Flujo de Datos:** Sincronizando la información de los pacientes entre los sistemas administrativo y clínico a través de APIs, eliminando la doble entrada de datos.
3.  **Gestión Segura de Documentos:** Integrando el repositorio de archivos con el sistema de registros médicos para que los documentos importantes estén siempre disponibles en el contexto correcto.

Todo esto se orquesta y se protege a través de un **API Gateway**, que actúa como la única puerta de entrada a los servicios de la clínica.

## 2. Arquitectura de la Solución

La arquitectura se basa en un conjunto de microservicios y aplicaciones que se comunican a través de patrones de integración bien definidos.

2.1. Componentes y Tecnologías
Componente

Sistema/Tecnología

Versión

Rol en el Proyecto

ERP

Odoo Community

16.0

Fuente de verdad para datos demográficos y administrativos de pacientes.

EMR/EHR (Backend)

OpenMRS Core

nightly

Corazón clínico del sistema; gestiona el historial médico y las observaciones.

Gestor de Archivos

Nextcloud

28

Repositorio central y seguro para documentos (resultados de laboratorio en PDF).

IAM / SSO

Keycloak

24.0.4

Proveedor de Identidad centralizado para la autenticación única (Single Sign-On).

API Gateway

Kong OSS

3.6

Componente Avanzado. Puerta de entrada única que protege y gestiona las APIs.

UI para Gateway

Konga

latest

Interfaz gráfica para administrar Kong.

Bases de Datos

PostgreSQL / MariaDB

13 / 10.11.7

Motores de persistencia para los diferentes servicios.

Orquestación

Docker & Docker Compose

latest

Para containerizar y gestionar el ciclo de vida de toda la arquitectura.

2.3. Patrones de Integración Aplicados
Single Sign-On (SSO) con OIDC: Se utilizó Keycloak para que los usuarios (ej. dr.garcia) puedan iniciar sesión una sola vez y acceder a todos los sistemas (Nextcloud en nuestra demo) sin volver a introducir credenciales.

API RESTful (Invocación Remota): Un script en Python lee la información de nuevos pacientes desde Odoo y utiliza la API REST de OpenMRS (a través de Kong) para crear el registro clínico, eliminando la necesidad de que una persona lo haga manualmente.

Transferencia de Archivos: Un segundo script monitorea una carpeta en Nextcloud. Al detectar un nuevo archivo PDF, lo asocia al paciente correcto en OpenMRS utilizando su API, creando una observación compleja.

3. Guía de Instalación y Ejecución
Sigue estos pasos para levantar toda la infraestructura en un entorno local.

3.1. Prerrequisitos
Docker Desktop instalado y en ejecución.

Git instalado.

Python instalado en tu sistema.

3.2. Configuración del Entorno
Clonar el Repositorio:

Bash

git clone [https://github.com/MartinVargas07/Clinica_Uni_ProyectoInt_IntegracionSistemas.git](https://github.com/MartinVargas07/Clinica_Uni_ProyectoInt_IntegracionSistemas.git)
cd Clinica_Uni_ProyectoInt_IntegracionSistemas
Crear el archivo de variables de entorno:
Crea un archivo llamado .env en la raíz del proyecto y copia el siguiente contenido.

Fragmento de código

# PostgreSQL Passwords
POSTGRES_PASSWORD_ODOO=odoo_password
POSTGRES_PASSWORD_NEXTCLOUD=nextcloud_password
POSTGRES_PASSWORD_KONG=kong_password

# Keycloak Admin Credentials
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin_password

# Odoo Master Password
ODOO_ADMIN_PASSWORD=odoo_admin_password

# OpenMRS Database Credentials
OMRS_DB_NAME=openmrs
OMRS_DB_USER=openmrs
OMRS_DB_PASSWORD=openmrs
OMRS_DB_ROOT_PASSWORD=openmrs
OMRS_ADMIN_USER_PASSWORD=Admin123
Crear el script de inicialización de la DB de Nextcloud:

Crea una carpeta llamada db-init.

Dentro de ella, crea un archivo llamado create-nextcloud-db.sql.

Pega el siguiente contenido en el archivo:

SQL

CREATE USER nextcloud_user WITH PASSWORD 'nextcloud_password';
CREATE DATABASE nextcloud;
GRANT ALL PRIVILEGES ON DATABASE nextcloud TO nextcloud_user;
3.3. Levantar la Infraestructura
Abre una terminal en la raíz del proyecto.

Ejecuta el siguiente comando para construir y lanzar todos los contenedores:

Bash

docker-compose up -d
Espera pacientemente. El primer arranque puede tardar entre 5 y 10 minutos, ya que Odoo y OpenMRS necesitan crear sus bases de datos desde cero.

3.4. Configuración Inicial de las Aplicaciones
Una vez que los contenedores estén corriendo, accede a cada servicio en tu navegador para su configuración inicial:

Odoo (http://localhost:8069): Completa el asistente de creación de la base de datos (usa ClinicaDB como nombre) y asegúrate de marcar la casilla de "Demo data". Luego, instala la app "Contacts".

Nextcloud (http://localhost:8081): Crea un usuario administrador (ej. admin_nc con una contraseña de tu elección) y configura la conexión a la base de datos PostgreSQL usando los datos del archivo .env.

OpenMRS (http://localhost:8083/openmrs): La primera vez verás un asistente de instalación. Sigue los pasos aceptando los valores por defecto. Usa Admin123 como contraseña para el usuario admin.

Keycloak (http://localhost:8888): Accede a la "Administration Console" con las credenciales del .env.

Konga (http://localhost:1337): Crea un usuario local para Konga y luego conéctalo a la API de Admin de Kong usando la URL: http://kong:8001.

4. Ejecución de las Integraciones
Los flujos de integración se ejecutan a través de scripts de Python.

Prepara el entorno de Python:

Bash

# Navega a la carpeta de scripts
cd scripts

# Crea un entorno virtual
python -m venv venv

# Activa el entorno
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
# source venv/bin/activate

# Instala las dependencias
pip install -r requirements.txt
Ejecuta los Scripts:

Para sincronizar pacientes de Odoo a OpenMRS:

Bash

python odoo_to_openmrs_sync.py
Para transferir archivos de resultados de Nextcloud a OpenMRS:

Bash

python nextcloud_to_openmrs_sync.py
5. Conclusión
Este proyecto demuestra con éxito la implementación de una arquitectura de integración compleja y funcional. Se resolvieron problemas de negocio tangibles y se aplicaron patrones y tecnologías estándar de la industria, cumpliendo con todos los objetivos y criterios de evaluación del curso.
