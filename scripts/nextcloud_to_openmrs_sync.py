import requests
import os
import logging
import json
from dotenv import load_dotenv
from webdav3.client import Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv(dotenv_path='../.env')

# --- Configuración de Nextcloud ---
NEXTCLOUD_URL = "http://localhost:8081"
NEXTCLOUD_USER = "admin_nc"
# ATENCIÓN: Asegúrate de que esta es la contraseña que pusiste para el usuario 'admin_nc'
NEXTCLOUD_PASS = "admin_nc_password" 
NEXTCLOUD_RESULTS_DIR = '/ResultadosNuevos'
NEXTCLOUD_PROCESSED_DIR = '/ResultadosProcesados'

# --- Configuración de OpenMRS (vía API Gateway) ---
OPENMRS_URL = 'http://localhost:8000/openmrs/ws/rest/v1'
OPENMRS_USER = 'admin'
OPENMRS_PASS = os.getenv('OMRS_ADMIN_USER_PASSWORD')

def get_patient_uuid_by_odoo_id(session, odoo_id):
    """Busca el UUID de un paciente usando su identificador único de Odoo."""
    identifier = f"ODOO-{odoo_id}"
    try:
        # Buscamos un paciente que tenga EXACTAMENTE ese identificador
        response = session.get(f"{OPENMRS_URL}/patient", params={'q': identifier, 'v': 'custom:(uuid)'})
        response.raise_for_status()
        results = response.json().get('results', [])
        if results:
            patient_uuid = results[0]['uuid']
            logging.info(f"Paciente con ID de Odoo '{odoo_id}' encontrado en OpenMRS. UUID: {patient_uuid}")
            return patient_uuid
        else:
            logging.warning(f"No se encontró paciente en OpenMRS con el identificador: {identifier}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red buscando paciente por identificador '{identifier}': {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado buscando paciente por identificador '{identifier}': {e}")
        return None

def main():
    logging.info("=====================================================")
    logging.info("= Iniciando script de transferencia: Nextcloud -> OpenMRS =")
    logging.info("=====================================================")
    try:
        # --- Conexión a Nextcloud ---
        options = {'webdav_hostname': NEXTCLOUD_URL, 'webdav_login': NEXTCLOUD_USER, 'webdav_password': NEXTCLOUD_PASS}
        client = Client(options)
        logging.info("Conexión a Nextcloud exitosa.")
        
        # --- Asegurarse de que los directorios existen ---
        if not client.is_dir(NEXTCLOUD_RESULTS_DIR): client.mkdir(NEXTCLOUD_RESULTS_DIR)
        if not client.is_dir(NEXTCLOUD_PROCESSED_DIR): client.mkdir(NEXTCLOUD_PROCESSED_DIR)

        files_to_process = [f for f in client.list(NEXTCLOUD_RESULTS_DIR) if not f.endswith('/')]
        if not files_to_process:
            logging.info("No hay nuevos archivos de resultados para procesar.")
            return
        logging.info(f"Se encontraron {len(files_to_process)} archivos para procesar.")
        
        # --- Preparar Conexión a OpenMRS ---
        session = requests.Session()
        session.auth = (OPENMRS_USER, OPENMRS_PASS)

        for file_name in files_to_process:
            logging.info(f"--- Procesando archivo: '{file_name}' ---")
            try:
                # --- Extraer ID de Odoo del nombre del archivo ---
                # Formato esperado: "CUALQUIERCOSA_ODOO-ID_CUALQUIERCOSA.pdf"
                # Ejemplo: "RESULTADO_ODOO-47_2025-07-12.pdf"
                odoo_id = file_name.split('_')[1].split('-')[1]
                patient_uuid = get_patient_uuid_by_odoo_id(session, odoo_id)
                if not patient_uuid:
                    logging.error(f"No se pudo encontrar al paciente para el archivo '{file_name}'. Se reintentará en la próxima ejecución.")
                    continue

                # --- Descargar archivo y adjuntarlo como una "Observación Compleja" ---
                logging.info(f"Descargando '{file_name}' de Nextcloud...")
                remote_file_path = os.path.join(NEXTCLOUD_RESULTS_DIR, file_name)
                temp_file_content = client.resource(remote_file_path).read()
                
                # Para subir un archivo, la API de OpenMRS necesita un payload multipart/form-data.
                # 'json' contiene los metadatos de la observación.
                # 'file' contiene el binario del archivo.
                # El concept UUID 'a899e040-e794-4363-80e9-794541728235' es el default para "Complex Data"
                obs_payload = {
                    "person": patient_uuid,
                    "concept": "a899e040-e794-4363-80e9-794541728235", 
                    "obsDatetime": "2025-07-12T10:15:00.000-0500",
                    "comment": f"Resultado de laboratorio importado: {file_name}"
                }
                
                files_to_upload = {
                    'json': (None, json.dumps(obs_payload), 'application/json'),
                    'file': (file_name, temp_file_content, 'application/pdf')
                }
                
                logging.info(f"Subiendo archivo a OpenMRS para el paciente {patient_uuid}...")
                response = session.post(f"{OPENMRS_URL}/obs", files=files_to_upload)
                
                if response.status_code == 201:
                    logging.info(f"¡ÉXITO! Archivo '{file_name}' adjuntado al paciente.")
                    # Mover archivo a la carpeta de procesados para no volver a procesarlo
                    client.move(remote_file_path, os.path.join(NEXTCLOUD_PROCESSED_DIR, file_name))
                else:
                    logging.error(f"Error al adjuntar archivo en OpenMRS: {response.status_code} - {response.text}")
            except (IndexError, ValueError) as e:
                logging.error(f"El nombre del archivo '{file_name}' no tiene el formato correcto (ej: RESULTADO_ODOO-47_FECHA.pdf). Error: {e}")
            except Exception as e:
                logging.error(f"Error inesperado procesando el archivo '{file_name}': {e}")
                
    except Exception as e:
        logging.critical(f"CRITICAL: Ocurrió un error general. Verifica la conexión a Nextcloud u OpenMRS. Detalle: {e}")

if __name__ == "__main__":
    main()