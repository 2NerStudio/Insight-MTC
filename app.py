import streamlit as st
import tempfile, os
from validacao_parametros import gerar_relatorio_pdf_regex

# — Login simples —
usuarios = {"yan":"1234","cliente1":"senha123","Dolorice20":"Rebeca10"}
if "auth" not in st.session_state: st.session_state.auth=False

if not st.session_state.auth:
    st.set_page_config(page_title="Login", layout="centered")
    st.title("🔐 Login")
    u=st.text_input("Usuário"); p=st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuarios.get(u)==p:
            st.session_state.auth=True; st.experimental_rerun()
        else:
            st.error("Credenciais inválidas")
    st.stop()

# — App principal —
st.set_page_config(page_title="MTC Insight", layout="centered")
if st.sidebar.button("Sair"):
    st.session_state.auth=False; st.experimental_rerun()

st.title("🌿 MTC Insight Pro")
st.caption("Extração por Regex e Validação de Intervalos")

# dados do terapeuta
nome = st.text_input("Nome do Terapeuta")
reg  = st.text_input("Registro Profissional")

# upload
arquivo = st.file_uploader("Envie o relatório (.pdf)", type="pdf")

if st.button("⚙️ Validar (Regex)"):
    if not nome or not reg:
        st.warning("Preencha nome e registro")
    elif not arquivo:
        st.warning("Envie o PDF")
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(arquivo.read()); tmp.close()

        out = gerar_relatorio_pdf_regex(tmp.name, nome, reg,
               os.path.join(tempfile.gettempdir(),"relatorio_regex.docx"))

        st.success("✅ Relatório gerado!")
        with open(out,"rb") as f:
            st.download_button("⬇️ Baixar .docx", f.read(),
                file_name="relatorio_regex.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        os.unlink(tmp.name)
