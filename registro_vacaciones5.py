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

# Configuración de autenticación
AUTH_CONFIG = {
    # Puedes añadir múltiples usuarios aquí
    "1234": "1c91373624b65d0912ac16178d37ffc9376ed7d857b88258bc56c3a6599d0daa",  
}

# Archivo para almacenar los datos de vacaciones
DATA_FILE = 'vacation_data.json'
TEMPLATE_FILE = 'horas_registro.pdf'
OUTPUT_FILE = 'horas_registro_rellenado.pdf'

def hash_password(password):
    """Hash de la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_authentication():
    """Verificar si el usuario está autenticado"""
    return st.session_state.get('authenticated', False)

def login_form():
    """Mostrar formulario de login"""
    # Ocultar elementos de Streamlit y crear página de login limpia
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
    
    .login-subtitle {
        text-align: center;
        color: #000;
        margin-bottom: 2rem;
        font-size: 1rem;
    }
    
    /* Ocultar el menú de Streamlit */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stHeader {display:none;}
    </style>
    """, unsafe_allow_html=True)
    
    # Centrar el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown('<div class="login-title">🔐 Acceso al sistema de gestor de horario 🗓️</div>', unsafe_allow_html=True)
        
        # Inicializar estado para mostrar/ocultar contraseña
        if 'show_password' not in st.session_state:
            st.session_state.show_password = False
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Usuario", 
                placeholder="Ingresa tu usuario",
                label_visibility="collapsed"
            )
            
            # Contraseña con botón para mostrar/ocultar
            password_container = st.container()
            with password_container:
                col_pass, col_eye = st.columns([4, 1])
                
                with col_pass:
                    password_type = "text" if st.session_state.show_password else "password"
                    password = st.text_input(
                        "Contraseña",
                        type=password_type,
                        placeholder="Ingresa tu contraseña",
                        label_visibility="collapsed"
                    )
                
    
            
            # Espaciado
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Botón de submit
            submit_button = st.form_submit_button(
                "Iniciar Sesión", 
                use_container_width=True,
                type="primary"
            )
            
            # Procesar login
            if submit_button:
                if username and password:
                    hashed_password = hash_password(password)
                    
                    if username in AUTH_CONFIG and AUTH_CONFIG[username] == hashed_password:
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['login_time'] = time.time()
                        st.success("✅ Credenciales correctas")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.warning("⚠️ Por favor, completa todos los campos")
        
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    """Cerrar sesión"""
    for key in ['authenticated', 'username', 'login_time']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def check_session_timeout():
    """Verificar si la sesión ha expirado (opcional)"""
    if 'login_time' in st.session_state:
        # Sesión expira después de 8 horas (28800 segundos)
        SESSION_TIMEOUT = 28800
        if time.time() - st.session_state['login_time'] > SESSION_TIMEOUT:
            logout()
            st.warning("⏰ Sesión expirada. Por favor, inicia sesión nuevamente.")
            return False
    return True

def get_madrid_holidays(year, custom_days=[]):
    """Obtener festivos de Madrid para un año específico."""
    madrid_holidays = holidays.Spain(years=year, subdiv='MD')  # 'MD' es Madrid
    for custom_day_str in custom_days:
        try:
            custom_date = datetime.strptime(custom_day_str, '%Y-%m-%d').date()
            if custom_date.year == year:
                madrid_holidays.append({custom_date: "Festivo personalizado"})
        except ValueError:
            pass
    return madrid_holidays

def load_vacation_data():
    """Cargar datos de vacaciones desde el archivo JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'total_days': 22,  # Días laborables libres por defecto
        'used_days': [],
        'custom_holidays': []
    }

def save_vacation_data(data):
    """Guardar datos de vacaciones en el archivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_remaining_days(total_days, used_days):
    """Calcular días de vacaciones restantes."""
    return total_days - len(used_days)

def create_calendar_events(vacation_data, selected_year):
    """Crear eventos para el calendario."""
    eventos = []
    
    # Obtener festivos de Madrid
    festivos_madrid = get_madrid_holidays(selected_year, vacation_data.get('custom_holidays', []))
    
    # Añadir festivos al calendario
    for fecha, nombre in festivos_madrid.items():
        eventos.append({
            "title": f"🎉 {nombre}",
            "start": fecha.isoformat(),
            "allDay": True,
            "color": "#FF6B6B",  # Rojo para festivos
            "textColor": "white"
        })
    
    # Añadir días de vacaciones
    for fecha_str in vacation_data.get('used_days', []):
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            if fecha.year == selected_year:
                eventos.append({
                    "title": "🏖️ Vacaciones",
                    "start": fecha.isoformat(),
                    "allDay": True,
                    "color": "#4ECDC4",  # Azul verdoso para vacaciones
                    "textColor": "white"
                })
        except ValueError:
            continue
    
    return eventos

def fill_pdf_template(selected_month, used_days, vacation_data):
    """Rellenar todas las páginas del formulario PDF usando PyMuPDF."""
    month_name = format_date(selected_month, "LLLL", locale="es").upper()
    OUTPUT_FILE = f'{month_name}_registro.pdf'

    with fitz.open(TEMPLATE_FILE) as doc:
        # Calcular los días laborables del mes seleccionado
        first_day = datetime(selected_month.year, selected_month.month, 1)
        last_day = datetime(selected_month.year, selected_month.month, calendar.monthrange(selected_month.year, selected_month.month)[1])
        madrid_holidays = get_madrid_holidays(selected_month.year, vacation_data['custom_holidays'])
        workdays = [
            day for day in pd.date_range(start=first_day, end=last_day)
            if day.weekday() < 5
        ]
        
        # Iterar sobre todas las páginas del documento
        for page_index in range(len(doc)):
            target_page = doc[page_index]
            fields = list(target_page.widgets())
            
            # En la primera página, escribir el mes
            if page_index == 0 and len(fields) > 4:
                fields[4].field_value = month_name
                fields[4].update()
            
            # Determinar el índice inicial de la página
            cell_index = 5 if page_index == 0 else 0
            
            # Continuar rellenando días para esta página
            while cell_index < len(fields) and workdays:
                day = workdays.pop(0)
                day_str = day.day
                is_vacation = day.strftime('%Y-%m-%d') in used_days
                is_festivo = day in madrid_holidays
                
                # Rellenar las celdas
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
                        
                        fields[cell_index + 1].update()
                        fields[cell_index + 2].update()
                        fields[cell_index + 3].update()
                        fields[cell_index + 4].update()
                    cell_index += 9
                
                if not workdays:
                    break
        
        doc.save(OUTPUT_FILE)
    return OUTPUT_FILE

def main_app():
    """Aplicación principal (solo se ejecuta si está autenticado)"""
    # Header con información de usuario
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title('🗓️ Seguimiento de Vacaciones')
    with col2:
        if st.button("🚪 Cerrar Sesión", type="secondary"):
            logout()
    
    st.markdown("---")
    
    # Cargar datos existentes
    vacation_data = load_vacation_data()
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Configuración de días totales
        total_days = st.number_input(
            'Días laborables libres al año:',
            min_value=0,
            max_value=50,
            value=vacation_data['total_days'],
            help="Número total de días de vacaciones disponibles"
        )
        
        if total_days != vacation_data['total_days']:
            vacation_data['total_days'] = total_days
            save_vacation_data(vacation_data)
            st.success("Configuración actualizada")
        
        st.info("**Por contrato:** 30 días naturales por año trabajado")
        
        # Resumen de días
        remaining_days = calculate_remaining_days(vacation_data['total_days'], vacation_data['used_days'])
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", vacation_data['total_days'])
        with col2:
            st.metric("Restantes", remaining_days)
        
        # Botón para resetear
        if st.button('🔄 Resetear Vacaciones', type="secondary"):
            vacation_data['used_days'] = []
            save_vacation_data(vacation_data)
            st.success('Días de vacaciones reseteados')
            st.rerun()

    # Contenido principal
    current_year = date.today().year
    
    # Selector de año
    year_col1, year_col2 = st.columns([3, 1])
    with year_col1:
        st.header(f'Calendario de Vacaciones {current_year}')
    with year_col2:
        selected_year = st.selectbox(
            "Año:",
            options=[current_year - 1, current_year, current_year + 1],
            index=1
        )
    
    # Crear eventos del calendario
    eventos = create_calendar_events(vacation_data, selected_year)
    
    # Configuración del calendario mejorada
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
        "initialDate": f"{selected_year}-01-01",
        "selectConstraint": {
            "start": f"{selected_year}-01-01",
            "end": f"{selected_year}-12-31"
        }
    }
    
    # Mostrar calendario
    selected = my_calendar(
        events=eventos,
        options=calendar_config,
        key=f"calendar_{selected_year}"
    )
    
    # Procesar selección del calendario
    if selected:
        if "dateClick" in selected:
            date_clicked = selected["dateClick"]["date"][:10]
            st.session_state.selected_date = date_clicked
        
        if "select" in selected:
            start_date = selected["select"]["start"][:10]
            end_date = selected["select"]["end"][:10]
            st.session_state.date_range = (start_date, end_date)
    
    # Sección para añadir días
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
                        save_vacation_data(vacation_data)
                        st.success("Día añadido correctamente")
                        st.rerun()
                    else:
                        st.warning("Este día ya está registrado")
            
            with col2:
                if st.button("❌ Eliminar Vacaciones", type="secondary"):
                    if st.session_state.selected_date in vacation_data["used_days"]:
                        vacation_data["used_days"].remove(st.session_state.selected_date)
                        save_vacation_data(vacation_data)
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
            help="Selecciona las fechas de inicio y fin para añadir vacaciones"
        )
        
        if len(date_range) == 2:
            start_sel, end_sel = date_range
            days_in_range = []
            current_date = start_sel
            while current_date <= end_sel:
                if current_date.weekday() < 5:  # Solo días laborables
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
                    save_vacation_data(vacation_data)
                    st.success(f"Se añadieron {added_days} días de vacaciones")
                    st.rerun()
            
            with col2:
                if st.button("❌ Eliminar Rango de Vacaciones", type="secondary"):
                    removed_days = 0
                    for day in days_in_range:
                        if day in vacation_data["used_days"]:
                            vacation_data["used_days"].remove(day)
                            removed_days += 1
                    save_vacation_data(vacation_data)
                    st.success(f"Se eliminaron {removed_days} días de vacaciones")
                    st.rerun()
    
    with tab3:
        st.write("Añade días festivos personalizados que no están en el calendario oficial:")
        
        custom_date = st.date_input(
            "Selecciona fecha para festivo personalizado:",
            min_value=date(selected_year, 1, 1),
            max_value=date(selected_year, 12, 31)
        )
        
        custom_name = st.text_input("Nombre del festivo:", placeholder="Ej: Día del patrón local")
        
        if st.button("➕ Añadir Festivo Personalizado"):
            if custom_name:
                custom_date_str = custom_date.strftime('%Y-%m-%d')
                if custom_date_str not in vacation_data['custom_holidays']:
                    vacation_data['custom_holidays'].append(custom_date_str)
                    save_vacation_data(vacation_data)
                    st.success(f"Festivo '{custom_name}' añadido para {custom_date}")
                    st.rerun()
                else:
                    st.warning("Esta fecha ya está marcada como festivo personalizado")
            else:
                st.error("Por favor, introduce un nombre para el festivo")
    
    # Sección de informes
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
    
    # Mostrar resumen
    st.markdown("---")
    st.header("Resumen")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏖️ Días de Vacaciones")
        vacation_dates = [d for d in vacation_data['used_days'] if datetime.strptime(d, '%Y-%m-%d').year == selected_year]
        vacation_dates.sort()
        
        if vacation_dates:
            for date_str in vacation_dates:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                st.write(f"• {date_obj.strftime('%d/%m/%Y')} - {date_obj.strftime('%A')}")
        else:
            st.write("No hay días de vacaciones registrados")
    
    with col2:
        st.subheader("🎉 Festivos Oficiales")
        festivos = get_madrid_holidays(selected_year)
        festivos_sorted = sorted(festivos.items())
        
        for fecha, nombre in festivos_sorted:
            st.write(f"• {fecha.strftime('%d/%m/%Y')} - {nombre}")
    
    with col3:
        st.subheader("🏛️ Festivos Personalizados")
        custom_holidays = [d for d in vacation_data.get('custom_holidays', []) if datetime.strptime(d, '%Y-%m-%d').year == selected_year]
        custom_holidays.sort()
        
        if custom_holidays:
            for date_str in custom_holidays:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                st.write(f"• {date_obj.strftime('%d/%m/%Y')} - Festivo personalizado")
        else:
            st.write("No hay festivos personalizados")

def main():
    """Función principal que controla la autenticación y la aplicación"""
    # Verificar timeout de sesión
    if check_authentication():
        if not check_session_timeout():
            return
    
    # Mostrar login si no está autenticado
    if not check_authentication():
        login_form()
    else:
        # Mostrar la aplicación principal
        main_app()

if __name__ == '__main__':
    main()