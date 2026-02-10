import streamlit as st
import calendar
import json
from datetime import datetime, timedelta, date
import os
import pandas as pd
import fitz  # PyMuPDF
from pathlib import Path
import locale
from babel.dates import format_date
import subprocess
import sys
import holidays
import hashlib
import time
import requests
import base64

try:
    from streamlit_calendar import calendar as my_calendar
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-calendar"])
    from streamlit_calendar import calendar as my_calendar

# Configurar página
st.set_page_config(
    page_title="Seguimiento de Vacaciones",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Archivo para gestionar usuarios
USERS_FILE = 'users.json'
TEMPLATE_FILE = 'horas_registro.pdf'

def hash_password(password):
    """Hash de la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Cargar usuarios desde GitHub"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        
        api_url = f"https://api.github.com/repos/{repo}/contents/users.json?ref={branch}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            file_content = base64.b64decode(content['content']).decode()
            return json.loads(file_content)
        else:
            return {}
    except:
        return {}

def save_users(users_dict):
    """Guardar usuarios en GitHub"""
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    
    api_url = f"https://api.github.com/repos/{repo}/contents/users.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Obtener SHA del archivo actual (si existe)
    response = requests.get(api_url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]
    
    # Codificar contenido
    encoded_content = base64.b64encode(json.dumps(users_dict, indent=4).encode()).decode()
    
    payload = {
        "message": "🔄 Actualización de usuarios",
        "content": encoded_content,
        "branch": branch
    }
    
    if sha:
        payload["sha"] = sha
    
    result = requests.put(api_url, headers=headers, json=payload)
    return result.status_code in [200, 201]

def update_vacation_data_on_github(user_id, data_dict):
    """Actualizar vacation_data_USER.json en GitHub"""
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    file_name = f"vacation_data_{user_id}.json"
    
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Obtener SHA
    response = requests.get(api_url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]
    
    encoded_content = base64.b64encode(json.dumps(data_dict, indent=4).encode()).decode()
    
    payload = {
        "message": f"🔄 Actualización de vacaciones de {user_id}",
        "content": encoded_content,
        "branch": branch
    }
    
    if sha:
        payload["sha"] = sha
    
    result = requests.put(api_url, headers=headers, json=payload)
    
    if result.status_code in [200, 201]:
        st.toast("✅ Datos guardados", icon="💾")
    else:
        st.error(f"❌ Error al guardar: {result.json()}")

def load_vacation_data(user_id):
    """Cargar datos de vacaciones desde GitHub"""
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    file_name = f"vacation_data_{user_id}.json"
    
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_name}?ref={branch}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        content = response.json()
        file_content = base64.b64decode(content['content']).decode()
        return json.loads(file_content)
    
    return None

def save_vacation_data(user_id, data):
    """Guardar datos de vacaciones"""
    update_vacation_data_on_github(user_id, data)

def check_authentication():
    """Verificar si el usuario está autenticado"""
    return st.session_state.get('authenticated', False)

def register_form():
    """Formulario de registro"""
    st.markdown("""
    <style>
    .register-title {
        text-align: center;
        color: #000;
        margin-bottom: 1.5rem;
        font-size: 1.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="register-title">📝 Crear Nueva Cuenta</div>', unsafe_allow_html=True)
        
        with st.form("register_form", clear_on_submit=False):
            username = st.text_input(
                "Usuario",
                placeholder="Elige un nombre de usuario",
                help="Este será tu identificador único"
            )
            
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Crea una contraseña segura"
            )
            
            password_confirm = st.text_input(
                "Confirmar Contraseña",
                type="password",
                placeholder="Repite la contraseña"
            )
            
            st.markdown("---")
            st.subheader("Datos personales")
            
            full_name = st.text_input(
                "Nombre completo",
                placeholder="Ej: PÉREZ GARCÍA, JUAN"
            )
            
            nif = st.text_input(
                "NIF/DNI",
                placeholder="Ej: 12345678X",
                max_chars=9
            )
            
            workplace = st.text_input(
                "Centro de trabajo",
                value="E.T.S. DE INGENIEROS DE TELECOMUNICACIÓN",
                placeholder="Centro de trabajo"
            )
            
            company = st.text_input(
                "Empresa",
                value="UPM",
                placeholder="Empresa"
            )
            
            total_days = st.number_input(
                "Días de vacaciones al año",
                min_value=1,
                max_value=50,
                value=22,
                help="Días laborables libres al año"
            )
            
            st.markdown("---")
            st.subheader("📥 Importar datos existentes (opcional)")
            st.info("Si ya tienes datos de vacaciones guardados, puedes importarlos aquí")
            
            uploaded_file = st.file_uploader(
                "Sube tu archivo vacation_data.json",
                type=['json'],
                help="Importa tus días de vacaciones y festivos personalizados"
            )
            
            import_data = None
            if uploaded_file is not None:
                try:
                    import_data = json.load(uploaded_file)
                    st.success(f"✅ Archivo cargado: {len(import_data.get('used_days', []))} días de vacaciones, {len(import_data.get('custom_holidays', []))} festivos personalizados")
                except:
                    st.error("❌ Error al leer el archivo JSON")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submit_button = st.form_submit_button(
                    "Crear Cuenta",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_btn2:
                cancel_button = st.form_submit_button(
                    "Cancelar",
                    use_container_width=True
                )
            
            if cancel_button:
                st.session_state.show_register = False
                st.rerun()
            
            if submit_button:
                # Validaciones
                if not username or not password or not full_name or not nif:
                    st.error("❌ Por favor completa todos los campos obligatorios")
                    return
                
                if password != password_confirm:
                    st.error("❌ Las contraseñas no coinciden")
                    return
                
                if len(password) < 4:
                    st.error("❌ La contraseña debe tener al menos 4 caracteres")
                    return
                
                # Cargar usuarios existentes
                users = load_users()
                
                if username in users:
                    st.error("❌ El usuario ya existe")
                    return
                
                # Crear nuevo usuario
                hashed_password = hash_password(password)
                users[username] = {
                    "password": hashed_password,
                    "full_name": full_name,
                    "nif": nif.upper(),
                    "workplace": workplace,
                    "company": company,
                    "created_at": datetime.now().isoformat()
                }
                
                # Guardar usuarios
                if save_users(users):
                    # Crear archivo de vacaciones inicial
                    vacation_data = {
                        "total_days": total_days,
                        "used_days": import_data.get('used_days', []) if import_data else [],
                        "custom_holidays": import_data.get('custom_holidays', []) if import_data else [],
                        "full_name": full_name,
                        "nif": nif.upper(),
                        "workplace": workplace,
                        "company": company
                    }
                    
                    update_vacation_data_on_github(username, vacation_data)
                    
                    success_msg = "✅ Cuenta creada exitosamente."
                    if import_data:
                        success_msg += f" Se importaron {len(vacation_data['used_days'])} días de vacaciones y {len(vacation_data['custom_holidays'])} festivos personalizados."
                    success_msg += " Ya puedes iniciar sesión."
                    
                    st.success(success_msg)
                    time.sleep(2)
                    st.session_state.show_register = False
                    st.rerun()
                else:
                    st.error("❌ Error al crear la cuenta. Inténtalo de nuevo.")

def login_form():
    """Formulario de login"""
    st.markdown("""
    <style>
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        background: linear-gradient(135deg, #e0f7f1 0%, #ffffff 100%);
        min-height: 100vh;
    }
    
    .main .block-container {
        background: black;
        padding-top: 8rem;
        padding-bottom: 2rem;
        max-width: 500px;
    }
    
    .login-title {
        text-align: center;
        color: #000;
        margin-bottom: 1.5rem;
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stHeader {display:none;}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🔐 Gestor de Horario 🗓️</div>', unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Usuario",
                placeholder="Ingresa tu usuario",
                label_visibility="collapsed"
            )
            
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submit_button = st.form_submit_button(
                "Iniciar Sesión",
                use_container_width=True,
                type="primary"
            )
            
            if submit_button:
                if username and password:
                    users = load_users()
                    hashed_password = hash_password(password)
                    
                    if username in users and users[username]["password"] == hashed_password:
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['user_data'] = users[username]
                        st.session_state['login_time'] = time.time()
                        st.success("✅ Credenciales correctas")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.warning("⚠️ Por favor, completa todos los campos")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📝 Crear nueva cuenta", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()

def logout():
    """Cerrar sesión"""
    for key in ['authenticated', 'username', 'user_data', 'login_time']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def check_session_timeout():
    """Verificar timeout de sesión"""
    if 'login_time' in st.session_state:
        SESSION_TIMEOUT = 28800
        if time.time() - st.session_state['login_time'] > SESSION_TIMEOUT:
            logout()
            st.warning("⏰ Sesión expirada")
            return False
    return True

def get_madrid_holidays(year, custom_days=[]):
    """Obtener festivos de Madrid"""
    madrid_holidays = holidays.Spain(years=year, subdiv='MD')
    for custom_day_dict in custom_days:
        try:
            if isinstance(custom_day_dict, dict):
                custom_date = datetime.strptime(custom_day_dict['date'], '%Y-%m-%d').date()
                custom_name = custom_day_dict.get('name', 'Festivo personalizado')
            else:
                # Compatibilidad con formato antiguo (solo string)
                custom_date = datetime.strptime(custom_day_dict, '%Y-%m-%d').date()
                custom_name = "Festivo personalizado"
            
            if custom_date.year == year:
                madrid_holidays.append({custom_date: custom_name})
        except (ValueError, KeyError):
            pass
    return madrid_holidays

def calculate_remaining_days(total_days, used_days):
    """Calcular días restantes"""
    return total_days - len(used_days)

def create_calendar_events(vacation_data, selected_year):
    """Crear eventos para calendario"""
    eventos = []
    
    festivos_madrid = get_madrid_holidays(selected_year, vacation_data.get('custom_holidays', []))
    
    for fecha, nombre in festivos_madrid.items():
        eventos.append({
            "title": f"🎉 {nombre}",
            "start": fecha.isoformat(),
            "allDay": True,
            "color": "#FF6B6B",
            "textColor": "white"
        })
    
    for fecha_str in vacation_data.get('used_days', []):
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            if fecha.year == selected_year:
                eventos.append({
                    "title": "🏖️ Vacaciones",
                    "start": fecha.isoformat(),
                    "allDay": True,
                    "color": "#4ECDC4",
                    "textColor": "white"
                })
        except ValueError:
            continue
    
    return eventos

def fill_pdf_template(selected_month, used_days, vacation_data):
    """Rellenar PDF con datos del usuario"""
    month_name = format_date(selected_month, "LLLL", locale="es").upper()
    OUTPUT_FILE = f'{month_name}_registro.pdf'

    with fitz.open(TEMPLATE_FILE) as doc:
        first_day = datetime(selected_month.year, selected_month.month, 1)
        last_day = datetime(selected_month.year, selected_month.month, calendar.monthrange(selected_month.year, selected_month.month)[1])
        madrid_holidays = get_madrid_holidays(selected_month.year, vacation_data['custom_holidays'])
        workdays = [
            day for day in pd.date_range(start=first_day, end=last_day)
            if day.weekday() < 5
        ]
        
        for page_index in range(len(doc)):
            target_page = doc[page_index]
            fields = list(target_page.widgets())
            
            if page_index == 0:
                for f in fields:
                    if f.field_name:
                        fname = f.field_name.upper()
                        if "MES" in fname:
                            f.field_value = month_name
                            f.update()
                        if "AÑO" in fname or "ANIO" in fname:
                            f.field_value = str(selected_month.year)
                            f.update()
                        if "CENTRO" in fname:
                            f.field_value = vacation_data.get('workplace', '')
                            f.update()
                        if "NIF" in fname:
                            f.field_value = vacation_data.get('nif', '')
                            f.update()
                        if "NOMBRE" in fname:
                            f.field_value = vacation_data.get('full_name', '')
                            f.update()
                        if "EMPRESA" in fname:
                            f.field_value = vacation_data.get('company', '')
                            f.update()
            
            cell_index = 5 if page_index == 0 else 0
            
            while cell_index < len(fields) and workdays:
                day = workdays.pop(0)
                day_str = day.day
                is_vacation = day.strftime('%Y-%m-%d') in used_days
                is_festivo = day in madrid_holidays
                
                fields[cell_index].field_value = str(day_str)
                fields[cell_index].update()
                
                if is_festivo:
                    if cell_index + 8 < len(fields):
                        fields[cell_index + 8].field_value = "FESTIVO"
                        fields[cell_index + 8].update()
                    cell_index += 9
                elif is_vacation:
                    if cell_index + 8 < len(fields):
                        fields[cell_index + 8].field_value = "VACACIONES"
                        fields[cell_index + 8].update()
                    cell_index += 9
                else:
                    if cell_index + 4 < len(fields):
                        fields[cell_index + 1].field_value = "9:00"
                        fields[cell_index + 2].field_value = "13:00"
                        fields[cell_index + 3].field_value = "14:00"
                        fields[cell_index + 4].field_value = "17:30"
                        fields[cell_index + 7].field_value = "7,5"
                        
                        fields[cell_index + 1].update()
                        fields[cell_index + 2].update()
                        fields[cell_index + 3].update()
                        fields[cell_index + 4].update()
                        fields[cell_index + 7].update()
                    cell_index += 9
                
                if not workdays:
                    break
        
        doc.save(OUTPUT_FILE)
    return OUTPUT_FILE

def main_app():
    """Aplicación principal"""
    username = st.session_state.get('username')
    user_data = st.session_state.get('user_data', {})
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f'🗓️ Hola, {user_data.get("full_name", username)}')
    with col2:
        if st.button("🚪 Cerrar Sesión", type="secondary"):
            logout()
    
    st.markdown("---")
    
    vacation_data = load_vacation_data(username)
    
    if not vacation_data:
        st.error("Error al cargar datos de vacaciones")
        print()
        return
    
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Botón para importar datos
        with st.expander("📥 Importar datos de vacaciones"):
            st.write("Importa días de vacaciones y festivos desde un archivo JSON")
            
            import_file = st.file_uploader(
                "Sube vacation_data.json",
                type=['json'],
                key="import_existing"
            )
            
            if import_file is not None:
                try:
                    imported_data = json.load(import_file)
                    
                    st.write("**Datos a importar:**")
                    st.write(f"- Días de vacaciones: {len(imported_data.get('used_days', []))}")
                    st.write(f"- Festivos personalizados: {len(imported_data.get('custom_holidays', []))}")
                    
                    col_imp1, col_imp2 = st.columns(2)
                    
                    with col_imp1:
                        if st.button("✅ Importar y reemplazar", type="primary"):
                            vacation_data['used_days'] = imported_data.get('used_days', [])
                            vacation_data['custom_holidays'] = imported_data.get('custom_holidays', [])
                            save_vacation_data(username, vacation_data)
                            st.success("✅ Datos importados correctamente")
                            st.rerun()
                    
                    with col_imp2:
                        if st.button("➕ Importar y combinar"):
                            # Combinar sin duplicados
                            existing_used = set(vacation_data['used_days'])
                            existing_holidays = set(vacation_data.get('custom_holidays', []))
                            
                            new_used = set(imported_data.get('used_days', []))
                            new_holidays = set(imported_data.get('custom_holidays', []))
                            
                            vacation_data['used_days'] = list(existing_used | new_used)
                            vacation_data['custom_holidays'] = list(existing_holidays | new_holidays)
                            
                            save_vacation_data(username, vacation_data)
                            st.success("✅ Datos combinados correctamente")
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"❌ Error al leer el archivo: {str(e)}")
        
        st.markdown("---")

        # Editar datos personales
        with st.expander("✏️ Editar datos personales"):
            st.write("Modifica tu información personal")
            
            new_full_name = st.text_input(
                "Nombre completo:",
                value=vacation_data.get('full_name', ''),
                key="edit_name"
            )
            
            new_nif = st.text_input(
                "NIF/DNI:",
                value=vacation_data.get('nif', ''),
                max_chars=9,
                key="edit_nif"
            )
            
            new_workplace = st.text_input(
                "Centro de trabajo:",
                value=vacation_data.get('workplace', ''),
                key="edit_workplace"
            )
            
            new_company = st.text_input(
                "Empresa:",
                value=vacation_data.get('company', ''),
                key="edit_company"
            )
            
            if st.button("💾 Guardar cambios", type="primary", key="save_personal_data"):
                # Actualizar vacation_data
                vacation_data['full_name'] = new_full_name
                vacation_data['nif'] = new_nif.upper()
                vacation_data['workplace'] = new_workplace
                vacation_data['company'] = new_company
                
                # Guardar en GitHub
                save_vacation_data(username, vacation_data)
                
                # Actualizar también en users.json
                users = load_users()
                if username in users:
                    users[username]['full_name'] = new_full_name
                    users[username]['nif'] = new_nif.upper()
                    users[username]['workplace'] = new_workplace
                    users[username]['company'] = new_company
                    save_users(users)
                
                st.success("✅ Datos actualizados correctamente")
                time.sleep(1)
                st.rerun()
        
        total_days = st.number_input(
            'Días laborables libres al año:',
            min_value=0,
            max_value=50,
            value=vacation_data['total_days'],
            help="Número total de días de vacaciones disponibles"
        )
        
        if total_days != vacation_data['total_days']:
            vacation_data['total_days'] = total_days
            save_vacation_data(username, vacation_data)
            st.success("Configuración actualizada")
        
        st.info("**Por contrato:** 30 días naturales por año trabajado")
        
        remaining_days = calculate_remaining_days(vacation_data['total_days'], vacation_data['used_days'])
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", vacation_data['total_days'])
        with col2:
            st.metric("Restantes", remaining_days)
        
        if st.button('🔄 Resetear Vacaciones', type="secondary"):
            vacation_data['used_days'] = []
            save_vacation_data(username, vacation_data)
            st.success('Días de vacaciones reseteados')
            st.rerun()
        
        # Exportar datos
        st.markdown("---")
        with st.expander("📤 Exportar datos"):
            st.write("Descarga tus datos de vacaciones como respaldo")
            
            export_data = {
                "total_days": vacation_data['total_days'],
                "used_days": vacation_data['used_days'],
                "custom_holidays": vacation_data.get('custom_holidays', [])
            }
            
            export_json = json.dumps(export_data, indent=4)
            
            st.download_button(
                label="⬇️ Descargar vacation_data.json",
                data=export_json,
                file_name=f"vacation_data_{username}.json",
                mime="application/json"
            )

    current_year = date.today().year
    
    year_col1, year_col2 = st.columns([3, 1])
    with year_col1:
        st.header(f'Registro de Jornada - Año {current_year}')
    with year_col2:
        selected_year = st.selectbox(
            "Año:",
            options=[current_year - 1, current_year, current_year + 1],
            index=1
        )
    
    eventos = create_calendar_events(vacation_data, selected_year)
    
    # Usar la fecha de hoy si el año seleccionado es el actual, si no enero
    today = date.today()
    initial_date = today.strftime('%Y-%m-%d') if selected_year == today.year else f"{selected_year}-01-01"
    
    calendar_config = {
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "selectable": True,
        "selectMirror": True,
        "dayMaxEvents": True,
        "weekends": True,
        "navLinks": True,
        "editable": False,
        "height": 600,
        "locale": "es",
        "initialDate": initial_date,
        "selectConstraint": {
            "start": f"{selected_year}-01-01",
            "end": f"{selected_year}-12-31"
        }
    }
    
    selected = my_calendar(
        events=eventos,
        options=calendar_config,
        key=f"calendar_{selected_year}"
    )
    
    if selected:
        if "dateClick" in selected:
            date_clicked = selected["dateClick"]["date"][:10]
            st.session_state.selected_date = date_clicked
        
        if "select" in selected:
            start_date = selected["select"]["start"][:10]
            end_date = selected["select"]["end"][:10]
            st.session_state.date_range = (start_date, end_date)
    
    st.markdown("---")
    st.header("➕ Gestionar Días de Vacaciones")
    
    tab1, tab2, tab3 = st.tabs(["📅 Selección Individual", "📊 Selección Múltiple", "🎉 Festivos Personalizados"])
    
    with tab1:
        if "selected_date" in st.session_state:
            st.info(f"Fecha seleccionada: {st.session_state.selected_date}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Añadir como Vacaciones", type="primary"):
                    if st.session_state.selected_date not in vacation_data["used_days"]:
                        vacation_data["used_days"].append(st.session_state.selected_date)
                        save_vacation_data(username, vacation_data)
                        st.success("Día añadido correctamente")
                        st.rerun()
                    else:
                        st.warning("Este día ya está registrado")
            
            with col2:
                if st.button("❌ Eliminar Vacaciones", type="secondary"):
                    if st.session_state.selected_date in vacation_data["used_days"]:
                        vacation_data["used_days"].remove(st.session_state.selected_date)
                        save_vacation_data(username, vacation_data)
                        st.success("Día eliminado correctamente")
                        st.rerun()
                    else:
                        st.warning("Este día no está registrado como vacaciones")
    
    with tab2:
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)
        
        date_range = st.date_input(
            "Selecciona el rango de fechas:",
            value=(start_date, end_date),
            min_value=start_date,
            max_value=end_date,
            help="Selecciona las fechas de inicio y fin"
        )
        
        if len(date_range) == 2:
            start_sel, end_sel = date_range
            days_in_range = []
            current_date = start_sel
            while current_date <= end_sel:
                if current_date.weekday() < 5:
                    days_in_range.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
            
            st.info(f"Días laborables en el rango: {len(days_in_range)}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Añadir Rango como Vacaciones", type="primary"):
                    added_days = 0
                    for day in days_in_range:
                        if day not in vacation_data["used_days"]:
                            vacation_data["used_days"].append(day)
                            added_days += 1
                    save_vacation_data(username, vacation_data)
                    st.success(f"Se añadieron {added_days} días de vacaciones")
                    st.rerun()
            
            with col2:
                if st.button("❌ Eliminar Rango de Vacaciones", type="secondary"):
                    removed_days = 0
                    for day in days_in_range:
                        if day in vacation_data["used_days"]:
                            vacation_data["used_days"].remove(day)
                            removed_days += 1
                    save_vacation_data(username, vacation_data)
                    st.success(f"Se eliminaron {removed_days} días de vacaciones")
                    st.rerun()
    
    with tab3:
        st.write("Añade días festivos personalizados:")
        
        custom_date = st.date_input(
            "Selecciona fecha para festivo personalizado:",
            min_value=date(selected_year, 1, 1),
            max_value=date(selected_year, 12, 31)
        )
        
        custom_name = st.text_input("Nombre del festivo:", placeholder="Ej: Día del patrón local")
        
        if st.button("➕ Añadir Festivo Personalizado"):
            if custom_name:
                custom_date_str = custom_date.strftime('%Y-%m-%d')
                # Verificar si ya existe
                already_exists = False
                for holiday in vacation_data.get('custom_holidays', []):
                    if isinstance(holiday, dict):
                        if holiday['date'] == custom_date_str:
                            already_exists = True
                            break
                    elif holiday == custom_date_str:
                        already_exists = True
                        break
                
                if not already_exists:
                    # Convertir formato antiguo si existe
                    if 'custom_holidays' not in vacation_data:
                        vacation_data['custom_holidays'] = []
                    
                    # Convertir strings antiguos a nuevo formato
                    new_holidays = []
                    for h in vacation_data['custom_holidays']:
                        if isinstance(h, str):
                            new_holidays.append({'date': h, 'name': 'Festivo personalizado'})
                        else:
                            new_holidays.append(h)
                    
                    # Añadir el nuevo festivo
                    new_holidays.append({'date': custom_date_str, 'name': custom_name})
                    vacation_data['custom_holidays'] = new_holidays
                    
                    save_vacation_data(username, vacation_data)
                    st.success(f"Festivo '{custom_name}' añadido")
                    st.rerun()
                else:
                    st.warning("Esta fecha ya está marcada como festivo")
            else:
                st.error("Por favor, introduce un nombre para el festivo")
    
    st.markdown("---")
    st.header("📄 Generar Informe Mensual")
    
    col1, col2 = st.columns(2)
    with col1:
        today = datetime.today()
        first_of_month = today.replace(day=1)
        last_month = first_of_month - timedelta(days=1)
        
        selected_month = st.date_input(
            'Selecciona el mes del informe:',
            value=last_month,
            min_value=date(selected_year, 1, 1),
            max_value=date(selected_year, 12, 31)
        )
    
    with col2:
        if st.button('Generar Informe PDF', type="primary"):
            try:
                output_pdf = fill_pdf_template(selected_month, vacation_data['used_days'], vacation_data)
                with open(output_pdf, 'rb') as f:
                    st.download_button(
                        label="⬇️ Descargar Informe",
                        data=f,
                        file_name=output_pdf,
                        mime="application/pdf"
                    )
                st.success("Informe generado correctamente")
            except Exception as e:
                st.error(f"Error al generar el informe: {str(e)}")
    
    st.markdown("---")
    st.header("Resumen")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Días de Vacaciones")
        vacation_dates = [d for d in vacation_data['used_days'] if datetime.strptime(d, '%Y-%m-%d').year == selected_year]
        vacation_dates.sort()
        
        if vacation_dates:
            for date_str in vacation_dates:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                st.write(f"• {date_obj.strftime('%d/%m/%Y')} - {date_obj.strftime('%A')}")
        else:
            st.write("No hay días de vacaciones registrados")
    
    with col2:
        st.subheader("Festivos Oficiales")
        festivos = get_madrid_holidays(selected_year)
        festivos_sorted = sorted(festivos.items())
        
        for fecha, nombre in festivos_sorted:
            st.write(f"• {fecha.strftime('%d/%m/%Y')} - {nombre}")
    
    with col3:
        st.subheader("Festivos Personalizados")
        custom_holidays_data = vacation_data.get('custom_holidays', [])
        custom_holidays_display = []
        
        for holiday in custom_holidays_data:
            if isinstance(holiday, dict):
                try:
                    date_obj = datetime.strptime(holiday['date'], '%Y-%m-%d')
                    if date_obj.year == selected_year:
                        custom_holidays_display.append({
                            'date': date_obj,
                            'name': holiday.get('name', 'Festivo personalizado')
                        })
                except ValueError:
                    pass
            else:
                # Formato antiguo (solo string)
                try:
                    date_obj = datetime.strptime(holiday, '%Y-%m-%d')
                    if date_obj.year == selected_year:
                        custom_holidays_display.append({
                            'date': date_obj,
                            'name': 'Festivo personalizado'
                        })
                except ValueError:
                    pass
        
        custom_holidays_display.sort(key=lambda x: x['date'])
        
        if custom_holidays_display:
            for holiday in custom_holidays_display:
                st.write(f"• {holiday['date'].strftime('%d/%m/%Y')} - {holiday['name']}")
        else:
            st.write("No hay festivos personalizados")

def main():
    """Función principal"""
    if check_authentication():
        if not check_session_timeout():
            return
    
    # Mostrar formulario de registro si está activado
    if st.session_state.get('show_register', False):
        register_form()
    # Mostrar login si no está autenticado
    elif not check_authentication():
        login_form()
    else:
        # Mostrar la aplicación principal
        main_app()

if __name__ == '__main__':
    main()

