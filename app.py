import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import qrcode
from io import BytesIO
import urllib.parse

LINK_NUBE = "https://azulgrana-roga.streamlit.app/?pagina=portal"
LINK_BASE = "https://azulgrana-roga.streamlit.app"
TELEFONO_ALBERGUE = "595981123456"

st.set_page_config(page_title="Azulgrana Róga", layout="wide", page_icon="🏠")
st.markdown("""<style>
.stApp {background-color: #001F3F;} [data-testid="stSidebar"] {background-color: #00004B;} [data-testid="stSidebar"] * {color: white;}
.stButton>button {background-color: #FF0000;color: white;border-radius: 10px;border: 2px solid #00529F;font-weight: bold;}
h1, h2, h3 {color: #00529F; font-weight: bold;} [data-testid="stDataFrame"] {background-color: white!important;} [data-testid="stDataFrame"] * {color: black!important;}
#MainMenu, footer {display:none!important;}
</style>""", unsafe_allow_html=True)

conn = sqlite3.connect('albergue.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (documento TEXT PRIMARY KEY, nombre TEXT, password TEXT, rol TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS jovenes (id INTEGER PRIMARY KEY AUTOINCREMENT, documento TEXT, nombres TEXT, apellidos TEXT, fecha_nac DATE, ciudad TEXT, barrio TEXT, direccion TEXT, telefono TEXT, responsable TEXT, parentesco TEXT, tel_responsable TEXT, fecha_ingreso DATE, estado TEXT, habitacion TEXT, cama TEXT, colegio TEXT, grado TEXT, deporte TEXT, posicion TEXT, categoria TEXT, turno TEXT, foto_url TEXT, motivo_ingreso TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS permisos (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha_sol DATE, fecha_salida DATE, hora_salida TEXT, fecha_regreso DATE, hora_regreso TEXT, tipo_salida TEXT, destino TEXT, persona_salida TEXT, parentesco TEXT, tel_contacto TEXT, motivo TEXT, estado TEXT DEFAULT 'Pendiente', hora_regreso_real TEXT, qr_id TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, adolescente TEXT, contacto TEXT, tipo TEXT, mensaje TEXT, estado TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, desarrollo TEXT, rutinas TEXT, infraestructura TEXT, observaciones TEXT, necesidad TEXT, prioridad TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tutoria_joven (id INTEGER PRIMARY KEY AUTOINCREMENT, joven_id INTEGER, fecha DATE, informe TEXT)''')
c.execute("INSERT OR IGNORE INTO mensajes (id, tipo, mensaje) VALUES (1, 'Predeterminado', 'Hola {responsable}. Su hijo/a {nombre} solicita salida de Azulgrana Róga. Destino: {destino} - Fecha: {fecha_salida} {hora_salida}. Motivo: {motivo}')")
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

for k in ['usuario','rol']:
    if k not in st.session_state: st.session_state[k]=None

# APROBACION POR LINK
accion = str(st.query_params.get("accion", "")).lower()
id_accion = st.query_params.get("id", "")
if accion in ["aprobar", "rechazar"] and id_accion:
    nuevo = "Aprobado" if accion=="aprobar" else "Rechazado"
    c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo, int(id_accion)))
    conn.commit()
    info = pd.read_sql("SELECT j.nombres, j.apellidos, j.responsable FROM permisos p JOIN jovenes j ON p.joven_id=j.id WHERE p.id=?", conn, params=(int(id_accion),))
    if not info.empty:
        texto = f"RESPUESTA {nuevo}: {info.iloc[0]['responsable']} ha {nuevo} a {info.iloc[0]['nombres']} {info.iloc[0]['apellidos']} ID:{id_accion}"
        c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"{info.iloc[0]['nombres']} {info.iloc[0]['apellidos']}", "Albergue", f"Link {nuevo}", texto, nuevo))
        conn.commit()
        st.markdown(f"<h1 style='color:white;text-align:center;margin-top:80px;'>✅ Solicitud {id_accion} {nuevo}</h1><p style='color:white;text-align:center;'>Ya se actualizó en el Panel de Control</p>", unsafe_allow_html=True)
        st.balloons()
        st.stop()

# PORTAL JOVEN
if str(st.query_params.get("pagina","")).lower() in ["portal","portal joven"]:
    st.markdown("<h1 style='color:white;'>Portal del Joven</h1>", unsafe_allow_html=True)
    doc = st.text_input("Ingresá tu documento")
    if doc:
        j = pd.read_sql("SELECT * FROM jovenes WHERE documento=?", conn, params=(doc,))
        if j.empty: st.error("No encontrado")
        elif j.iloc[0]['estado']!="Actual": st.error("No ACTIVO")
        else:
            jd=j.iloc[0]
            st.success(f"{jd['nombres']} {jd['apellidos']}")
            plant = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn).iloc[0]['mensaje']
            with st.form("sol"):
                c1,c2=st.columns(2)
                with c1:
                    fs=st.date_input("Fecha salida"); hs=st.time_input("Hora salida"); fr=st.date_input("Fecha regreso"); hr=st.time_input("Hora regreso")
                with c2:
                    tipo=st.selectbox("Tipo",["Familiar","Médico","Deportivo","Personal","Otro"]); dest=st.text_input("Destino *"); pers=st.text_input("Con quien sale"); mot=st.text_area("Motivo")
                if st.form_submit_button("Enviar solicitud", type="primary", use_container_width=True):
                    if not dest: st.warning("Destino obligatorio")
                    else:
                        c.execute("INSERT INTO permisos (joven_id,fecha_sol,fecha_salida,hora_salida,fecha_regreso,hora_regreso,tipo_salida,destino,persona_salida,motivo,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (jd['id'], str(date.today()), str(fs), str(hs), str(fr), str(hr), tipo, dest, pers, mot, "Pendiente"))
                        conn.commit()
                        id_nuevo=c.lastrowid
                        txt_base = plant.replace("{nombre}", f"{jd['nombres']} {jd['apellidos']}").replace("{responsable}", str(jd['responsable'])).replace("{destino}", dest).replace("{fecha_salida}", str(fs)).replace("{hora_salida}", str(hs)).replace("{motivo}", mot)
                        link_ap = f"{LINK_BASE}/?accion=aprobar&id={id_nuevo}"
                        link_re = f"{LINK_BASE}/?accion=rechazar&id={id_nuevo}"
                        txt_final = f"{txt_base}\n\n✅ APROBAR: {link_ap}\n❌ RECHAZAR: {link_re}"
                        tel=limpiar_numero(jd['tel_responsable'])
                        url_wp=f"https://wa.me/{tel}?text={urllib.parse.quote(txt_final)}"
                        c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"{jd['nombres']} {jd['apellidos']}", jd['responsable'], "Salida", txt_final, "Pendiente"))
                        conn.commit()
                        st.success(f"Solicitud #{id_nuevo} PENDIENTE enviada")
                        st.link_button(f"📱 Enviar WhatsApp a {jd['responsable']}", url_wp, use_container_width=True)
    st.stop()

def login():
    _,c2,_=st.columns([1,2,1])
    with c2:
        st.image("Logo.png", width=120)
        d=st.text_input("Documento"); p=st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            u=pd.read_sql("SELECT * FROM usuarios WHERE documento=? AND password=?", conn, params=(d,p))
            if not u.empty:
                st.session_state.usuario=u.iloc[0]['nombre']; st.session_state.rol=u.iloc[0]['rol']; st.rerun()
            else: st.error("Incorrecto")

def app():
    st.sidebar.image("Logo.png", width=120)
    MENU = ["Panel de Control", "Jovenes", "Permisos", "WhatsApp Web", "Mensajería", "Reportes", "QR de Acceso"]
    if st.session_state.rol=="Director": MENU += ["Lista de Usuarios","Crear Usuarios"]
    pag = st.sidebar.radio("Menú", MENU)
    if st.sidebar.button("Cerrar Sesión", type="primary", use_container_width=True):
        st.session_state.usuario=None; st.rerun()

    if pag=="Panel de Control":
        st.title("Panel de Control")
        df_j = pd.read_sql("SELECT * FROM jovenes", conn)
        df_p = pd.read_sql("SELECT * FROM permisos", conn)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("EN ALBERGUE", len(df_j[df_j['estado']=="Actual"]) if not df_j.empty else 0)
        c2.metric("PENDIENTES", len(df_p[df_p['estado']=="Pendiente"]) if not df_p.empty else 0)
        c3.metric("APROBADOS", len(df_p[df_p['estado']=="Aprobado"]) if not df_p.empty else 0)
        c4.metric("RECHAZADOS", len(df_p[df_p['estado']=="Rechazado"]) if not df_p.empty else 0)
        if not df_p.empty:
            df_tabla = pd.read_sql("""SELECT p.id as ID, j.nombres || ' ' || j.apellidos as Adolescente, j.responsable as Responsable, p.fecha_sol as Solicitud, p.destino as Destino, p.estado as Resultado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.id DESC""", conn)
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    elif pag=="WhatsApp Web":
        st.title("📱 WhatsApp Web - Centro de Mensajes")

        col_qr, col_info = st.columns([1,2])
        with col_qr:
            st.subheader("Conectar por QR")
            # QR que abre WhatsApp Web
            qr_wp = generar_qr("https://web.whatsapp.com")
            st.image(qr_wp, width=180)
            st.link_button("🔗 Abrir WhatsApp Web", "https://web.whatsapp.com", use_container_width=True)
            st.caption("1. Tocá el botón\n2. En tu celular: WhatsApp > 3 puntitos > Dispositivos vinculados > Vincular\n3. Escaneá el QR de la PC")

        with col_info:
            st.subheader("Enviar mensaje al responsable")
            st.caption("Usa la plantilla de Mensajería")
            plantilla = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn).iloc[0]['mensaje']
            st.code(plantilla, language=None)
            tel_env = st.text_input("Número del responsable (ej: 0981123456)")
            id_env = st.number_input("ID Permiso a enviar (opcional, para incluir links)", min_value=0, step=1)
            mensaje_manual = st.text_area("Mensaje a enviar", value=plantilla, height=150)

            if st.button("Generar Link WhatsApp", type="primary", use_container_width=True):
                if not tel_env: st.warning("Poné número")
                else:
                    txt_final = mensaje_manual
                    if id_env>0:
                        txt_final += f"\n\n✅ APROBAR: {LINK_BASE}/?accion=aprobar&id={id_env}\n❌ RECHAZAR: {LINK_BASE}/?accion=rechazar&id={id_env}"
                    url = f"https://wa.me/{limpiar_numero(tel_env)}?text={urllib.parse.quote(txt_final)}"
                    st.link_button(f"📲 Abrir WhatsApp para enviar", url, use_container_width=True)
                    c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"ID {id_env}", tel_env, "Enviado Manual", txt_final, "Pendiente"))
                    conn.commit()

        st.markdown("---")
        st.subheader("Registrar respuesta que viene por WhatsApp")
        st.info("Cuando el papá te responde APROBADO o RECHAZADO por WhatsApp, pegá acá su mensaje para que se actualice el Panel")
        c_a, c_b = st.columns(2)
        with c_a: id_resp = st.number_input("ID Permiso", min_value=1, step=1, key="id_resp_wp")
        with c_b: contacto_resp = st.text_input("Nombre contacto", key="contact_resp")
        resp_wp = st.text_area("Pegá lo que respondió por WhatsApp", key="resp_wp")

        if st.button("✅ Procesar Respuesta de WhatsApp y Actualizar Panel", type="primary", use_container_width=True):
            if not resp_wp: st.warning("Pegá la respuesta")
            else:
                txt = resp_wp.upper()
                if "APROB" in txt: nuevo="Aprobado"
                elif "RECHAZ" in txt or "NO AUTORIZO" in txt: nuevo="Rechazado"
                else:
                    st.error("No encontré APROBADO o RECHAZADO")
                    st.stop()
                c.execute("UPDATE permisos SET estado=? WHERE id=?", (nuevo, int(id_resp)))
                c.execute("INSERT INTO mensajes (fecha, adolescente, contacto, tipo, mensaje, estado) VALUES (?,?,?,?,?,?)", (str(date.today()), f"ID {id_resp}", contacto_resp, f"Respuesta WhatsApp {nuevo}", resp_wp, nuevo))
                conn.commit()
                st.success(f"Permiso #{id_resp} ahora {nuevo} - Ya está en Panel de Control")
                st.balloons()
                st.rerun()

        st.markdown("---")
        st.subheader("📜 Historial completo de WhatsApp")
        df_hist = pd.read_sql("SELECT id, fecha, adolescente as Adolescente, contacto as Contacto, tipo as Tipo, estado as Estado, mensaje as Mensaje FROM mensajes ORDER BY id DESC", conn)
        st.dataframe(df_hist, use_container_width=True)

    elif pag=="Jovenes":
        st.title("Jovenes")
        st.dataframe(pd.read_sql("SELECT * FROM jovenes", conn), use_container_width=True)
        with st.form("add", clear_on_submit=True):
            d=st.text_input("Documento"); n=st.text_input("Nombres"); a=st.text_input("Apellidos"); r=st.text_input("Responsable"); tr=st.text_input("Tel Responsable")
            if st.form_submit_button("Guardar"):
                c.execute("INSERT INTO jovenes (documento,nombres,apellidos,responsable,tel_responsable,estado) VALUES (?,?,?,?,?,?)", (d,n,a,r,tr,"Actual"))
                conn.commit()
                st.rerun()

    elif pag=="Mensajería":
        st.title("Plantilla")
        msg = pd.read_sql("SELECT mensaje FROM mensajes WHERE tipo='Predeterminado' LIMIT 1", conn).iloc[0]['mensaje']
        with st.form("plant"):
            nuevo=st.text_area("Plantilla {nombre} {responsable} {destino} {fecha_salida} {hora_salida} {motivo}", msg, height=150)
            if st.form_submit_button("Guardar"):
                c.execute("UPDATE mensajes SET mensaje=? WHERE tipo='Predeterminado'", (nuevo,))
                conn.commit()
                st.success("Guardado")

    elif pag=="Permisos":
        st.dataframe(pd.read_sql("SELECT p.id, j.nombres, j.apellidos, p.destino, p.estado FROM permisos p JOIN jovenes j ON p.joven_id=j.id ORDER BY p.id DESC", conn), use_container_width=True)
    elif pag=="QR de Acceso":
        st.image(generar_qr(LINK_NUBE), width=250)
        st.code(LINK_NUBE)

if st.session_state.usuario is None:
    login()
else:
    app()
