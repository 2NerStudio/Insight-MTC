import streamlit as st
from utils import transformar_relatorio, exportar_para_docx

# ========================================
# LOGIN SIMPLES (SEM CRIPTOGRAFIA)
# ========================================

usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "cliente2": "outra"
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.title("🔐 Área de Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in usuarios_autorizados and senha == usuarios_autorizados[usuario]:
            st.session_state.autenticado = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")

# ========================================
# APP PRINCIPAL (SOMENTE SE AUTENTICADO)
# ========================================

elif st.session_state.autenticado:
    st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")

    # Botão de logout
    st.sidebar.success("🔓 Autenticado")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.experimental_rerun()

    # Logo (opcional)
    try:
        st.image("assets/logo.png", width=200)
    except:
        pass

    st.title("🌿 MTC Insight Pro")
    st.caption("Transforme relatórios técnicos em linguagem da Medicina Tradicional Chinesa")

    # Dados do terapeuta
    st.subheader("🧑‍⚕️ Informações do Terapeuta")
    nome_terapeuta = st.text_input("Nome completo")
    registro_terapeuta = st.text_input("CRF / CRTH / Registro")

    # Upload do arquivo
    st.subheader("📎 Upload do Relatório Original")
    arquivo = st.file_uploader("Envie um arquivo .pdf, .txt ou .docx", type=["pdf", "txt", "docx"])

    # Processar e gerar novo relatório
    if st.button("⚙️ Transformar Relatório"):
        if not nome_terapeuta or not registro_terapeuta:
            st.warning("⚠️ Preencha os dados do terapeuta.")
        elif not arquivo:
            st.warning("⚠️ Envie o relatório original.")
        else:
            with st.spinner("Processando e traduzindo o relatório..."):
                texto_transformado = transformar_relatorio(arquivo, nome_terapeuta, registro_terapeuta)

            st.success("✅ Relatório gerado com sucesso!")
            buffer_docx = exportar_para_docx(texto_transformado)

            st.download_button("⬇️ Baixar relatório (.docx)",
                               data=buffer_docx,
                               file_name="relatorio_mtc.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
