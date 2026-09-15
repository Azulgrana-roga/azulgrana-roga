import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time
import qrcode
from io import BytesIO
import urllib.parse
import base64

query_params = st.query_params
pagina_url = query_params.get("pagina", "Inicio")

st.set_page_config(page_title="Azulgrana Róga", layout="wide", page_icon="🏠")

# 1. DISEÑO AZULGRANA CICLÓN
st.markdown("""
    <style>
.stApp {background-color: #001F3F;}
    [data-testid="stSidebar"] {background-color: #00004B;}
    [data-testid="stSidebar"] * {color: white;}
.stButton>button {
        background-color: #FF0000;
        color: white;
        border-radius: 10px;
        border: 2px solid #00529F;
        font-weight: bold;
    }
.stButton>button:hover {
        background-color: #00529F;
        color: white;
        border: 2px solid #FF0000;
    }
    h1, h2, h3 {color: #00529F; font-weight: bold;}
    [data-testid="stMetric"] {
        background-color: white;
        border: 2px solid #00529F;
        border-radius: 10px;
        padding: 10px;
    }
    [data-testid="stDataFrame"] {background-color: white!important;}
    [data-testid="stDataFrame"] * {color: black!important;}
    @keyframes parpadeo { 0% {background-color: #8B0000;} 50% {background-color: transparent;} 100% {background-color: #8B0000;} }
 .atrasado { animation: parpadeo 1s infinite; color: white!important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

NOMBRE_ALBERGUE = "Fundación Club Cerro Porteño"
NOMBRE_SEDE = "Azulgrana Róga"

ROLES = ["Director", "Encargado/a del Albergue", "Trabajador/a Social", "Médico/a", "Psicólogo/a", "Tutor"]

# DB
conn = sqlite3.connect('albergue.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (documento TEXT PRIMARY KEY, nombre TEXT, password TEXT, rol TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS jovenes (id INTEGER PRIMARY KEY AUTOINCREMENT, documento TEXT, nombres TEXT, apellidos TEXT, fecha_nac DATE, ciudad TEXT, barrio TEXT, direccion TEXT, telefono TEXT, responsable TEXT, parentesco TEXT, tel_responsable TEXT, fecha_ingreso DATE, estado TEXT, habitacion TEXT, cama TEXT, colegio TEXT, grado TEXT, deporte TEXT, posicion TEXT, categoria TEXT, turno TEXT, foto_url TEXT, motivo_ingreso TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS permisos (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha_sol DATE, fecha_salida DATE, hora_salida TEXT, fecha_regreso DATE, hora_regreso TEXT, tipo_salida TEXT, destino TEXT, persona_salida TEXT, parentesco TEXT, tel_contacto TEXT, motivo TEXT, estado TEXT DEFAULT 'Pendiente', hora_regreso_real TEXT, qr_id TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, adolescente TEXT, contacto TEXT, tipo TEXT, mensaje TEXT, estado TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS contactos (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, nombres TEXT, apellidos TEXT, cargo TEXT, rol TEXT, telefono TEXT, observacion TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, desarrollo TEXT, rutinas TEXT, infraestructura TEXT, observaciones TEXT, necesidad TEXT, prioridad TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria_joven (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha DATE, informe TEXT)''')
c.execute("INSERT OR IGNORE INTO mensajes (id, tipo, mensaje) VALUES (1, 'Predeterminado', 'Hola. Su hijo/a ha solicitado permiso de salida del albergue Azulgrana Róga.')")

# CREAR ADMIN POR DEFECTO SI NO EXISTE
c.execute("INSERT OR IGNORE INTO usuarios (documento, nombre, password, rol) VALUES ('admin', 'Administrador', 'cerro2026', 'Director')")
conn.commit()

# FUNCIONES
def calcular_edad(fn): return date.today().year - fn.year - ((date.today().month, date.today().day) < (fn.month, fn.day)) if fn else ""
def generar_qr(data): qr = qrcode.make(data); buf = BytesIO(); qr.save(buf, format="PNG"); return buf.getvalue()

# SESION
if 'usuario' not in st.session_state: st.session_state.usuario = None
if 'rol' not in st.session_state: st.session_state.rol = None

# LOGIN
def login():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,5,1])
    with col2:
        st.image("Logo.png", width=100)
        st.markdown(f"<h2 style='color:white;'>{NOMBRE_ALBERGUE}</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#00529F;'>{NOMBRE_SEDE}</h3>", unsafe_allow_html=True)
        documento = st.text_input("Documento de usuario").strip()
        password = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar", type="primary", use_container_width=True):
            # DEBUG: para ver que hay en la base en la nube
            # st.write("DEBUG USUARIOS:", pd.read_sql("SELECT * FROM usuarios", conn))

            user = pd.read_sql("SELECT * FROM usuarios WHERE CAST(documento AS TEXT) =? AND CAST(password AS TEXT) =?", conn, params=(documento, password))
            if not user.empty:
                st.session_state.usuario = user.iloc[0]['nombre']
                st.session_state.rol = user.iloc[0]['rol']
                st.session_state.documento_user = user.iloc[0]['documento']
                st.rerun()
            else:
                st.error("Documento o contraseña incorrecta")

# APP
def app():
    # MENU CON PERMISOS
    st.sidebar.image("Logo.png", width=120)
    st.sidebar.title(f"🏠 {NOMBRE_SEDE}")
    st.sidebar.caption(NOMBRE_ALBERGUE)
    st.sidebar.markdown(f"**{st.session_state.rol.upper()}** | {st.session_state.usuario}")

    # 1. TODOS VEN ESTAS
    menu_base = ["Panel de Control", "Lista de Usuarios", "Jovenes", "Permisos", "Mensajería", "Informe Tutoría", "Reportes", "QR de Acceso"]

    # 2. SOLO ADMIN VE ESTAS
    if st.session_state.rol == "Director":
        menu_admin = ["Crear Usuarios", "Portal Joven", "Contactos del Albergue"]
        MENU = menu_base + menu_admin
    else:
        MENU = menu_base

    if 'ir_a' in st.session_state:
        pagina = st.session_state.ir_a
        del st.session_state.ir_a
    else:
        pagina = st.sidebar.radio("Menú", MENU, key="menu_principal")

    if st.sidebar.button("Cerrar Sesión", use_container_width=True, type="primary"):
        st.session_state.usuario = None
        st.session_state.rol = None
        st.rerun()

    # PESTAÑA NUEVA: LISTA DE USUARIOS - TODOS VEN
    if pagina == "Lista de Usuarios":
        st.title("👥 Lista de Usuarios del Sistema")
        df_usuarios = pd.read_sql("SELECT documento, nombre, rol FROM usuarios", conn)
        st.dataframe(df_usuarios, use_container_width=True)
        st.info("Todos pueden ver esta lista. Solo Director puede crear/editar.")

    # PESTAÑA NUEVA: CREAR USUARIOS - SOLO ADMIN
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
                except: st.error("Ese documento ya existe")

    elif pagina == "Panel de Control":
        st.title("Panel de Control")
        if st.button("MODO PROYECCIÓN - Presiona ESC para salir", type="primary"):
            st.session_state.modo_pantalla = True

        df_j = pd.read_sql("SELECT * FROM jovenes", conn)
        df_p = pd.read_sql("SELECT * FROM permisos", conn)
        en_albergue = len(df_j[df_j['estado']=="Actual"])
        aprobados = len(df_p[df_p['estado']=="Aprobado"])
        pendientes = len(df_p[df_p['estado']=="Pendiente"])
        try:
            df_p['hora_regreso'] = pd.to_datetime(df_p['hora_regreso'], errors='coerce')
            df_p['hora_regreso_real'] = pd.to_datetime(df_p['hora_regreso_real'], errors='coerce')
            atrasados = len(df_p[(df_p['hora_regreso_real'].notna()) & (df_p['hora_regreso_real'] > df_p['hora_regreso'])])
        except: atrasados = 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("EN EL ALBERGUE", en_albergue)
        col2.metric("PERMISOS APROB.", aprobados)
        col3.metric("PENDIENTES", pendientes)
        col4.metric("ATRASADOS", atrasados)

        st.markdown("### Permisos Solicitados")
        if not df_p.empty:
            df_tabla = pd.read_sql("SELECT p.id, j.nombres || ' || j.apellidos as Joven, p.destino, p.hora_salida, p.hora_regreso, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.fecha_sol DESC", conn)
            def color_estado(val):
                if val=="Pendiente": return 'background-color: #FFFF00; color: black'
                if val=="Aprobado": return 'background-color: #00FF00; color: black'
                if val=="Rechazado": return 'background-color: rgba(255,0,0,0.3); color: black'
                return ''
            st.dataframe(df_tabla.style.map(color_estado, subset=['estado']), use_container_width=True)

            st.subheader("Aprobar/Rechazar Solicitud")
            id_permiso = st.selectbox("ID Permiso", df_p['id'].tolist())
            nuevo_estado = st.selectbox("Estado", ["Pendiente","Aprobado","Rechazado"])
            if st.button("Actualizar Estado"):
                c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo_estado, id_permiso))
                conn.commit()
                if nuevo_estado=="Aprobado":
                    perm = pd.read_sql("SELECT * FROM permisos WHERE id=?", conn, params=(id_permiso,)).iloc[0]
                    qr_data = f"http://192.168.0.116:8501?pagina=Portal%20Joven&permiso={perm['id']}"
                    st.success(f"QR de salida generado"); st.image(generar_qr(qr_data), width=140)
                st.rerun()

        # QR NUEVO PARA PORTAL JOVEN
        st.markdown("---")
        st.subheader("QR de Solicitud de Salida")
        url_salida = f"http://192.168.0.116:8501?pagina=Portal%20Joven"
        qr_salida = generar_qr(url_salida)

        col_qr, col_info = st.columns([1,3])
        with col_qr:
            st.image(qr_salida, width=200)
            st.download_button("Descargar QR", qr_salida, "qr_salida.png", use_container_width=True)
        with col_info:
            st.info("1. El joven escanea \n2. Pone su documento \n3. Completa y se avisa al tutor")

    elif pagina == "Portal Joven" and st.session_state.rol == "Director":
        st.set_page_config(page_title="Portal Joven", layout="centered")
        st.markdown("""<style>[data-testid="stSidebar"] {display: none;} header {display: none;}</style>""", unsafe_allow_html=True)

        col1, col2 = st.columns([5,1])
        with col1:
            st.title("Portal del Joven - Azulgrana Róga")
        with col2:
            if st.button("🏠 Volver al Panel de Control", use_container_width=True, type="primary"):
                st.query_params.clear()
                st.session_state.ir_a = "Panel de Control"
                st.rerun()

        tab1, tab2 = st.tabs(["Solicitar Salida", "Consultar Estado"])

        with tab1:
            query_params = st.query_params
            doc_url = query_params.get("doc", "")
            if not doc_url:
                doc_url = st.text_input("Ingrese su documento")

            joven = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc_url,)) if doc_url else pd.DataFrame()

            if not joven.empty:
                jd = joven.iloc[0]
                if jd['estado']!="Actual":
                    st.error(f"⚠️ {jd['nombres']} no se encuentra ACTIVO")
                else:
                    st.success(f"Bienvenido {jd['nombres']} {jd['apellidos']}")
                    with st.form("form_salida"):
                        c1,c2 = st.columns(2)
                        with c1:
                            st.text_input("Documento", jd['documento'], disabled=True)
                            st.text_input("Nombre", jd['nombres'], disabled=True)
                            st.text_input("Apellidos", jd['apellidos'], disabled=True)
                            fecha_sol = st.date_input("Fecha de solicitud", date.today())
                            fecha_salida = st.date_input("Fecha de salida")
                            hora_salida = st.time_input("Hora de salida")
                        with c2:
                            fecha_regreso = st.date_input("Fecha de regreso")
                            hora_regreso = st.time_input("Hora de regreso")
                            tipo_salida = st.selectbox("Tipo de salida", ["Familiar","Médico","Deportivo","Personal","Otro"])
                            destino = st.text_input("Destino *")
                            persona = st.text_input("Persona con quien saldrá")
                            parentesco = st.text_input("Parentesco")
                            tel_contacto = st.text_input("Teléfono de contacto")
                            motivo = st.text_area("Motivo")

                        if st.form_submit_button("Enviar solicitud", type="primary", use_container_width=True):
                            if not destino: st.warning("El campo Destino es obligatorio")
                            else:
                                c.execute("INSERT INTO permisos (joven_id,fecha_sol,fecha_salida,hora_salida,fecha_regreso,hora_regreso,tipo_salida,destino,persona_salida,parentesco,tel_contacto,motivo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                (jd['id'],str(fecha_sol),str(fecha_salida),str(hora_salida),str(fecha_regreso),str(hora_regreso),tipo_salida,destino,persona,parentesco,tel_contacto,motivo))
                                conn.commit()
                                st.success("✅ Solicitud enviada!")

        with tab2:
            doc_cons = st.text_input("Documento para consultar estado")
            if doc_cons:
                df_est = pd.read_sql("SELECT p.id, p.fecha_sol, p.destino, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE j.documento=? ORDER BY p.fecha_sol DESC", conn, params=(doc_cons,))
                st.dataframe(df_est, use_container_width=True)

    elif pagina == "Jovenes":
        st.title("Gestión de Jóvenes")
        buscar = st.text_input("🔍 Buscar por documento")
        if st.button("+ Agregar Joven"):
            with st.form("form_nuevo"):
                c1,c2 = st.columns(2)
                with c1:
                    documento=st.text_input("Documento"); nombres=st.text_input("Nombres"); apellidos=st.text_input("Apellidos")
                    fecha_nac=st.date_input("Fecha de nacimiento", format="DD/MM/YYYY"); ciudad=st.text_input("Ciudad"); barrio=st.text_input("Barrio")
                    direccion=st.text_input("Dirección"); telefono=st.text_input("Teléfono"); responsable=st.text_input("Responsable")
                    parentesco=st.text_input("Parentesco"); tel_responsable=st.text_input("Tel Responsable")
                with c2:
                    fecha_ingreso=st.date_input("Fecha ingreso"); estado=st.selectbox("Estado",["Actual","Desvinculado"])
                    habitacion=st.text_input("Habitación"); cama=st.text_input("Cama"); colegio=st.text_input("Colegio"); grado=st.text_input("Grado")
                    deporte=st.text_input("Deporte"); posicion=st.text_input("Posición"); categoria=st.text_input("Categoría")
                    turno=st.selectbox("Turno",["Mañana","Tarde","Noche"]); foto_url=st.text_input("URL Foto")
                motivo_ingreso=st.text_area("Motivo ingreso")
                if st.form_submit_button("Guardar"):
                    c.execute("INSERT INTO jovenes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (documento,nombres,apellidos,fecha_nac,ciudad,barrio,direccion,telefono,responsable,parentesco,tel_responsable,fecha_ingreso,estado,habitacion,cama,colegio,grado,deporte,posicion,categoria,turno,foto_url,motivo_ingreso))
                    conn.commit(); st.success("Guardado"); st.rerun()
        df = pd.read_sql("SELECT * FROM jovenes", conn)
        if buscar: df = df[df['documento'].astype(str).str.contains(buscar)]
        df['estado_auto'] = df['estado'].apply(lambda x: "En el Albergue" if x=="Actual" else "Fuera del Albergue")
        st.dataframe(df, use_container_width=True)
        st.download_button("🖨️ Imprimir lista", df.to_csv(index=False).encode('utf-8'), "lista_jovenes.csv")

    elif pagina == "Permisos":
        st.title("Permisos")
        c1,c2,c3,c4 = st.columns(4)
        doc_f=c1.text_input("Documento"); est_f=c2.selectbox("Estado",["Todos","Pendiente","Aprobado","Rechazado"])
        fecha_f=c3.date_input("Fecha"); dest_f=c4.text_input("Destino")
        query="SELECT p.id, j.documento, j.nombres, j.apellidos, p.fecha_sol, p.fecha_salida, p.destino, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE 1=1"
        if doc_f: query+=f" AND j.documento LIKE '%{doc_f}%'"
        if est_f!="Todos": query+=f" AND p.estado='{est_f}'"
        st.dataframe(pd.read_sql(query, conn), use_container_width=True)

    elif pagina == "Mensajería":
        st.title("Mensajería")
        st.subheader("Plantilla WhatsApp")
        msg = pd.read_sql("SELECT * FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn)
        msg_act = msg.iloc[0]['mensaje'] if not msg.empty else ""
        with st.form("plantilla"):
            nuevo = st.text_area("Mensaje predeterminado", msg_act)
            if st.form_submit_button("Guardar"): c.execute("UPDATE mensajes SET mensaje=? WHERE tipo='Predeterminado'",(nuevo,)); conn.commit(); st.success("Guardado")
        st.subheader("Historial")
        st.dataframe(pd.read_sql("SELECT * FROM mensajes", conn), use_container_width=True)

    elif pagina == "Contactos del Albergue" and st.session_state.rol == "Director":
        st.title("Contactos")
        with st.form("new_contact"):
            c1,c2 = st.columns(2)
            nombres=c1.text_input("Nombres"); apellidos=c2.text_input("Apellidos")
            cargo=c1.selectbox("Cargo",ROLES); telefono=c2.text_input("Teléfono"); obs=st.text_area("Observación")
            if st.form_submit_button("Guardar"): c.execute("INSERT INTO contactos (nombres,apellidos,cargo,telefono,observacion) VALUES (?,?,?,?,?)",(nombres,apellidos,cargo,telefono,obs)); conn.commit(); st.success("Guardado")
        st.dataframe(pd.read_sql("SELECT * FROM contactos", conn), use_container_width=True)

    elif pagina == "Informe Tutoría":
        st.title("Informe Tutoría")
        with st.form("inf_gen"):
            fecha=st.date_input("Fecha"); desarrollo=st.text_area("Desarrollo"); rutinas=st.text_area("Rutinas")
            infra=st.text_area("Infraestructura"); obs=st.text_area("Observaciones"); nec=st.text_area("Necesidades")
            prio=st.selectbox("Prioridad",["Normal","Urgente"])
            if st.form_submit_button("Guardar"): c.execute("INSERT INTO tutoria VALUES (NULL,?,?,?,?,?,?,?)",(fecha,desarrollo,rutinas,infra,obs,nec,prio)); conn.commit(); st.success("Guardado")
        st.markdown("---")
        with st.form("inf_joven"):
            doc_j=st.text_input("Documento Joven"); informe=st.text_area("Informe")
            if st.form_submit_button("Guardar Informe Joven"):
                jid = pd.read_sql("SELECT id FROM jovenes WHERE documento=?", conn, params=(doc_j,))
                if not jid.empty: c.execute("INSERT INTO tutoria_joven VALUES (NULL,?,?,?)",(jid.iloc[0]['id'],date.today(),informe)); conn.commit(); st.success("Guardado")

    elif pagina == "Reportes":
        st.title("Reportes")
        df_rep = pd.read_sql("SELECT j.nombres, j.apellidos, j.categoria, p.fecha_sol, p.fecha_salida, p.fecha_regreso, p.motivo, p.destino FROM permisos p JOIN jovenes j ON p.joven_id=j.id", conn)
        st.dataframe(df_rep, use_container_width=True)
        st.download_button("📄 Imprimir", df_rep.to_csv(index=False).encode('utf-8'), "reporte.csv")

    elif pagina == "QR de Acceso":
        st.title("QR de Acceso")
        qr = generar_qr(f"ALBERGUE:{NOMBRE_SEDE}")
        st.image(qr, width=300)
        st.download_button("Descargar QR", qr, "qr_acceso.png")

if st.session_state.usuario is None: login(); st.stop()
else: app()
