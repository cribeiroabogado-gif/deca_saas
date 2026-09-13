import os
import datetime
import streamlit as st
from deca_generator import DecaGenerator, publicar_en_nas, REPOSITORY_DIR

st.set_page_config(page_title="Emisión de DeCA - Boutique Legal Transporte", layout="wide")

st.title("Generador de Documentos Electrónicos de Control (DeCA)")
st.caption("Conforme a la Orden FOM/2861/2012 y la Resolución de 5 de junio de 2026")

with st.form("deca_form"):
    st.subheader("1. Identificación del Envío")
    col_id1, _ = st.columns(2)
    with col_id1:
        num_deca = st.number_input("Número correlativo", min_value=1, value=1, step=1)
        deca_id = f"DECA-{datetime.datetime.now().year}-{int(num_deca):05d}"
        st.info(f"ID DeCA: **{deca_id}**")

    st.subheader("2. Intervinientes en el Transporte")
    col_carg, col_trans = st.columns(2)
    
    with col_carg:
        st.markdown("### Cargador Principal / Remitente")
        cargador_nombre = st.text_input("Razón Social Cargador", "LOGÍSTICA ALIMENTARIA S.A.")
        cargador_nif = st.text_input("NIF Cargador", "A12345678")
        cargador_domicilio = st.text_input("Domicilio Cargador", "Av. de la Industria 45, Madrid")

    with col_trans:
        st.markdown("### Transportista Efectivo")
        transportista_nombre = st.text_input("Razón Social Transportista", "TRANSPORTES RÁPIDOS S.L.")
        transportista_nif = st.text_input("NIF Transportista", "B98765432")
        transportista_domicilio = st.text_input("Domicilio Transportista", "Calle Transporte 12, Valencia")

    st.markdown("### Cadena de Subcontratación / Intermediarios")
    num_agencias = st.number_input("Número de agencias intermediarias", min_value=0, max_value=5, value=0)
    
    agencias_list = []
    for i in range(int(num_agencias)):
        st.markdown(f"**Intermediario N.º {i+1}**")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            nom_ag = st.text_input(f"Nombre/Razón Agencia {i+1}", key=f"ag_nom_{i}")
        with col_a2:
            nif_ag = st.text_input(f"NIF Agencia {i+1}", key=f"ag_nif_{i}")
        if nom_ag:
            agencias_list.append(f"Agencia {i+1}: {nom_ag} (NIF: {nif_ag})")

    st.subheader("3. Datos del Viaje")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        origen_lugar = st.text_input("Lugar de Carga", "Mercamadrid, Nave 4, Madrid")
        fecha_carga = st.text_input("Fecha y Hora Carga", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    with col_r2:
        destino_lugar = st.text_input("Lugar de Descarga", "Puerto de Valencia, Muelle 3")
        fecha_descarga = st.text_input("Fecha y Hora Descarga", (datetime.datetime.now() + datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"))

    st.subheader("4. Mercancía y Vehículo")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        mercancia = st.text_area("Descripción Mercancía", "Productos refrigerados")
        peso_kg = st.number_input("Peso Bruto (kg)", value=18500)
    with col_m2:
        bultos = st.number_input("N.º Bultos", value=24)
        matricula = st.text_input("Matrícula Tractora", "1234-BBB")
    with col_m3:
        remolque = st.text_input("Matrícula Remolque", "R-5678-BBB")
        obs_adicionales = st.text_input("Observaciones", "Mantener temperatura +4°C")

    submitted = st.form_submit_button("Generar y Publicar DeCA")

if submitted:
    cadena_texto = ""
    if agencias_list:
        cadena_texto = " | Subcontratación: " + " -> ".join(agencias_list)
    
    observaciones_totales = f"{obs_adicionales}{cadena_texto}"

    deca_data = {
        "creation_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cargador_nombre": cargador_nombre,
        "cargador_nif": cargador_nif,
        "cargador_domicilio": cargador_domicilio,
        "transportista_nombre": transportista_nombre,
        "transportista_nif": transportista_nif,
        "transportista_domicilio": transportista_domicilio,
        "origen_lugar": origen_lugar,
        "fecha_carga": fecha_carga,
        "destino_lugar": destino_lugar,
        "fecha_descarga": fecha_descarga,
        "mercancia_descripcion": mercancia,
        "peso_kg": peso_kg,
        "bultos": bultos,
        "matricula": matricula,
        "remolque": remolque,
        "observaciones": observaciones_totales
    }

    output_pdf_file = os.path.join(REPOSITORY_DIR, f"{deca_id}.pdf")

    try:
        DecaGenerator.generate_deca_pdf(deca_id, deca_data, output_pdf_file)
        publicar_en_nas(output_pdf_file)
        st.success(f"DeCA {deca_id} generado y publicado correctamente en el NAS.")
    except Exception as e:
        st.error(f"Error durante el proceso: {e}")