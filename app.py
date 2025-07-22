import streamlit as st
import tempfile
import os
from validacao_parametros import extrair_por_intervalo, gerar_relatorio_por_intervalo

# ========================================
# LOGIN SIMPLES
# ========================================
usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10"
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

st.title("🌿 MTC Insight Pro")
st.caption("Extrai só a 4ª coluna (Valor Real) e valida contra os parâmetros")

# Dados do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Upload do PDF
st.subheader("📎 Upload do Relatório Original (.pdf)")
arquivo = st.file_uploader("Selecione o arquivo", type=["pdf"])

if st.button("⚙️ Validar Parâmetros (por intervalo)"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Envie o relatório original.")
    else:
        with st.spinner("🔍 Extraindo por intervalo..."):
            # salva temporário
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(arquivo.read())
            tmp.close()

            # extrai e gera docx
            rel_path = gerar_relatorio_por_intervalo(
                tmp.name, nome_terapeuta, registro_terapeuta,
                output=os.path.join(tempfile.gettempdir(), "relatorio_intervalo.docx")
            )

        st.success("✅ Relatório gerado com base em intervalos!")
        with open(rel_path, "rb") as f:
            st.download_button(
                "⬇️ Baixar relatório",
                data=f.read(),
                file_name="relatorio_intervalo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        os.unlink(tmp.name)
