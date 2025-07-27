import streamlit as st
import tempfile
import os
import subprocess
try:
    from docx2pdf import convert  # Alternativa para conversão sem LibreOffice (instale com pip install docx2pdf)
except ImportError:
    convert = None  # Se não instalado, usa LibreOffice

# Import do seu script (certifique-se de que validacao_dinamica.py está no mesmo diretório)
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
st.caption("Suporta PDF e DOCX (via LibreOffice ou docx2pdf) e valida parâmetros diretamente do arquivo")

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
        with st.spinner("🔍 Processando..."):
            tmp_input = None
            pdf_path = None
            try:
                # 1) Salva upload em arquivo temporário
                ext = os.path.splitext(arquivo.name)[1].lower()
                tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_input.write(arquivo.read())
                tmp_input.close()

                # 2) Se for DOCX, converte para PDF
                if ext == ".docx":
                    tmp_pdf = tmp_input.name.replace(".docx", ".pdf")
                    if convert:  # Usa docx2pdf se instalado (mais simples para deploy)
                        convert(tmp_input.name, tmp_pdf)
                    else:  # Usa LibreOffice
                        subprocess.run(
                            [
                                "libreoffice",
                                "--headless",
                                "--convert-to",
                                "pdf",
                                tmp_input.name,
                                "--outdir",
                                os.path.dirname(tmp_input.name),
                            ],
                            check=True,
                            capture_output=True,  # Captura output para depuração
                        )
                    pdf_path = tmp_pdf
                    if not os.path.exists(pdf_path):
                        raise FileNotFoundError("Falha na conversão de DOCX para PDF. Verifique se LibreOffice ou docx2pdf está instalado.")
                else:
                    pdf_path = tmp_input.name

                # Depuração: Verifica se PDF existe
                st.write(f"DEBUG: PDF path = {pdf_path} (existe? {os.path.exists(pdf_path)})")

                # 3) Extrai e valida
                dados = extrair_parametros_valores(pdf_path)
                if not dados:
                    raise ValueError("Nenhum parâmetro extraído do PDF. Verifique o arquivo.")
                anomalias = validar_parametros(dados)

                # 4) Exibe resultado
                if not anomalias:
                    st.success("🎉 Todos os parâmetros estão dentro do intervalo normal.")
                else:
                    st.error(f"⚠️ {len(anomalias)} anomalias encontradas:")
                    for a in anomalias:
                        st.markdown(
                            f"- **{a['item']}**: {a['valor_real']}  "
                            f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                        )

                    # 5) Gera e oferece download do .docx final
                    output_path = os.path.join(
                        tempfile.gettempdir(), "relatorio_anomalias.docx"
                    )
                    ok, msg = gerar_relatorio(
                        pdf_path, nome_terapeuta, registro_terapeuta, output_path
                    )
                    if not ok:
                        raise ValueError(f"Erro ao gerar relatório: {msg}")
                    with open(output_path, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar relatório de anomalias (.docx)",
                            data=f.read(),
                            file_name="relatorio_anomalias.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )

            except Exception as e:
                st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
                st.write("DEBUG: Detalhes do erro:", e)  # Para depuração
            finally:
                # 6) Limpeza
                if tmp_input and os.path.exists(tmp_input.name):
                    os.unlink(tmp_input.name)
                if pdf_path and os.path.exists(pdf_path) and pdf_path != tmp_input.name:
                    os.unlink(pdf_path)