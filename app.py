import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time
import qrcode
from io import BytesIO
import urllib.parse
import socket

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.100.5"
IP_LOCAL = get_ip()

LINK_NUBE = "https://azulgrana-roga.streamlit.app/?pagina=portal"
LINK_BASE = "https://azulgrana-roga.streamlit.app"
TELEFONO_ALBERGUE = "595981531063" # <-- CAMBIA ACA POR EL NUMERO DE BACILIO CON 595

st.set_page_config(page_title="Azulgrana Róga", layout="wide", page_icon="🏠")

st.markdown("""
    <style>
.stApp {background-color: #001F3F;}
    [data-testid="stSidebar"] {background-color: #00004B;}
    [data-testid="stSidebar"] * {color: white;}
.stButton>button {background-color: #FF0000;color: white;border-radius: 10px;border: 2px solid #00529F;font-weight: bold;}
.stButton>button:hover {background-color: #00529F;color: white;border: 2px solid #FF0000;}
    h1, h2, h3 {color: #00529F; font-weight: bold;}
    [data-testid="stDataFrame"] {background-color: white!important;}
    [data-testid="stDataFrame"] * {color: black!important;}
    #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none!important;}
   .stDeployButton, [data-testid="stDeployButton"], [data-testid="stAppDeployButton"], a[href*="deploy"] {display:none!important; visibility:hidden!important; width:0!important; height:0!important;}
    button[title="View fullscreen"], [data-testid="StyledFullScreenButton"] {display: none!important;}
    header, [data-testid="stHeader"] {background: #001F3F!important;}
    [data-testid="stToolbar"] {visibility: visible!important; display: block!important;}
    </style>
    """, unsafe_allow_html=True)

NOMBRE_ALBERGUE = "Fundación Club Cerro Porteño"
NOMBRE_SEDE = "Azulgrana Róga"
ROLES = ["Director", "Encargado/a del Albergue", "Trabajador/a Social", "Médico/a", "Psicólogo/a", "Tutor", "CEO"]

conn = sqlite3.connect('albergue.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (documento TEXT PRIMARY KEY, nombre TEXT, password TEXT, rol TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS jovenes (id INTEGER PRIMARY KEY AUTOINCREMENT, documento TEXT, nombres TEXT, apellidos TEXT, fecha_nac DATE, ciudad TEXT, barrio TEXT, direccion TEXT, telefono TEXT, responsable TEXT, parentesco TEXT, tel_responsable TEXT, fecha_ingreso DATE, estado TEXT, habitacion TEXT, cama TEXT, colegio TEXT, grado TEXT, deporte TEXT, posicion TEXT, categoria TEXT, turno TEXT, foto_url TEXT, motivo_ingreso TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS permisos (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha_sol DATE, fecha_salida DATE, hora_salida TEXT, fecha_regreso DATE, hora_regreso TEXT, tipo_salida TEXT, destino TEXT, persona_salida TEXT, parentesco TEXT, tel_contacto TEXT, motivo TEXT, estado TEXT DEFAULT 'Pendiente', hora_regreso_real TEXT, qr_id TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, adolescente TEXT, contacto TEXT, tipo TEXT, mensaje TEXT, estado TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS contactos (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, nombres TEXT, apellidos TEXT, cargo TEXT, rol TEXT, telefono TEXT, observacion TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, desarrollo TEXT, rutinas TEXT, infraestructura TEXT, observaciones TEXT, necesidad TEXT, prioridad TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria_joven (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha DATE, informe TEXT)''')
c.execute("INSERT OR IGNORE INTO mensajes (id, tipo, mensaje) VALUES (1, 'Predeterminado', 'Hola. Su hijo/a {nombre} ha solicitado permiso de salida del albergue Azulgrana Róga. Destino: {destino} - Fecha: {fecha_salida} {hora_salida}.')")
c.execute("INSERT OR IGNORE INTO usuarios (documento, nombre, password, rol) VALUES ('admin', 'Administrador', 'cerro2026', 'Director')")
conn.commit()

def generar_qr(data):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def limpiar_numero(num):
    num = ''.join(filter(str.isdigit, str(num)))
    if num.startswith('0'):
        num = '595' + num[1:]
    return num

if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'modo_proyeccion' not in st.session_state:
    st.session_state.modo_proyeccion = False

# --- 1. MANEJO DE APROBACION POR LINK DEL RESPONSABLE ---
accion = str(st.query_params.get("accion", "")).lower()
id_accion = st.query_params.get("id", "")
if accion in ["aprobar", "rechazar"] and id_accion:
    nuevo_estado = "Aprobado" if accion == "aprobar" else "Rechazado"
    try:
        c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo_estado, int(id_accion)))
        conn.commit()
        info = pd.read_sql("SELECT j.nombres, j.apellidos, j.responsable, p.destino, p.fecha_salida FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE p.id=?", conn, params=(int(id_accion),))
        if not info.empty:
            nom = f"{info.iloc[0]['nombres']} {info.iloc[0]['apellidos']}"
            resp = info.iloc[0]['responsable']
            dest = info.iloc[0]['destino']
            texto_aviso = f"AVISO ALBERGUE AZULGRANA ROGA: El responsable {resp} ha {nuevo_estado.upper()} la salida de {nom} con destino a {dest}. ID: {id_accion}"
            c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), nom, "Albergue", f"Respuesta {nuevo_estado}", texto_aviso, nuevo_estado))
            conn.commit()
            url_aviso = f"https://wa.me/{TELEFONO_ALBERGUE}?text={urllib.parse.quote(texto_aviso)}"
            st.markdown(f"<h1 style='color:white; text-align:center; margin-top:50px;'>✅ Solicitud {id_accion} {nuevo_estado}</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='color:white; text-align:center;'>Gracias {resp} por responder.<br>Ahora avisá al albergue.</h3>", unsafe_allow_html=True)
            st.link_button(f"📲 Avisar al Albergue que fue {nuevo_estado}", url_aviso, type="primary", use_container_width=True)
            st.balloons()
            st.stop()
        else:
            st.success(f"Solicitud {nuevo_estado}")
            st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# --- 2. PORTAL JOVEN ---
pagina_qr = str(st.query_params.get("pagina", "")).lower()
if pagina_qr in ["portal", "portal joven"]:
    st.markdown(f"<h1 style='color:white;'>Portal del Joven - {NOMBRE_SEDE}</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Solicitar Salida", "Consultar Estado", "Marcar Regreso"])
    with tab1:
        doc_qr = st.text_input("Ingresá tu documento", key="doc_solicitar")
        if doc_qr:
            joven_qr = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc_qr,))
            if joven_qr.empty:
                st.error("Documento no encontrado")
            else:
                jd = joven_qr.iloc[0]
                if jd['estado']!= "Actual":
                    st.error(f"{jd['nombres']} no está ACTIVO")
                else:
                    st.success(f"Bienvenido {jd['nombres']} {jd['apellidos']}")
                    plantilla_row = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn)
                    plantilla = plantilla_row.iloc[0]['mensaje'] if not plantilla_row.empty else "Solicitud de salida de {nombre} a {destino}"
                    with st.form("form_qr_publico"):
                        c1,c2 = st.columns(2)
                        with c1:
                            fecha_salida = st.date_input("Fecha de salida")
                            hora_salida = st.time_input("Hora de salida")
                            fecha_regreso = st.date_input("Fecha de regreso")
                            hora_regreso = st.time_input("Hora de regreso")
                        with c2:
                            tipo_salida = st.selectbox("Tipo de salida", ["Familiar","Médico","Deportivo","Personal","Otro"])
                            destino = st.text_input("Destino *")
                            persona = st.text_input("Persona con quien saldrá")
                            motivo = st.text_area("Motivo")
                        if st.form_submit_button("Enviar solicitud", type="primary", use_container_width=True):
                            if not destino:
                                st.warning("Destino obligatorio")
                            else:
                                c.execute("INSERT INTO permisos (joven_id,fecha_sol,fecha_salida,hora_salida,fecha_regreso,hora_regreso,tipo_salida,destino,persona_salida,motivo,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                (jd['id'], str(date.today()), str(fecha_salida), str(hora_salida), str(fecha_regreso), str(hora_regreso), tipo_salida, destino, persona, motivo, "Pendiente"))
                                conn.commit()
                                id_nuevo = c.lastrowid
                                texto_base = plantilla.replace("{nombre}", f"{jd['nombres']} {jd['apellidos']}").replace("{destino}", destino).replace("{fecha_salida}", str(fecha_salida)).replace("{hora_salida}", str(hora_salida)).replace("{motivo}", motivo)
                                link_aprobar = f"{LINK_BASE}/?accion=aprobar&id={id_nuevo}"
                                link_rechazar = f"{LINK_BASE}/?accion=rechazar&id={id_nuevo}"
                                texto_final = f"{texto_base}\n\n✅ Para APROBAR toque: {link_aprobar}\n❌ Para RECHAZAR toque: {link_rechazar}\n\nDestino: {destino}\nSalida: {fecha_salida} {hora_salida}\nRegreso: {fecha_regreso} {hora_regreso}\nMotivo: {motivo}"
                                tel = limpiar_numero(jd['tel_responsable'])
                                url_wp = f"https://wa.me/{tel}?text={urllib.parse.quote(texto_final)}"
                                st.success("✅ Solicitud enviada. Se generó el WhatsApp automático.")
                                st.link_button(f"📱 Enviar WhatsApp a {jd['responsable']}", url_wp, use_container_width=True)
                                c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"{jd['nombres']} {jd['apellidos']}", jd['responsable'], "Salida", texto_final, "Pendiente"))
                                conn.commit()
    with tab2:
        doc_cons_qr = st.text_input("Ingresá tu documento para consultar", key="doc_consultar")
        if doc_cons_qr:
            df_est = pd.read_sql("SELECT p.id, p.fecha_sol, p.destino, p.estado, p.hora_regreso_real FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE j.documento=? ORDER BY p.id DESC", conn, params=(doc_cons_qr,))
            if df_est.empty:
                st.warning("No tenés solicitudes")
            else:
                st.dataframe(df_est, use_container_width=True)
    with tab3:
        doc_ret_qr = st.text_input("Ingresá tu documento para marcar regreso", key="doc_regreso")
        if doc_ret_qr:
            df_pend_qr = pd.read_sql("SELECT p.id, p.fecha_salida, p.destino FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE j.documento=? AND p.estado='Aprobado' AND (p.hora_regreso_real IS NULL OR p.hora_regreso_real='')", conn, params=(doc_ret_qr,))
            if df_pend_qr.empty:
                st.info("No tenés salidas pendientes")
            else:
                st.dataframe(df_pend_qr, use_container_width=True)
                id_ret_qr = st.selectbox("ID a marcar", df_pend_qr['id'].tolist(), key="id_ret")
                if st.button("✅ Ya regresé al albergue", type="primary", use_container_width=True):
                    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("UPDATE permisos SET hora_regreso_real=? WHERE id=?", (ahora, id_ret_qr))
                    conn.commit()
                    st.success(f"¡Bienvenido! Regreso: {ahora}")
                    st.balloons()
    st.stop()

def login():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,5,1])
    with col2:
        st.image("Logo.png", width=100)
        st.markdown(f"<h2 style='color:white;'>{NOMBRE_ALBERGUE}</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#00529F;'>{NOMBRE_SEDE}</h3>", unsafe_allow_html=True)
        documento = st.text_input("Documento de usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            user = pd.read_sql("SELECT * FROM usuarios WHERE documento=? AND password=?", conn, params=(documento, password))
            if not user.empty:
                st.session_state.usuario = user.iloc[0]['nombre']
                st.session_state.rol = user.iloc[0]['rol']
                st.rerun()
            else:
                st.error("Documento o contraseña incorrecta")

def app():
    st.sidebar.image("Logo.png", width=120)
    st.sidebar.title(f"🏠 {NOMBRE_SEDE}")
    st.sidebar.markdown(f"**{st.session_state.rol.upper()}** | {st.session_state.usuario}")
    menu_base = ["Panel de Control", "Lista de Usuarios", "Jovenes", "Permisos", "Mensajería", "Informe Tutoría", "Reportes", "QR de Acceso", "WhatsApp Web"]
    if st.session_state.rol == "Director":
        menu_admin = ["Crear Usuarios", "Portal Joven", "Contactos del Albergue"]
        MENU = menu_base + menu_admin
    else:
        MENU = menu_base
    pagina = st.sidebar.radio("Menú", MENU, key="menu_principal")
    if st.sidebar.button("Cerrar Sesión", use_container_width=True, type="primary"):
        st.session_state.usuario = None
        st.session_state.rol = None
        st.session_state.modo_proyeccion = False
        st.rerun()

    if pagina == "Panel de Control":
        st.title("Panel de Control")
        df_j = pd.read_sql("SELECT * FROM jovenes", conn)
        df_p = pd.read_sql("SELECT * FROM permisos", conn)
        en_albergue = len(df_j[df_j['estado']=="Actual"]) if not df_j.empty else 0
        aprobados = len(df_p[df_p['estado']=="Aprobado"]) if not df_p.empty else 0
        pendientes = len(df_p[df_p['estado']=="Pendiente"]) if not df_p.empty else 0
        rechazados = len(df_p[df_p['estado']=="Rechazado"]) if not df_p.empty else 0
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("EN EL ALBERGUE", en_albergue)
        with col2: st.metric("PENDIENTES", pendientes)
        with col3: st.metric("APROBADOS", aprobados)
        with col4: st.metric("RECHAZADOS", rechazados)
        st.markdown("---")
        col_izq, col_der = st.columns([2.6,1])
        with col_izq:
            st.markdown("### Permisos Solicitados")
            if not df_p.empty:
                df_tabla = pd.read_sql("""SELECT p.id as ID, j.nombres as Nombre, j.apellidos as Apellido, p.fecha_sol as "Fec.Sol", p.fecha_salida as "Salida", p.destino as Destino, p.estado as Estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.id DESC""", conn)
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
                c_a, c_b, c_c = st.columns([1,1,1])
                with c_a: id_permiso = st.selectbox("ID", df_p['id'].tolist(), key="id_panel")
                with c_b: nuevo_estado = st.selectbox("Estado", ["Pendiente","Aprobado","Rechazado"], key="estado_panel")
                with c_c:
                    st.write("")
                    if st.button("Actualizar", type="primary", use_container_width=True):
                        c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo_estado, id_permiso))
                        conn.commit()
                        st.rerun()
            else:
                st.info("Aún no hay solicitudes")
        with col_der:
            st.markdown("### QR Salida")
            url_salida = LINK_NUBE
            qr_salida = generar_qr(url_salida)
            st.image(qr_salida, width=220)
            st.code(url_salida, language=None)
            st.download_button("Descargar QR", qr_salida, "qr_salida.png", use_container_width=True)

    elif pagina == "Lista de Usuarios":
        st.title("👥 Lista de Usuarios")
        st.dataframe(pd.read_sql("SELECT documento, nombre, rol FROM usuarios", conn), use_container_width=True)
    elif pagina == "Crear Usuarios" and st.session_state.rol == "Director":
        st.title("➕ Crear Nuevo Usuario")
        with st.form("form_usuario"):
            doc = st.text_input("Documento/Cédula")
            nombre = st.text_input("Nombre Completo")
            password = st.text_input("Contraseña", type="password")
            rol = st.selectbox("Rol", ROLES)
            if st.form_submit_button("Guardar Usuario"):
                try:
                    c.execute("INSERT INTO usuarios VALUES (?,?,?,?)", (doc, nombre, password, rol))
                    conn.commit()
                    st.success(f"Usuario {nombre} creado!")
                except:
                    st.error("Ese documento ya existe")
    elif pagina == "Jovenes":
        st.title("Gestión de Jóvenes")
        buscar = st.text_input("🔍 Buscar por documento")
        df = pd.read_sql("SELECT * FROM jovenes", conn)
        if buscar:
            df = df[df['documento'].astype(str).str.contains(buscar, na=False)]
        st.dataframe(df, use_container_width=True)
        st.markdown("---")
        st.subheader("➕ Agregar Nuevo Joven")
        with st.form("form_nuevo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                documento=st.text_input("Documento")
                nombres=st.text_input("Nombres")
                apellidos=st.text_input("Apellidos")
                fecha_nac=st.date_input("Fecha de nacimiento", format="DD/MM/YYYY")
                ciudad=st.text_input("Ciudad")
                barrio=st.text_input("Barrio")
                direccion=st.text_input("Dirección")
                telefono=st.text_input("Teléfono")
                responsable=st.text_input("Responsable")
                parentesco=st.text_input("Parentesco")
                tel_responsable=st.text_input("Tel Responsable")
            with c2:
                fecha_ingreso=st.date_input("Fecha ingreso")
                estado=st.selectbox("Estado",["Actual","Desvinculado"])
                habitacion=st.text_input("Habitación")
                cama=st.text_input("Cama")
                colegio=st.text_input("Colegio")
                grado=st.text_input("Grado")
                deporte=st.text_input("Deporte")
                posicion=st.text_input("Posición")
                categoria=st.text_input("Categoría")
                turno=st.selectbox("Turno",["Mañana","Tarde","Noche"])
                foto_url=st.text_input("URL Foto")
            motivo_ingreso=st.text_area("Motivo ingreso")
            if st.form_submit_button("Guardar Nuevo"):
                c.execute("INSERT INTO jovenes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (documento,nombres,apellidos,str(fecha_nac),ciudad,barrio,direccion,telefono,responsable,parentesco,tel_responsable,str(fecha_ingreso),estado,habitacion,cama,colegio,grado,deporte,posicion,categoria,turno,foto_url,motivo_ingreso))
                conn.commit()
                st.success("Joven guardado")
                st.rerun()
        st.markdown("---")
        st.subheader("✏️ Editar / Eliminar Ficha")
        doc_editar = st.text_input("Ingresá el documento del joven a editar")
        if doc_editar:
            joven_edit = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc_editar,))
            if joven_edit.empty:
                st.error("No existe un joven con ese documento")
            else:
                jd = joven_edit.iloc[0]
                st.info(f"Editando ficha de: {jd['nombres']} {jd['apellidos']}")
                with st.form("form_editar"):
                    c1, c2 = st.columns(2)
                    with c1:
                        e_documento=st.text_input("Documento", value=jd['documento'])
                        e_nombres=st.text_input("Nombres", value=jd['nombres'])
                        e_apellidos=st.text_input("Apellidos", value=jd['apellidos'])
                        e_ciudad=st.text_input("Ciudad", value=jd['ciudad'] or "")
                        e_barrio=st.text_input("Barrio", value=jd['barrio'] or "")
                        e_direccion=st.text_input("Dirección", value=jd['direccion'] or "")
                        e_telefono=st.text_input("Teléfono", value=jd['telefono'] or "")
                        e_responsable=st.text_input("Responsable", value=jd['responsable'] or "")
                        e_parentesco=st.text_input("Parentesco", value=jd['parentesco'] or "")
                        e_tel_responsable=st.text_input("Tel Responsable", value=jd['tel_responsable'] or "")
                    with c2:
                        e_estado=st.selectbox("Estado", ["Actual","Desvinculado"], index=0 if jd['estado']=="Actual" else 1)
                        e_habitacion=st.text_input("Habitación", value=jd['habitacion'] or "")
                        e_cama=st.text_input("Cama", value=jd['cama'] or "")
                        e_colegio=st.text_input("Colegio", value=jd['colegio'] or "")
                        e_grado=st.text_input("Grado", value=jd['grado'] or "")
                        e_deporte=st.text_input("Deporte", value=jd['deporte'] or "")
                        e_posicion=st.text_input("Posición", value=jd['posicion'] or "")
                        e_categoria=st.text_input("Categoría", value=jd['categoria'] or "")
                        e_turno=st.selectbox("Turno", ["Mañana","Tarde","Noche"], index=["Mañana","Tarde","Noche"].index(jd['turno']) if jd['turno'] in ["Mañana","Tarde","Noche"] else 0)
                        e_foto_url=st.text_input("URL Foto", value=jd['foto_url'] or "")
                    e_motivo=st.text_area("Motivo ingreso", value=jd['motivo_ingreso'] or "")
                    col_guardar, col_eliminar = st.columns(2)
                    with col_guardar:
                        guardar = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
                    with col_eliminar:
                        eliminar = st.form_submit_button("🗑️ Eliminar Joven", use_container_width=True)
                    if guardar:
                        c.execute("""UPDATE jovenes SET documento=?, nombres=?, apellidos=?, ciudad=?, barrio=?, direccion=?, telefono=?, responsable=?, parentesco=?, tel_responsable=?, estado=?, habitacion=?, cama=?, colegio=?, grado=?, deporte=?, posicion=?, categoria=?, turno=?, foto_url=?, motivo_ingreso=? WHERE id=?""",
                            (e_documento, e_nombres, e_apellidos, e_ciudad, e_barrio, e_direccion, e_telefono, e_responsable, e_parentesco, e_tel_responsable, e_estado, e_habitacion, e_cama, e_colegio, e_grado, e_deporte, e_posicion, e_categoria, e_turno, e_foto_url, e_motivo, jd['id']))
                        conn.commit()
                        st.success("✅ Ficha actualizada")
                        st.rerun()
                    if eliminar:
                        c.execute("DELETE FROM jovenes WHERE id=?", (jd['id'],))
                        conn.commit()
                        st.warning("Joven eliminado")
                        st.rerun()
    elif pagina == "Permisos":
        st.title("Permisos")
        c1,c2,c3,c4 = st.columns(4)
        doc_f=c1.text_input("Documento")
        est_f=c2.selectbox("Estado",["Todos","Pendiente","Aprobado","Rechazado"])
        fecha_f=c3.date_input("Fecha")
        dest_f=c4.text_input("Destino")
        query="SELECT p.id, j.documento, j.nombres, j.apellidos, p.fecha_sol, p.fecha_salida, p.destino, p.estado, p.hora_regreso_real FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE 1=1"
        if doc_f:
            query+=f" AND j.documento LIKE '%{doc_f}%'"
        if est_f!="Todos":
            query+=f" AND p.estado='{est_f}'"
        st.dataframe(pd.read_sql(query, conn), use_container_width=True)
    elif pagina == "Mensajería":
        st.title("Mensajería")
        st.subheader("Plantilla WhatsApp")
        st.caption("Usa {nombre}, {destino}, {fecha_salida}, {hora_salida}, {motivo} como variables")
        msg = pd.read_sql("SELECT * FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn)
        msg_act = msg.iloc[0]['mensaje'] if not msg.empty else ""
        with st.form("plantilla"):
            nuevo = st.text_area("Mensaje predeterminado", msg_act, height=150)
            if st.form_submit_button("Guardar"):
                c.execute("UPDATE mensajes SET mensaje=? WHERE tipo='Predeterminado'", (nuevo,))
                conn.commit()
                st.success("Guardado")
        st.subheader("Historial")
        st.dataframe(pd.read_sql("SELECT * FROM mensajes ORDER BY id DESC", conn), use_container_width=True)
    elif pagina == "Contactos del Albergue" and st.session_state.rol == "Director":
        st.title("Contactos")
        with st.form("new_contact"):
            c1,c2 = st.columns(2)
            nombres=c1.text_input("Nombres")
            apellidos=c2.text_input("Apellidos")
            cargo=c1.selectbox("Cargo",ROLES)
            telefono=c2.text_input("Teléfono")
            obs=st.text_area("Observación")
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO contactos (nombres,apellidos,cargo,telefono,observacion) VALUES (?,?,?,?,?)",(nombres,apellidos,cargo,telefono,obs))
                conn.commit()
                st.success("Guardado")
        st.dataframe(pd.read_sql("SELECT * FROM contactos", conn), use_container_width=True)
    elif pagina == "WhatsApp Web":
        st.title("📱 WhatsApp Web Directo")
        col1, col2 = st.columns([1,2])
        with col1:
            telefono = st.text_input("Número (ej: 0981123456)")
        with col2:
            mensaje = st.text_area("Mensaje", height=150)
        if st.button("Generar Link de WhatsApp", type="primary", use_container_width=True):
            if not telefono:
                st.warning("Ingresá un número")
            else:
                num_limpio = limpiar_numero(telefono)
                url = f"https://wa.me/{num_limpio}?text={urllib.parse.quote(mensaje)}"
                st.link_button(f"📲 Abrir WhatsApp", url, use_container_width=True)
    elif pagina == "Informe Tutoría":
        st.title("Informe Tutoría")
        tab_a, tab_b = st.tabs(["Informe General del Albergue", "Informe por Joven"])
        with tab_a:
            with st.form("inf_gen"):
                fecha=st.date_input("Fecha")
                desarrollo=st.text_area("Desarrollo")
                rutinas=st.text_area("Rutinas")
                infra=st.text_area("Infraestructura")
                obs=st.text_area("Observaciones")
                nec=st.text_area("Necesidades")
                prio=st.selectbox("Prioridad",["Normal","Urgente"])
                if st.form_submit_button("Guardar Informe General", type="primary", use_container_width=True):
                    c.execute("INSERT INTO tutoria VALUES (NULL,?,?,?,?,?,?,?)",(str(fecha),desarrollo,rutinas,infra,obs,nec,prio))
                    conn.commit()
                    st.success("✅ Informe general guardado")
            st.dataframe(pd.read_sql("SELECT * FROM tutoria ORDER BY fecha DESC", conn), use_container_width=True)
        with tab_b:
            st.subheader("Cargar Informe Individual")
            with st.form("inf_joven"):
                doc_j=st.text_input("Documento del Joven")
                informe=st.text_area("Informe del Joven", height=200)
                if st.form_submit_button("Guardar Informe Joven", type="primary", use_container_width=True):
                    jid = pd.read_sql("SELECT id, nombres, apellidos FROM jovenes WHERE documento=?", conn, params=(doc_j,))
                    if jid.empty:
                        st.error("No existe un joven con ese documento")
                    else:
                        c.execute("INSERT INTO tutoria_joven VALUES (NULL,?,?,?)",(jid.iloc[0]['id'], str(date.today()), informe))
                        conn.commit()
                        st.success(f"✅ Informe guardado para {jid.iloc[0]['nombres']} {jid.iloc[0]['apellidos']}")
            st.dataframe(pd.read_sql("SELECT tj.fecha, j.documento, j.nombres, j.apellidos, tj.informe FROM tutoria_joven tj JOIN jovenes j ON tj.joven_id=j.id ORDER BY tj.fecha DESC", conn), use_container_width=True)
    elif pagina == "Reportes":
        st.title("Reportes")
        df_rep = pd.read_sql("SELECT j.nombres, j.apellidos, j.categoria, p.fecha_sol, p.fecha_salida, p.fecha_regreso, p.motivo, p.destino, p.hora_regreso_real, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id", conn)
        st.dataframe(df_rep, use_container_width=True)
        st.download_button("📄 Imprimir", df_rep.to_csv(index=False).encode('utf-8'), "reporte.csv")
    elif pagina == "QR de Acceso":
        st.title("QR de Acceso")
        qr = generar_qr(f"ALBERGUE:{NOMBRE_SEDE}")
        st.image(qr, width=300)
        st.download_button("Descargar QR", qr, "qr_acceso.png")

if st.session_state.usuario is None:
    login()
    st.stop()
else:
    app()
