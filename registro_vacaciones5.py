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

def simple_recovery_form():
    """Recuperación simple solo con DNI"""
    st.markdown("""
    <style>
    .recovery-title {
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
        st.markdown('<div class="recovery-title">🔑 Recuperar Acceso</div>', unsafe_allow_html=True)
        
        st.info("💡 Solo necesitas tu DNI/NIF para recuperar tu cuenta")
        
        with st.form("simple_recovery_form", clear_on_submit=False):
            search_dni = st.text_input(
                "DNI/NIF",
                placeholder="Ej: 12345678X",
                help="Ingresa tu DNI/NIF registrado (sin espacios)",
                max_chars=9
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submit_button = st.form_submit_button(
                    "🔍 Buscar mi cuenta",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_btn2:
                cancel_button = st.form_submit_button(
                    "Cancelar",
                    use_container_width=True
                )
            
            if cancel_button:
                st.session_state.show_simple_recovery = False
                st.rerun()
            
            if submit_button:
                if not search_dni:
                    st.error("❌ Por favor ingresa tu DNI/NIF")
                    return
                
                search_dni = search_dni.upper()
                users = load_users()
                found_user = None
                found_username = None
                
                # Buscar usuario por DNI
                for username, user_data in users.items():
                    if user_data.get('nif', '').upper() == search_dni:
                        found_user = user_data
                        found_username = username
                        break
                
                if found_user:
                    st.session_state['recovery_user'] = found_username
                    st.session_state['recovery_data'] = found_user
                    st.rerun()
                else:
                    st.error(f"❌ No se encontró ninguna cuenta con el DNI: {search_dni}")
        
        # Si encontró usuario, mostrar formulario de reset
        if 'recovery_user' in st.session_state:
            st.markdown("---")
            st.success(f"✅ Cuenta encontrada: **{st.session_state['recovery_data'].get('full_name', 'N/A')}**")
            st.info(f"👤 Tu usuario es: **{st.session_state['recovery_user']}**")
            
            st.markdown("### 🔒 Establecer Nueva Contraseña")
            
            with st.form("set_new_password", clear_on_submit=False):
                new_password = st.text_input(
                    "Nueva contraseña:",
                    type="password",
                    placeholder="Mínimo 4 caracteres"
                )
                
                confirm_password = st.text_input(
                    "Confirmar contraseña:",
                    type="password",
                    placeholder="Repite la contraseña"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.form_submit_button("💾 Restablecer Contraseña", type="primary", use_container_width=True):
                    if not new_password or not confirm_password:
                        st.error("❌ Completa ambos campos")
                    elif new_password != confirm_password:
                        st.error("❌ Las contraseñas no coinciden")
                    elif len(new_password) < 4:
                        st.error("❌ La contraseña debe tener al menos 4 caracteres")
                    else:
                        username = st.session_state['recovery_user']
                        users = load_users()
                        users[username]['password'] = hash_password(new_password)
                        
                        if save_users(users):
                            st.success(f"""
                            ✅ **¡Contraseña restablecida correctamente!**
                            
                            📋 Tus datos de acceso:
                            - **Usuario:** {username}
                            - **Contraseña:** (la que acabas de crear)
                            
                            Ya puedes iniciar sesión.
                            """)
                            
                            # Limpiar datos de recuperación
                            del st.session_state['recovery_user']
                            del st.session_state['recovery_data']
                            
                            time.sleep(3)
                            st.session_state.show_simple_recovery = False
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar la contraseña. Inténtalo de nuevo.")

def admin_panel():
    """Panel de administrador para buscar usuarios por DNI"""
    st.markdown("""
    <style>
    .admin-title {
        text-align: center;
        color: #FF6B6B;
        margin-bottom: 1.5rem;
        font-size: 1.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="admin-title">👨‍💼 Panel de Administrador</div>', unsafe_allow_html=True)
        
        # Autenticación de admin
        if not st.session_state.get('admin_authenticated', False):
            with st.form("admin_login"):
                admin_user = st.text_input("Usuario Admin", placeholder="admin")
                admin_pass = st.text_input("Contraseña Admin", type="password")
                
                col_adm1, col_adm2 = st.columns(2)
                
                with col_adm1:
                    login_btn = st.form_submit_button("Acceder", type="primary", use_container_width=True)
                
                with col_adm2:
                    cancel_btn = st.form_submit_button("Volver", use_container_width=True)
                
                if cancel_btn:
                    st.session_state.show_admin = False
                    st.rerun()
                
                if login_btn:
                    try:
                        if (admin_user == st.secrets.get("ADMIN_USERNAME", "admin") and 
                            admin_pass == st.secrets.get("ADMIN_PASSWORD", "admin123")):
                            st.session_state['admin_authenticated'] = True
                            st.success("✅ Acceso concedido")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas")
                    except:
                        st.error("❌ Configuración de admin no encontrada en secrets")
        else:
            # Panel de búsqueda
            st.markdown("### 🔍 Buscar Usuario por DNI/NIF")
            
            search_dni = st.text_input(
                "Ingresa el DNI/NIF:",
                placeholder="12345678X",
                max_chars=9
            ).upper()
            
            if st.button("🔍 Buscar", type="primary"):
                if search_dni:
                    users = load_users()
                    found_users = []
                    
                    # Buscar en users.json
                    for username, user_data in users.items():
                        if user_data.get('nif', '').upper() == search_dni:
                            found_users.append({
                                'username': username,
                                'full_name': user_data.get('full_name', 'N/A'),
                                'nif': user_data.get('nif', 'N/A'),
                                'workplace': user_data.get('workplace', 'N/A'),
                                'company': user_data.get('company', 'N/A'),
                                'created_at': user_data.get('created_at', 'N/A')
                            })
                    
                    if found_users:
                        st.success(f"✅ Se encontraron {len(found_users)} usuario(s)")
                        
                        for user in found_users:
                            st.markdown("---")
                            st.markdown("### 📋 Información del Usuario")
                            
                            col_info1, col_info2 = st.columns(2)
                            
                            with col_info1:
                                st.write(f"**Usuario:** {user['username']}")
                                st.write(f"**Nombre:** {user['full_name']}")
                                st.write(f"**DNI/NIF:** {user['nif']}")
                            
                            with col_info2:
                                st.write(f"**Centro:** {user['workplace']}")
                                st.write(f"**Empresa:** {user['company']}")
                                st.write(f"**Creado:** {user['created_at'][:10] if user['created_at'] != 'N/A' else 'N/A'}")
                            
                            st.warning("⚠️ **NOTA:** Las contraseñas están encriptadas y NO se pueden recuperar. Solo se pueden restablecer.")
                            
                            # Formulario para restablecer contraseña
                            with st.expander("🔑 Restablecer Contraseña"):
                                new_pwd = st.text_input(
                                    "Nueva contraseña:",
                                    type="password",
                                    key=f"new_pwd_{user['username']}"
                                )
                                
                                confirm_pwd = st.text_input(
                                    "Confirmar contraseña:",
                                    type="password",
                                    key=f"confirm_pwd_{user['username']}"
                                )
                                
                                if st.button(f"💾 Restablecer para {user['username']}", key=f"reset_{user['username']}"):
                                    if not new_pwd or not confirm_pwd:
                                        st.error("❌ Completa ambos campos")
                                    elif new_pwd != confirm_pwd:
                                        st.error("❌ Las contraseñas no coinciden")
                                    elif len(new_pwd) < 4:
                                        st.error("❌ Mínimo 4 caracteres")
                                    else:
                                        users[user['username']]['password'] = hash_password(new_pwd)
                                        if save_users(users):
                                            st.success(f"✅ Contraseña restablecida para {user['username']}")
                                            st.info(f"📧 Comunica al usuario: Usuario={user['username']}, Contraseña={new_pwd}")
                                        else:
                                            st.error("❌ Error al guardar")
                    else:
                        st.error(f"❌ No se encontró ningún usuario con el DNI: {search_dni}")
                else:
                    st.warning("⚠️ Ingresa un DNI/NIF")
            
            st.markdown("---")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📊 Ver Todos los Usuarios"):
                    users = load_users()
                    st.markdown("### 👥 Todos los Usuarios")
                    
                    users_list = []
                    for username, data in users.items():
                        users_list.append({
                            'Usuario': username,
                            'Nombre': data.get('full_name', 'N/A'),
                            'DNI': data.get('nif', 'N/A'),
                            'Empresa': data.get('company', 'N/A')
                        })
                    
                    if users_list:
                        df = pd.DataFrame(users_list)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No hay usuarios registrados")
            
            with col_btn2:
                if st.button("🚪 Cerrar Admin"):
                    st.session_state.admin_authenticated = False
                    st.session_state.show_admin = False
                    st.rerun()

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
        
        # BOTONES DE NAVEGACIÓN
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("📝 Crear cuenta", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()
        
        with col_btn2:
            if st.button("🔑 Recuperar acceso", use_container_width=True):
                st.session_state.show_simple_recovery = True
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # BOTÓN ADMIN
        if st.button("👨‍💼 Acceso Admin", use_container_width=True, type="secondary"):
            st.session_state.show_admin = True
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
                    "color
