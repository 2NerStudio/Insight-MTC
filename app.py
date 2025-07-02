import streamlit as st
from utils import transformar_relatorio, exportar_para_docx

# ========================================
# LOGIN SIMPLES COM RERUN CONTROLADO
# ========================================

usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10"
}

# Controle de sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "login_ok" not in st.session_state:
    st.session_state.login_ok = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.title("🔐 Área de Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    login_botao = st.button("Entrar")

    if login_botao:
        if usuario in usuarios_autorizados and senha == usuarios_autorizados[usuario]:
            st.session_state.autenticado = True
            st.rerun()  # forma nova, substitui experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")


# ========================================
# APP PRINCIPAL (APÓS LOGIN)
# ========================================
elif st.session_state.autenticado:
    st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")

    # Logout
    st.sidebar.success("🔓 Autenticado")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    # Logo (opcional)
    try:
        st.image("assets/logo.png", width=200)
    except:
        pass

    st.title("🌿 MTC Insight Pro")
    st.caption("Transforme relatórios técnicos em análises energéticas com base na Medicina Tradicional Chinesa")

    # Terapeuta
    st.subheader("🧑‍⚕️ Informações do Terapeuta")
    nome_terapeuta = st.text_input("Nome completo do terapeuta")
    registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

    # Upload
    st.subheader("📎 Upload do Relatório Original")
    arquivo = st.file_uploader("Envie o relatório (.pdf, .txt ou .docx)", type=["pdf", "txt", "docx"])

    if st.button("⚙️ Transformar Relatório"):
        if not nome_terapeuta or not registro_terapeuta:
            st.warning("⚠️ Preencha os dados do terapeuta.")
        elif not arquivo:
            st.warning("⚠️ Envie o relatório original.")
        else:
            with st.spinner("Processando..."):
                texto_transformado = transformar_relatorio(arquivo, nome_terapeuta, registro_terapeuta)

            st.success("✅ Relatório gerado com sucesso!")
            buffer_docx = exportar_para_docx(texto_transformado)

            st.download_button("⬇️ Baixar relatório (.docx)",
                               data=buffer_docx,
                               file_name="relatorio_mtc.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
