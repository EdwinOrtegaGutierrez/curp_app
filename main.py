import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import time
from io import BytesIO

st.set_page_config(page_title="Consulta CURP", layout="wide")

st.title("🔍 Consulta Masiva de CURP")
st.subheader("Ejemplo de uso")
st.write("Sube un archivo Excel con la siguiente estructura:")
data = {
    "Nombre(s)*": ["edwin omar", "edwin omar"],
    "Primer apellido*": ["orte", "Ortega"],
    "Segundo apellido": ["gutierrez", "Gutierrez"],
    "Fecha de nacimiento": ["31/10/2002", "31/10/2002"],
    "Sexo*": ["No binario", "Hombre"],
    "Estado*": ["Jalisco", "Nacido en el extranjero"]
}

df = pd.DataFrame(data)

st.write(df)
st.write("La fecha debe estar en formato DD/MM/AAAA.")
archivo_excel = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

def procesar_datos(df_input):
    # Configurar Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Modo sin interfaz
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")

    driver = webdriver.Chrome(options=options)

    resultados = []

    def llenar_campo(id_elemento, valor):
        campo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, id_elemento))
        )
        campo.click()
        campo.send_keys(str(valor))

    for _, row in df_input.iterrows():
        driver.get("https://www.gob.mx/curp/")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "¿No conoces tu CURP?"))
        ).click()

        fecha = str(row["Fecha de nacimiento"].date()).split("-")

        try:
            llenar_campo("nombre", row["Nombre(s)*"])
            llenar_campo("primerApellido", row["Primer apellido*"])
            llenar_campo("segundoApellido", row["Segundo apellido"])
            llenar_campo("diaNacimiento", fecha[2])
            llenar_campo("mesNacimiento", fecha[1])
            llenar_campo("selectedYear", fecha[0])
            llenar_campo("sexo", row["Sexo*"])
            llenar_campo("claveEntidad", row["Estado*"])

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "searchButton"))
            ).click()

            time.sleep(2)

            try:
                modal = driver.find_element(By.CSS_SELECTOR, "div.modal-header h4.modal-title")
                if "aviso" in modal.text.lower():
                    resultados.append({
                        "CURP": "error de datos",
                        "Nombre(s)": row["Nombre(s)*"],
                        "Primer apellido": row["Primer apellido*"],
                        "Segundo apellido": row["Segundo apellido"],
                        "Fecha de nacimiento": row["Fecha de nacimiento"].date(),
                        "Entidad de nacimiento": row["Estado*"],
                        "Sexo": row["Sexo*"]
                    })
                    continue
            except:
                pass

            try:
                tablas = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                )

                datos = {}
                if tablas:
                    for fila in tablas[0].find_elements(By.TAG_NAME, "tr"):
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        if len(celdas) >= 2:
                            clave = celdas[0].text.strip().rstrip(":")
                            valor = celdas[1].text.strip()
                            datos[clave] = valor

                resultados.append({
                    "CURP": datos.get("CURP", ""),
                    "Nombre(s)": datos.get("Nombre(s)", row["Nombre(s)*"]),
                    "Primer apellido": datos.get("Primer apellido", row["Primer apellido*"]),
                    "Segundo apellido": datos.get("Segundo apellido", row["Segundo apellido"]),
                    "Fecha de nacimiento": datos.get("Fecha de nacimiento", row["Fecha de nacimiento"].date()),
                    "Entidad de nacimiento": datos.get("Entidad de nacimiento", row["Estado*"]),
                    "Sexo": datos.get("Sexo", row["Sexo*"])
                })

            except Exception:
                resultados.append({
                    "CURP": "error de datos",
                    "Nombre(s)": row["Nombre(s)*"],
                    "Primer apellido": row["Primer apellido*"],
                    "Segundo apellido": row["Segundo apellido"],
                    "Fecha de nacimiento": row["Fecha de nacimiento"].date(),
                    "Entidad de nacimiento": row["Estado*"],
                    "Sexo": row["Sexo*"]
                })

        except Exception as e:
            st.error(f"Error con: {row['Nombre(s)*']} - {str(e)}")
            resultados.append({
                "CURP": "error de datos",
                "Nombre(s)": row["Nombre(s)*"],
                "Primer apellido": row["Primer apellido*"],
                "Segundo apellido": row["Segundo apellido"],
                "Fecha de nacimiento": row["Fecha de nacimiento"].date(),
                "Entidad de nacimiento": row["Estado*"],
                "Sexo": row["Sexo*"]
            })

    driver.quit()
    return pd.DataFrame(resultados)

if archivo_excel:
    df_input = pd.read_excel(archivo_excel)

    if st.button("🔄 Procesar CURPs"):
        with st.spinner("Procesando..."):
            df_resultados = procesar_datos(df_input)

        st.success("✅ Procesamiento completo.")

        # Mostrar resultados
        df_ok = df_resultados[df_resultados["CURP"] != "error de datos"]
        df_errores = df_resultados[df_resultados["CURP"] == "error de datos"]

        st.subheader("✅ Procesados correctamente")
        st.dataframe(df_ok)

        st.subheader("⚠️ Errores encontrados")
        st.dataframe(df_errores)

        # Botón de descarga
        def convertir_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        st.download_button(
            label="📥 Descargar resultados",
            data=convertir_excel(df_resultados),
            file_name="curps_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
