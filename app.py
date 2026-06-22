import streamlit as st
import pandas as pd
import mysql.connector

st.set_page_config(page_title="Control de Insumos", layout="wide")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = ""
if 'rol_actual' not in st.session_state:
    st.session_state['rol_actual'] = ""


def conectar_db():
    return mysql.connector.connect(
        host="mysql-escinv.alwaysdata.net",
        user="escinv_IthanR",
        password="23Ene2003",
        database="escinv_hola"
    )


if not st.session_state['autenticado']:
    st.title("Acceso al Sistema")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("Ingresa tus credenciales para administrar el inventario.")
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            contrasena = st.text_input("Contraseña", type="password")
            btn_ingresar = st.form_submit_button("Ingresar")

            if btn_ingresar:
                try:
                    db = conectar_db()
                    cursor = db.cursor(dictionary=True)
                    query = "SELECT * FROM usuarios WHERE usuario = %s AND contrasena = %s"
                    cursor.execute(query, (usuario, contrasena))
                    usuario_valido = cursor.fetchone()
                    cursor.close()
                    db.close()

                    if usuario_valido:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_actual'] = usuario_valido['usuario']
                        st.session_state['rol_actual'] = usuario_valido.get('tipo', 'Administrador')
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error de conexión a la base de datos: {e}")

else:
    st.title("Sistema de Control de Inventario e Insumos")

    st.sidebar.markdown(f"### Bienvenido, {st.session_state['usuario_actual']}")
    st.sidebar.markdown(f"**Rol:** {st.session_state['rol_actual']}")

    # MUESTRA DE PRIVILEGIOS AL USUARIO Y DEFINICIÓN DE MENÚ
    st.sidebar.markdown("**Tus Privilegios:**")
    if st.session_state['rol_actual'] == 'Administrador':
        st.sidebar.info("Acceso Total: Puedes ver reportes, gestionar usuarios y modificar el inventario.")
        menu = ["Catálogo de Productos", "Altas y Bajas de Insumos", "Reporte de Movimientos", "Gestión de Usuarios"]
    else:
        st.sidebar.info("Acceso Operativo: Limitado a consultar el catálogo y registrar entradas o salidas de stock.")
        menu = ["Catálogo de Productos", "Altas y Bajas de Insumos"]

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.session_state['usuario_actual'] = ""
        st.session_state['rol_actual'] = ""
        st.rerun()

    st.sidebar.markdown("---")

    eleccion = st.sidebar.selectbox("Módulo", menu)

    if eleccion == "Catálogo de Productos":
        st.subheader("Catálogo Maestro de Insumos")

        with st.expander("Registrar nuevo insumo en el catálogo"):
            with st.form("form_catalogo"):
                codigo = st.text_input("Código único / SKU")
                nombre = st.text_input("Nombre del Insumo")
                desc = st.text_area("Descripción")
                stock_ini = st.number_input("Stock Inicial", min_value=0, value=0)
                btn_guardar = st.form_submit_button("Añadir al Catálogo")

                if btn_guardar:
                    if codigo and nombre:
                        try:
                            db = conectar_db()
                            cursor = db.cursor()
                            query = "INSERT INTO insumos (codigo, nombre, descripcion, stock_actual) VALUES (%s, %s, %s, %s)"
                            valores = (codigo, nombre, desc, stock_ini)
                            cursor.execute(query, valores)
                            db.commit()
                            cursor.close()
                            db.close()
                            st.success(f"Insumo '{nombre}' guardado exitosamente en la base de datos.")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("Por favor, llena los campos obligatorios (Código y Nombre).")

        st.markdown("---")
        st.write("### Productos Registrados")

        try:
            db = conectar_db()
            query = "SELECT codigo AS 'Código', nombre AS 'Nombre', descripcion AS 'Descripción', stock_actual AS 'Stock Actual' FROM insumos"
            df_insumos = pd.read_sql(query, db)
            db.close()

            if not df_insumos.empty:
                st.dataframe(df_insumos, use_container_width=True)
            else:
                st.info("El catálogo está vacío. Agrega un insumo arriba para empezar.")
        except Exception as e:
            st.error(f"Error al cargar el catálogo: {e}")

    elif eleccion == "Altas y Bajas de Insumos":
        st.subheader("Registrar Movimiento de Inventario")

        insumos_db = []
        try:
            db = conectar_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id_insumo, codigo, nombre FROM insumos")
            insumos_db = cursor.fetchall()
            cursor.close()
            db.close()
        except Exception as e:
            st.error(f"Error al cargar productos: {e}")

        opciones_insumos = {f"{i['codigo']} - {i['nombre']}": i['id_insumo'] for i in insumos_db}

        if opciones_insumos:
            with st.form("form_movimientos"):
                insumo_seleccionado = st.selectbox("Selecciona el insumo", list(opciones_insumos.keys()))
                tipo_movimiento = st.radio("Tipo de movimiento", ["Alta (Entrada)", "Baja (Salida)"])
                cantidad = st.number_input("Cantidad", min_value=1, step=1)
                motivo = st.text_input("Motivo / Referencia", placeholder="Ej: Compra a proveedor, Ajuste por daño")
                btn_registrar = st.form_submit_button("Procesar Movimiento")

                if btn_registrar:
                    id_insumo_elegido = opciones_insumos[insumo_seleccionado]
                    tipo_db = 'Alta' if "Alta" in tipo_movimiento else 'Baja'

                    try:
                        db = conectar_db()
                        cursor = db.cursor()

                        query_mov = "INSERT INTO movimientos (id_insumo, tipo, cantidad, motivo) VALUES (%s, %s, %s, %s)"
                        cursor.execute(query_mov, (id_insumo_elegido, tipo_db, cantidad, motivo))

                        if tipo_db == 'Alta':
                            query_stock = "UPDATE insumos SET stock_actual = stock_actual + %s WHERE id_insumo = %s"
                        else:
                            query_stock = "UPDATE insumos SET stock_actual = stock_actual - %s WHERE id_insumo = %s"

                        cursor.execute(query_stock, (cantidad, id_insumo_elegido))
                        db.commit()
                        cursor.close()
                        db.close()
                        st.success("Movimiento procesado y stock actualizado correctamente.")
                    except Exception as e:
                        st.error(f"Error al procesar el movimiento: {e}")
        else:
            st.info("No hay insumos registrados en el catálogo todavía.")

    elif eleccion == "Reporte de Movimientos":
        st.subheader("Historial y Reporte General de Altas y Bajas")

        col1, col2 = st.columns(2)
        with col1:
            filtro_tipo = st.multiselect("Filtrar por tipo:", ["Alta", "Baja"], default=["Alta", "Baja"])

        try:
            db = conectar_db()
            query_reporte = """
                            SELECT m.fecha AS 'Fecha y Hora', i.codigo AS 'Código', i.nombre AS 'Insumo', m.tipo AS 'Tipo', m.cantidad AS 'Cantidad', m.motivo AS 'Motivo'
                            FROM movimientos m
                                     JOIN insumos i ON m.id_insumo = i.id_insumo
                            ORDER BY m.fecha DESC \
                            """
            df_reporte = pd.read_sql(query_reporte, db)
            db.close()

            if not df_reporte.empty:
                df_filtrado = df_reporte[df_reporte['Tipo'].isin(filtro_tipo)]
                st.dataframe(df_filtrado, use_container_width=True)

                st.download_button(
                    label="Descargar Reporte en CSV",
                    data=df_filtrado.to_csv(index=False).encode('utf-8'),
                    file_name='reporte_altas_bajas.csv',
                    mime='text/csv'
                )
            else:
                st.info("Aún no hay movimientos registrados.")
        except Exception as e:
            st.error(f"Error al cargar el reporte: {e}")

    elif eleccion == "Gestión de Usuarios":
        st.subheader("Administración de Accesos al Sistema")

        with st.expander("Registrar Nuevo Usuario"):
            with st.form("form_usuarios"):
                nuevo_usuario = st.text_input("Nombre de Usuario")
                nueva_contrasena = st.text_input("Contraseña", type="password")
                nuevo_tipo = st.selectbox("Tipo de Usuario", ["Administrador", "Usuario"])
                btn_guardar_usuario = st.form_submit_button("Crear Usuario")

                if btn_guardar_usuario:
                    if nuevo_usuario and nueva_contrasena:
                        try:
                            db = conectar_db()
                            cursor = db.cursor()
                            query = "INSERT INTO usuarios (usuario, contrasena, tipo) VALUES (%s, %s, %s)"
                            cursor.execute(query, (nuevo_usuario, nueva_contrasena, nuevo_tipo))
                            db.commit()
                            cursor.close()
                            db.close()
                            st.success(f"Usuario '{nuevo_usuario}' de tipo '{nuevo_tipo}' creado exitosamente.")
                        except mysql.connector.IntegrityError:
                            st.error("Ese nombre de usuario ya existe. Elige otro.")
                        except Exception as e:
                            st.error(f"Error al crear usuario: {e}")
                    else:
                        st.warning("Debes llenar todos los campos.")

        st.markdown("---")
        st.write("### Usuarios Registrados y sus Privilegios")

        try:
            db = conectar_db()
            query = "SELECT id_usuario AS 'ID', usuario AS 'Usuario', tipo AS 'Rol' FROM usuarios ORDER BY tipo ASC, usuario ASC"
            df_usuarios = pd.read_sql(query, db)
            db.close()

            if not df_usuarios.empty:
                def asignar_privilegios(rol):
                    if rol == 'Administrador':
                        return 'Acceso Total (Catálogo, Movimientos, Reportes y Usuarios)'
                    else:
                        return 'Acceso Operativo (Solo Catálogo y Movimientos)'


                df_usuarios['Privilegios Asignados'] = df_usuarios['Rol'].apply(asignar_privilegios)

                filtro_rol = st.selectbox("Filtrar la tabla por rol:", ["Todos", "Administrador", "Usuario"])

                if filtro_rol != "Todos":
                    df_mostrar = df_usuarios[df_usuarios['Rol'] == filtro_rol]
                else:
                    df_mostrar = df_usuarios

                st.dataframe(df_mostrar, use_container_width=True)
        except Exception as e:
            st.error(f"Error al cargar los usuarios: {e}")