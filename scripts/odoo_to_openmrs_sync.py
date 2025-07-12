import odoorpc
import requests
import os
from dotenv import load_dotenv
import logging

# --- Configuración de Logs ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Cargar Variables de Entorno ---
load_dotenv(dotenv_path='../.env')

# --- Configuración de Conexiones ---
ODOO_URL = 'localhost'
ODOO_PORT = 8069
ODOO_DB = 'ClinicaDB'
ODOO_ADMIN_USER = 'admin'
# ATENCIÓN: Asegúrate que esta sea la contraseña que pusiste al crear la base de datos de Odoo
ODOO_ADMIN_PASS = 'admin_password' 

# URL del API Gateway (Kong) que apunta al servicio de OpenMRS
# La ruta /openmrs fue la que configuramos en la Route de Kong
OPENMRS_URL = 'http://localhost:8000/openmrs/ws/rest/v1' 
OPENMRS_USER = 'admin'
OPENMRS_PASS = os.getenv('OMRS_ADMIN_USER_PASSWORD')

def get_first_uuid(session, resource_path, display_name=""):
    """Función genérica para obtener el primer UUID de un recurso de OpenMRS."""
    try:
        response = session.get(f"{OPENMRS_URL}/{resource_path}")
        response.raise_for_status()
        results = response.json().get('results', [])
        if results:
            uuid = results[0]['uuid']
            logging.info(f"UUID para '{resource_path}' encontrado: {uuid}")
            return uuid
        logging.error(f"No se encontraron recursos en OpenMRS en la ruta: {resource_path}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al obtener UUID de '{resource_path}': {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado obteniendo UUID de '{resource_path}': {e}")
        return None

def main():
    logging.info("==================================================")
    logging.info("= Iniciando script de sincronización: Odoo -> OpenMRS =")
    logging.info("==================================================")
    
    try:
        # --- Conexión a Odoo ---
        odoo = odoorpc.ODOO(ODOO_URL, port=ODOO_PORT)
        odoo.login(ODOO_DB, ODOO_ADMIN_USER, ODOO_ADMIN_PASS)
        logging.info("Conexión a Odoo exitosa.")

        Partner = odoo.env['res.partner']
        # Búsqueda mejorada: no es compañía y no es el usuario admin por defecto
        patient_ids = Partner.search([('is_company', '=', False), ('name', '!=', 'Mitchell Admin')])
        
        if not patient_ids:
            logging.warning("No se encontraron contactos (pacientes) en Odoo para sincronizar.")
            return
            
        patients_data = Partner.browse(patient_ids)
        logging.info(f"Se encontraron {len(patients_data)} pacientes en Odoo para procesar.")

        # --- Preparar Conexión a OpenMRS ---
        session = requests.Session()
        session.auth = (OPENMRS_USER, OPENMRS_PASS)
        
        location_uuid = get_first_uuid(session, "location")
        identifier_type_uuid = get_first_uuid(session, "patientidentifiertype")

        if not location_uuid or not identifier_type_uuid:
            logging.error("Faltan UUIDs de configuración de OpenMRS (location o identifiertype). Abortando script.")
            return

        for patient in patients_data:
            patient_name = patient.name
            odoo_id = patient.id
            logging.info(f"--- Procesando paciente: '{patient_name}' (ID Odoo: {odoo_id}) ---")

            # --- Verificar si el paciente ya existe en OpenMRS por su identificador único de Odoo ---
            identifier_query = f"ODOO-{odoo_id}"
            search_response = session.get(f"{OPENMRS_URL}/patient", params={'q': identifier_query, 'v': 'custom:(uuid)'})
            search_response.raise_for_status()
            
            if search_response.json().get('results'):
                logging.warning(f"Paciente con ID de Odoo '{odoo_id}' ya existe en OpenMRS. Saltando.")
                continue

            # --- Mapeo de Datos ---
            names = patient_name.split()
            given_name = names[0] if names else "Desconocido"
            family_name = " ".join(names[1:]) if len(names) > 1 else " "

            person_payload = {
                "names": [{"givenName": given_name, "familyName": family_name}],
                "gender": "M", # Valor de ejemplo, se puede extender para obtenerlo de Odoo
                "birthdate": "1990-01-01" # Valor de ejemplo
            }

            # --- Crear la Persona en OpenMRS ---
            person_response = session.post(f"{OPENMRS_URL}/person", json=person_payload)
            if person_response.status_code != 201:
                logging.error(f"Error creando la entidad Persona para '{patient_name}': {person_response.text}")
                continue
            
            person_uuid = person_response.json()['uuid']
            logging.info(f"Entidad Persona '{patient_name}' creada con UUID: {person_uuid}")

            # --- Crear el Paciente en OpenMRS, vinculándolo a la Persona ---
            patient_payload = {
                "person": person_uuid,
                "identifiers": [{
                    "identifier": identifier_query,
                    "identifierType": identifier_type_uuid,
                    "location": location_uuid,
                    "preferred": True
                }]
            }
            
            patient_response = session.post(f"{OPENMRS_URL}/patient", json=patient_payload)
            if patient_response.status_code == 201:
                logging.info(f"¡ÉXITO! Paciente '{patient_name}' creado en OpenMRS.")
            else:
                logging.error(f"Error creando la entidad Paciente para '{patient_name}': {patient_response.text}")

    except odoorpc.error.RPCError as e:
        logging.critical(f"CRITICAL: Error de conexión o autenticación con Odoo. Verifica URL, DB y credenciales. Detalle: {e}")
    except requests.exceptions.RequestException as e:
        logging.critical(f"CRITICAL: Error de red conectando a OpenMRS. ¿Está el API Gateway (Kong) funcionando en el puerto 8000? Detalle: {e}")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante la ejecución: {e}")

if __name__ == "__main__":
    main()