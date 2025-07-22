import streamlit as st
import tempfile, os
from validacao_parametros import gerar_relatorio_por_intervalo

# ——— Login simples ———
usuarios_autorizados = {"yan":"1234", "cliente1":"senha123","Dolorice20":"Rebeca10"}
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login", layout="centered")
    st.title("🔐 Login")
    u = st.text_input("Usuário"); s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuarios_autorizados.get(u)==s:
            st.session_state.autenticado = True; st.experimental_rerun()
        else: st.error("Usuário ou senha inválidos.")
    st.stop()

# ——— App principal ———
st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False; st.experimental_rerun()

st.title("🌿 MTC Insight Pro")
st.caption("Validação por Intervalo de Parâmetros")

# Terapeuta
st.subheader("🧑‍⚕️ Terapeuta")
nome = st.text_input("Nome completo"); reg = st.text_input("Registro")

# Upload
st.subheader("📎 Envie o PDF")
arquivo = st.file_uploader("", type=["pdf"])

if st.button("⚙️ Validar por Intervalo"):
    if not nome or not reg:
        st.warning("Preencha terapeuta e registro.")
    elif not arquivo:
        st.warning("Envie o PDF.")
    else:
        with st.spinner("Processando..."):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(arquivo.read()); tmp.close()

            out = gerar_relatorio_por_intervalo(tmp.name, nome, reg,
                output_path=os.path.join(tempfile.gettempdir(),"relatorio_intervalo.docx")
            )

        st.success("✅ Relatório pronto!")
        with open(out,"rb") as f:
            st.download_button("⬇️ Baixar relatório", f.read(),
                file_name="relatorio_intervalo.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        os.unlink(tmp.name)
