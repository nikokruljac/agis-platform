# =====================================================================
# MÓDULO 5: AGIS STUDIO (CENTRO DE CONTROL ADMINISTRATIVO)
# =====================================================================

with tab5:
    st.header("💻 AGIS Studio: Centro de Control")
    st.info("Panel exclusivo para administración de usuarios y carga de datos.")
    
    sub_tab1, sub_tab2 = st.tabs(["👥 Gestión de Usuarios", "📂 Carga de Datos en Línea"])
    
    # --- SUB-TAB 1: GESTIÓN DE USUARIOS ---
    with sub_tab1:
        st.subheader("👥 Gestión de Usuarios")
        
        # Formulario para registrar nuevo usuario
        with st.expander("➕ Registrar Nuevo Usuario"):
            with st.form("form_usuario", clear_on_submit=True):
                nombre_usuario = st.text_input("Nombre y Apellido")
                user_login = st.text_input("Nombre de Usuario (Login)")
                pass_usuario = st.text_input("Contraseña", type="password")
                email_usuario = st.text_input("Email")
                telefono_usuario = st.text_input("WhatsApp (+549...)", placeholder="+549...")
                perfil_usuario = st.selectbox("Perfil", ["Productor", "Técnico", "Administrador"])
                chacras_asignadas = st.text_area("Chacras asignadas (separadas por coma)")
                btn_guardar_usuario = st.form_submit_button("Guardar Usuario")
                
            if btn_guardar_usuario:
                if nombre_usuario and user_login and pass_usuario:
                    try:
                        hash_pass = hashlib.sha256(pass_usuario.encode()).hexdigest()
                        conn = sqlite3.connect("database/agis_database.db")
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO usuarios (nombre, username, password, email, telefono, perfil, chacras)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (nombre_usuario, user_login, hash_pass, email_usuario, telefono_usuario, perfil_usuario, chacras_asignadas))
                        conn.commit()
                        conn.close()
                        st.success(f"Usuario {nombre_usuario} registrado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El usuario ya existe.")
                else:
                    st.error("Campos obligatorios incompletos.")

        st.divider()
        st.subheader("📋 Usuarios Registrados")
        
        # Obtener lista actualizada
        conn = sqlite3.connect("database/agis_database.db")
        df_usuarios = pd.read_sql_query("SELECT id, nombre, username, perfil FROM usuarios", conn)
        conn.close()

        # Mostrar tabla interactiva con acciones
        for index, row in df_usuarios.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['username']}** ({row['perfil']}) - {row['nombre']}")
            
            # Acción: Eliminar
            if c2.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                conn = sqlite3.connect("database/agis_database.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (row['id'],))
                conn.commit()
                conn.close()
                st.rerun()
                
            # Acción: Editar
            if c3.button("✏️ Editar", key=f"edit_{row['id']}"):
                st.session_state[f"edit_mode_{row['id']}"] = True

            # Formulario de edición (solo aparece si se presiona editar)
            if st.session_state.get(f"edit_mode_{row['id']}", False):
                with st.form(key=f"form_edit_{row['id']}"):
                    nuevo_nombre = st.text_input("Nuevo Nombre", value=row['nombre'])
                    btn_confirmar = st.form_submit_button("Guardar Cambios")
                    if btn_confirmar:
                        conn = sqlite3.connect("database/agis_database.db")
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", (nuevo_nombre, row['id']))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_mode_{row['id']}"] = False
                        st.rerun()

    # --- SUB-TAB 2: CARGA DE DATOS EN LÍNEA ---
    with sub_tab2:
        st.subheader("📂 Carga de Datos Semanales")
        conn = sqlite3.connect("database/agis_database.db")
        nombres_usuarios = pd.read_sql_query("SELECT username FROM usuarios", conn)['username'].tolist()
        conn.close()
        
        user_sel = st.selectbox("Seleccionar Cliente:", nombres_usuarios, key="sel_user_carga")
        chacra_sel = st.text_input("Nombre de la Chacra:", key="in_chacra_carga")
        archivo = st.file_uploader("Subir Archivo (CSV/TIF)", type=['csv', 'tif'], key="uploader_archivo")
        
        if st.button("Procesar y Asignar"):
            if user_sel and chacra_sel and archivo:
                ruta_dir = os.path.join("uploads", user_sel, chacra_sel)
                os.makedirs(ruta_dir, exist_ok=True)
                ruta_archivo = os.path.join(ruta_dir, archivo.name)
                with open(ruta_archivo, "wb") as f:
                    f.write(archivo.getbuffer())
                st.success(f"Archivo {archivo.name} guardado para {user_sel}.")
                st.balloons()
            else:
                st.error("Por favor completa el cliente, chacra y selecciona un archivo.")
