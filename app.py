import streamlit as st
import tempfile
import os
from validacao_parametros import gerar_relatorio

# ——— Login simples ———
USUARIOS = {"yan": "1234", "cliente1": "senha123", "Dolorice20": "Rebeca10"}
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.title("🔐 Área de Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if USUARIOS.get(usuario) == senha:
            st.session_state.autenticado = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")
    st.stop()

# ——— App principal ———
st.set_page_config(page_title="MTC Insight Pro", layout="centered", page_icon="🌿")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.experimental_rerun()

st.title("🌿 MTC Insight Pro")
st.caption("Extração por Regex e Validação de Anomalias")

# Informações do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("Registro profissional (CRF/CRTH)")

# Upload do PDF
st.subheader("📎 Upload do Relatório Original")
arquivo = st.file_uploader("Envie o arquivo .pdf", type="pdf")

# Botão de geração
if st.button("⚙️ Gerar Relatório de Anomalias"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha as informações do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Faça upload do relatório original.")
    else:
        with st.spinner("🔍 Processando..."):
            # Salva temporariamente
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(arquivo.read())
            tmp.close()

            # Gera o relatório usando o script regex
            output_path = os.path.join(tempfile.gettempdir(), "relatorio_anomalias.docx")
            gerar_relatorio(tmp.name, nome_terapeuta, registro_terapeuta, output_path)

        st.success("✅ Relatório gerado com sucesso!")
        with open(output_path, "rb") as f:
            st.download_button(
                "⬇️ Baixar Relatório (.docx)",
                data=f.read(),
                file_name="relatorio_anomalias.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # Limpa o arquivo temporário
        os.unlink(tmp.name)
