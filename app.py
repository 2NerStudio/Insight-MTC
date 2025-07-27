import streamlit as st
import tempfile
import os
import subprocess
import time  # Para timeout global
try:
    from docx2pdf import convert  # Alternativa para conversão (pip install docx2pdf)
except ImportError:
    convert = None

from validacao_dinamica import (
    extrair_parametros_valores,
    validar_parametros,
    gerar_relatorio,
)

# ========================================
# LOGIN SIMPLES
# ========================================
usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10",
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.title("🔐 Área de Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuarios_autorizados.get(usuario) == senha:
            st.session_state.autenticado = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")
    st.stop()

# ========================================
# APP PRINCIPAL
# ========================================
st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")
st.sidebar.success("🔓 Autenticado")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.experimental_rerun()

st.title("🌿 MTC Insight Pro")
st.caption("Suporta PDF e DOCX e valida parâmetros diretamente do arquivo")

# Terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Upload
st.subheader("📎 Upload do Relatório (.pdf ou .docx)")
arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "docx"])

if st.button("⚙️ Validar Parâmetros"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Envie um arquivo PDF ou DOCX.")
    else:
        with st.status("🔍 Processando...", expanded=True) as status:
            tmp_input = None
            pdf_path = None
            start_time = time.time()  # Início do timer
            try:
                if time.time() - start_time > 60:
                    raise TimeoutError("Processamento demorou demais – tente um arquivo menor.")

                print("LOG: Iniciando salvamento de arquivo...")  # Logging para nuvem
                status.update(label="Salvando arquivo temporário...")
                ext = os.path.splitext(arquivo.name)[1].lower()
                tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_input.write(arquivo.read())
                tmp_input.close()

                if time.time() - start_time > 60:
                    raise TimeoutError("Processamento demorou demais – tente um arquivo menor.")

                print("LOG: Iniciando conversão...")  # Logging
                status.update(label="Convertendo DOCX para PDF se necessário...")
                if ext == ".docx":
                    tmp_pdf = tmp_input.name.replace(".docx", ".pdf")
                    if convert:
                        convert(tmp_input.name, tmp_pdf)
                    else:
                        subprocess.run(
                            ["libreoffice", "--headless", "--convert-to", "pdf", tmp_input.name, "--outdir", os.path.dirname(tmp_input.name)],
                            check=True, timeout=30
                        )
                    pdf_path = tmp_pdf
                    if not os.path.exists(pdf_path):
                        raise FileNotFoundError("Falha na conversão de DOCX para PDF. Verifique LibreOffice ou instale docx2pdf.")
                else:
                    pdf_path = tmp_input.name

                if time.time() - start_time > 60:
                    raise TimeoutError("Processamento demorou demais – tente um arquivo menor.")

                print("LOG: Iniciando extração...")  # Logging
                status.update(label="Extraindo parâmetros do PDF...")
                dados = extrair_parametros_valores(pdf_path)
                if not dados:
                    raise ValueError("Nenhum parâmetro extraído. Verifique se o PDF contém tabelas válidas.")

                if time.time() - start_time > 60:
                    raise TimeoutError("Processamento demorou demais – tente um arquivo menor.")

                print("LOG: Iniciando validação...")  # Logging
                status.update(label="Validando parâmetros...")
                anomalias = validar_parametros(dados)

                if time.time() - start_time > 60:
                    raise TimeoutError("Processamento demorou demais – tente um arquivo menor.")

                print("LOG: Gerando relatório...")  # Logging
                status.update(label="Gerando relatório...")
                output_path = os.path.join(tempfile.gettempdir(), "relatorio_anomalias.docx")
                ok, msg = gerar_relatorio(pdf_path, nome_terapeuta, registro_terapeuta, output_path)
                if not ok:
                    raise ValueError(f"Erro ao gerar relatório: {msg}")

                status.update(label="Finalizado!", state="complete")
                print("LOG: Processamento concluído com sucesso.")  # Logging

                if not anomalias:
                    st.success("🎉 Todos os parâmetros estão dentro do intervalo normal.")
                else:
                    st.error(f"⚠️ {len(anomalias)} anomalias encontradas:")
                    for a in anomalias:
                        st.markdown(f"- **{a['item']}**: {a['valor_real']} ({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})")

                    with open(output_path, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar relatório de anomalias (.docx)",
                            data=f.read(),
                            file_name="relatorio_anomalias.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )

            except Exception as e:
                status.update(label=f"Erro: {str(e)}", state="error")
                st.error(f"❌ Erro ao processar: {str(e)}")
                print(f"LOG ERROR: {str(e)}")  # Logging para nuvem
            finally:
                if tmp_input and os.path.exists(tmp_input.name):
                    os.unlink(tmp_input.name)
                if pdf_path and os.path.exists(pdf_path) and pdf_path != (tmp_input.name if tmp_input else ''):
                    os.unlink(pdf_path)