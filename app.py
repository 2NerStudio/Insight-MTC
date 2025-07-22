import streamlit as st
from extrair_dados import extrair_valores_apenas
from utils import transformar_relatorio, exportar_para_docx

# ========================================
# LOGIN SIMPLES
# ========================================

usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10"
}

# Controle de sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.title("🔐 Área de Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    login_botao = st.button("Entrar")

    if login_botao:
        if usuario in usuarios_autorizados and senha == usuarios_autorizados[usuario]:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")

# ========================================
# APP PRINCIPAL
# ========================================
elif st.session_state.autenticado:
    st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")

    # Sidebar
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
    st.caption("Transforme relatórios técnicos em dados extraídos automaticamente.")

    # Terapeuta
    st.subheader("🧑‍⚕️ Informações do Terapeuta")
    nome_terapeuta = st.text_input("Nome completo do terapeuta")
    registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

    # Upload
    st.subheader("📎 Upload do Relatório Original")
    arquivo = st.file_uploader("Envie o relatório (.pdf)", type=["pdf"])

    if st.button("⚙️ Extrair Valores"):
        if not nome_terapeuta or not registro_terapeuta:
            st.warning("⚠️ Preencha os dados do terapeuta.")
        elif not arquivo:
            st.warning("⚠️ Envie o relatório original.")
        else:
            with st.spinner("🔍 Extraindo dados..."):
                valores = extrair_valores_apenas(arquivo)

            st.success("✅ Valores extraídos com sucesso!")
            st.write("📊 Valores extraídos do relatório:")
            st.json(valores)

            # Aqui você pode montar o texto final, se quiser:
            texto = f"Relatório - Terapeuta: {nome_terapeuta} (Registro: {registro_terapeuta})\n\n"
            for item, valor in valores.items():
                texto += f"{item}: {valor or '—'}\n"

            st.download_button("⬇️ Baixar como .docx",
                               data=exportar_para_docx(texto),
                               file_name="relatorio_valores.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
