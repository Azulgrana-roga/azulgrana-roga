import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import qrcode
from io import BytesIO
import urllib.parse
import socket

LINK_NUBE = "https://azulgrana-roga.streamlit.app/?pagina=portal"
LINK_BASE = "https://azulgrana-roga.streamlit.app"
TELEFONO_ALBERGUE = "595981123456" # NUMERO DE BACILIO

st.set_page_config(page_title="Azulgrana Róga", layout="wide", page_icon="🏠")
st.markdown("""<style>
.stApp {background-color: #001F3F;} [data-testid="stSidebar"] {background-color: #00004B;} [data-testid="stSidebar"] * {color: white;}
.stButton>button {background-color: #FF0000;color: white;border-radius: 10px;border: 2px solid #00529F;font-weight: bold;}
h1, h2, h3 {color: #00529F; font-weight: bold;} [data-testid="stDataFrame"] {background-color: white!important;} [data-testid="stDataFrame"] * {color: black!important;}
#MainMenu, footer {display:none!important;}
</style>""", unsafe_allow_html=True)

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
c.execute("INSERT OR IGNORE INTO mensajes (id, tipo, mensaje) VALUES (1, 'Predeterminado', 'Hola {responsable}. Su hijo/a {nombre} solicita salida del albergue Azulgrana Róga. Destino: {destino} - Fecha: {fecha_salida} a las {hora_salida}. Motivo: {motivo}')")
c.execute("INSERT OR IGNORE INTO usuarios (documento, nombre, password, rol) VALUES ('admin', 'Administrador', 'cerro2026', 'Director')")
conn.commit()

def generar_qr(data):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def limpiar_numero(num):
    num = ''.join(filter(str.isdigit, str(num)))
    if num.startswith('0'): num = '595' + num[1:]
    return num

for k in ['usuario','rol','confirmar_eliminar_id']:
    if k not in st.session_state: st.session_state[k]=None

# === 1. RESPUESTA DEL RESPONSABLE POR LINK ===
accion = str(st.query_params.get("accion", "")).lower()
id_accion = st.query_params.get("id", "")
if accion in ["aprobar", "rechazar"] and id_accion:
    nuevo = "Aprobado" if accion=="aprobar" else "Rechazado"
    c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo, int(id_accion)))
    conn.commit()
    info = pd.read_sql("SELECT j.nombres, j.apellidos, j.responsable, p.destino FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE p.id=?", conn, params=(int(id_accion),))
    if not info.empty:
        nom = f"{info.iloc[0]['nombres']} {info.iloc[0]['apellidos']}"
        texto = f"RESPUESTA {nuevo.upper()}: El responsable {info.iloc[0]['responsable']} ha {nuevo} la salida de {nom} a {info.iloc[0]['destino']} ID:{id_accion}"
        c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), nom, "Albergue", f"Respuesta {nuevo}", texto, nuevo))
        conn.commit()
        url_aviso = f"https://wa.me/{TELEFONO_ALBERGUE}?text={urllib.parse.quote(texto)}"
        st.markdown(f"<h1 style='color:white;text-align:center;margin-top:80px;'>✅ Solicitud {id_accion} {nuevo}</h1>", unsafe_allow_html=True)
        st.link_button(f"📲 Avisar al Albergue que fue {nuevo}", url_aviso, type="primary", use_container_width=True)
        st.balloons()
        st.stop()

# === 2. PORTAL JOVEN ===
if str(st.query_params.get("pagina","")).lower() in ["portal","portal joven"]:
    st.markdown("<h1 style='color:white;'>Portal del Joven - Azulgrana Róga</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Solicitar Salida", "Consultar Estado"])
    with tab1:
        doc = st.text_input("Ingresá tu documento")
        if doc:
            j = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc,))
            if j.empty: st.error("Documento no encontrado")
            elif j.iloc[0]['estado']!="Actual": st.error("No estás ACTIVO")
            else:
                jd = j.iloc[0]
                st.success(f"Bienvenido {jd['nombres']} {jd['apellidos']}")
                plant = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn).iloc[0]['mensaje']
                with st.form("sol"):
                    c1,c2=st.columns(2)
                    with c1:
                        fs=st.date_input("Fecha salida")
                        hs=st.time_input("Hora salida")
                        fr=st.date_input("Fecha regreso")
                        hr=st.time_input("Hora regreso")
                    with c2:
                        tipo=st.selectbox("Tipo",["Familiar","Médico","Deportivo","Personal","Otro"])
                        dest=st.text_input("Destino *")
                        pers=st.text_input("Persona con quien sale")
                        mot=st.text_area("Motivo")
                    if st.form_submit_button("Enviar solicitud", type="primary", use_container_width=True):
                        if not dest: st.warning("Destino obligatorio")
                        else:
                            c.execute("INSERT INTO permisos (joven_id,fecha_sol,fecha_salida,hora_salida,fecha_regreso,hora_regreso,tipo_salida,destino,persona_salida,motivo,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (jd['id'], str(date.today()), str(fs), str(hs), str(fr), str(hr), tipo, dest, pers, mot, "Pendiente"))
                            conn.commit()
                            id_nuevo = c.lastrowid
                            # PLANTILLA DE MENSAJERIA
                            txt_base = plant.replace("{nombre}", f"{jd['nombres']} {jd['apellidos']}").replace("{responsable}", str(jd['responsable'])).replace("{destino}", dest).replace("{fecha_salida}", str(fs)).replace("{hora_salida}", str(hs)).replace("{motivo}", mot)
                            link_ap = f"{LINK_BASE}/?accion=aprobar&id={id_nuevo}"
                            link_re = f"{LINK_BASE}/?accion=rechazar&id={id_nuevo}"
                            txt_final = f"{txt_base}\n\n*Responda tocando:*\n✅ APROBAR: {link_ap}\n❌ RECHAZAR: {link_re}\n\nRegreso: {fr} {hr}"
                            tel = limpiar_numero(jd['tel_responsable'])
                            url_wp = f"https://wa.me/{tel}?text={urllib.parse.quote(txt_final)}"
                            c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"{jd['nombres']} {jd['apellidos']}", jd['responsable'], "Salida", txt_final, "Pendiente"))
                            conn.commit()
                            st.success(f"✅ Solicitud #{id_nuevo} enviada como PENDIENTE")
                            st.link_button(f"📱 Enviar WhatsApp a {jd['responsable']}", url_wp, use_container_width=True)
    with tab2:
        doc2 = st.text_input("Documento para consultar")
        if doc2:
            df = pd.read_sql("SELECT p.id, p.fecha_sol, p.destino, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE j.documento=? ORDER BY p.id DESC", conn, params=(doc2,))
            st.dataframe(df, use_container_width=True)
    st.stop()

def login():
    st.markdown("<style>[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)
    _,c2,_ = st.columns([1,2,1])
    with c2:
        st.image("Logo.png", width=120)
        d=st.text_input("Documento")
        p=st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            u=pd.read_sql("SELECT * FROM usuarios WHERE documento=? AND password=?", conn, params=(d,p))
            if not u.empty:
                st.session_state.usuario=u.iloc[0]['nombre']
                st.session_state.rol=u.iloc[0]['rol']
                st.rerun()
            else: st.error("Datos incorrectos")

def app():
    st.sidebar.image("Logo.png", width=120)
    st.sidebar.title("🏠 Azulgrana Róga")
    MENU = ["Panel de Control", "Lista de Usuarios", "Jovenes", "Permisos", "Mensajería", "Informe Tutoría", "Reportes", "QR de Acceso", "WhatsApp Web", "Crear Usuarios", "Portal Joven", "Contactos del Albergue"] if st.session_state.rol=="Director" else ["Panel de Control", "Lista de Usuarios", "Jovenes", "Permisos", "Mensajería", "Informe Tutoría", "Reportes", "QR de Acceso", "WhatsApp Web"]
    pag = st.sidebar.radio("Menú", MENU)
    if st.sidebar.button("Cerrar Sesión", type="primary", use_container_width=True):
        st.session_state.usuario=None
        st.session_state.rol=None
        st.rerun()

    if pag=="Panel de Control":
        st.title("Panel de Control")
        df_j = pd.read_sql("SELECT * FROM jovenes", conn)
        df_p = pd.read_sql("SELECT * FROM permisos", conn)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("EN ALBERGUE", len(df_j[df_j['estado']=="Actual"]) if not df_j.empty else 0)
        c2.metric("PENDIENTES", len(df_p[df_p['estado']=="Pendiente"]) if not df_p.empty else 0)
        c3.metric("APROBADOS", len(df_p[df_p['estado']=="Aprobado"]) if not df_p.empty else 0)
        c4.metric("RECHAZADOS", len(df_p[df_p['estado']=="Rechazado"]) if not df_p.empty else 0)
        st.markdown("---")
        col_izq, col_der = st.columns([3,1])
        with col_izq:
            st.markdown("### Permisos Solicitados - Datos del solicitante y resultado")
            if not df_p.empty:
                df_tabla = pd.read_sql("""SELECT p.id as ID, j.documento as Doc, j.nombres || ' ' || j.apellidos as Adolescente, j.responsable as Responsable, j.tel_responsable as Tel_Resp, p.fecha_sol as Solicitud, p.fecha_salida as Salida, p.destino as Destino, p.motivo as Motivo, p.estado as Resultado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.id DESC""", conn)
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
                st.markdown("Actualizar manualmente si el responsable responde por texto:")
                ca,cb,cc=st.columns(3)
                with ca: id_sel=st.selectbox("ID Permiso", df_p['id'].tolist())
                with cb: est_sel=st.selectbox("Resultado", ["Pendiente","Aprobado","Rechazado"])
                with cc:
                    st.write("")
                    if st.button("Actualizar Resultado", type="primary", use_container_width=True):
                        c.execute("UPDATE permisos SET estado=? WHERE id=?", (est_sel, id_sel))
                        conn.commit()
                        st.rerun()
            else: st.info("Sin solicitudes")
        with col_der:
            st.markdown("### QR Portal")
            st.image(generar_qr(LINK_NUBE), width=200)
            st.code(LINK_NUBE)
            st.download_button("Descargar QR", generar_qr(LINK_NUBE), "qr_portal.png", use_container_width=True)

    elif pag=="Jovenes":
        st.title("Gestión de Jóvenes")
        st.dataframe(pd.read_sql("SELECT * FROM jovenes", conn), use_container_width=True)
        st.markdown("---")
        with st.form("form_nuevo", clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1:
                documento=st.text_input("Documento"); nombres=st.text_input("Nombres"); apellidos=st.text_input("Apellidos"); responsable=st.text_input("Responsable"); tel_responsable=st.text_input("Tel Responsable")
            with c2:
                fecha_ingreso=st.date_input("Fecha ingreso"); estado=st.selectbox("Estado",["Actual","Desvinculado"]); habitacion=st.text_input("Habitación"); categoria=st.text_input("Categoría")
            motivo=st.text_area("Motivo ingreso")
            if st.form_submit_button("Guardar Nuevo"):
                c.execute("INSERT INTO jovenes (documento,nombres,apellidos,responsable,tel_responsable,fecha_ingreso,estado,habitacion,categoria,motivo_ingreso) VALUES (?,?,?,?,?,?,?,?,?,?)", (documento,nombres,apellidos,responsable,tel_responsable,str(fecha_ingreso),estado,habitacion,categoria,motivo))
                conn.commit()
                st.success("Guardado")
                st.rerun()
        st.markdown("---")
        st.subheader("✏️ Editar")
        doc_editar = st.text_input("Documento a editar")
        if doc_editar:
            je = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc_editar,))
            if je.empty: st.error("No existe")
            else:
                jd=je.iloc[0]
                st.info(f"Editando {jd['nombres']} {jd['apellidos']}")
                with st.form("form_edit"):
                    en=st.text_input("Nombres", str(jd['nombres'])); ea=st.text_input("Apellidos", str(jd['apellidos'])); er=st.text_input("Responsable", str(jd['responsable'] or "")); et=st.text_input("Tel Responsable", str(jd['tel_responsable'] or "")); ee=st.selectbox("Estado", ["Actual","Desvinculado"], index=0 if jd['estado']=="Actual" else 1)
                    if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                        c.execute("UPDATE jovenes SET nombres=?, apellidos=?, responsable=?, tel_responsable=?, estado=? WHERE id=?", (en,ea,er,et,ee,int(jd['id'])))
                        conn.commit()
                        st.success("✅ Actualizado")
                        st.rerun()

    elif pag=="Permisos":
        st.title("Permisos")
        st.dataframe(pd.read_sql("SELECT p.id, j.nombres, j.apellidos, j.responsable, p.destino, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.id DESC", conn), use_container_width=True)
    elif pag=="Mensajería":
        st.title("Mensajería")
        msg = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn).iloc[0]['mensaje']
        with st.form("plant"):
            nuevo=st.text_area("Plantilla - Usa {nombre} {responsable} {destino} {fecha_salida} {hora_salida} {motivo}", msg, height=150)
            if st.form_submit_button("Guardar Plantilla"):
                c.execute("UPDATE mensajes SET mensaje=? WHERE tipo='Predeterminado'", (nuevo,))
                conn.commit()
                st.success("Plantilla guardada")
        st.dataframe(pd.read_sql("SELECT fecha, adolescente, contacto, tipo, estado, mensaje FROM mensajes ORDER BY id DESC", conn), use_container_width=True)
    elif pag=="Panel de Control" or True:
        if pag in ["Lista de Usuarios","Crear Usuarios","Contactos del Albergue","Informe Tutoría","Reportes","QR de Acceso","WhatsApp Web","Portal Joven"]:
            st.title(pag)
            if pag=="Lista de Usuarios": st.dataframe(pd.read_sql("SELECT documento,nombre,rol FROM usuarios", conn), use_container_width=True)
            if pag=="QR de Acceso":
                qr=generar_qr(LINK_NUBE)
                st.image(qr, width=300)
                st.download_button("Descargar", qr, "qr.png")
            if pag=="WhatsApp Web":
                tel=st.text_input("Número")
                men=st.text_area("Mensaje")
                if st.button("Generar WhatsApp"):
                    st.link_button("Abrir WhatsApp", f"https://wa.me/{limpiar_numero(tel)}?text={urllib.parse.quote(men)}")

if st.session_state.usuario is None:
    login()
else:
    app()
