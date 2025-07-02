import streamlit as st

# Usuários permitidos
usuarios_autorizados = {
    "yan": "1234",
    "maria": "senha123"
}

# Sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Área de Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in usuarios_autorizados and senha == usuarios_autorizados[usuario]:
            st.session_state.autenticado = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")
else:
    st.sidebar.success("✅ Autenticado")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.experimental_rerun()

    st.title("🌿 MTC Insight Pro")
    st.write("Bem-vindo ao sistema.")
