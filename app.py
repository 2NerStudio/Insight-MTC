import streamlit as st
import tempfile
import os
import subprocess
from typing import Optional
from validacao import extract_parameters_from_pdf, validate_parameters, generate_report

# CSS (inalterado)
st.markdown("""
<style>
.stApp { background-color: #f0f7f4; color: #2e7d32; }
.stButton > button { background-color: #4caf50; color: white; border-radius: 8px; padding: 0.5em 1em; }
.stButton > button:hover { background-color: #388e3c; }
.stTextInput > div > input { border: 1px solid #81c784; border-radius: 4px; }
h1, h2, h3 { color: #1b5e20; }
.header-icon { font-size: 3em; text-align: center; margin-bottom: 0.5em; }
</style>
""", unsafe_allow_html=True)

# Usuários (inalterado)
AUTHORIZED_USERS = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10",
}

# Estado de sessão
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Tela de Login (inalterado)
if not st.session_state.authenticated:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.markdown('<div class="header-icon">🔐</div>', unsafe_allow_html=True)
    st.title("Login - MTC Insight")
    st.caption("Acesse a ferramenta de validação de relatórios")

    with st.form(key="login_form"):
        username = st.text_input("Usuário", placeholder="Digite seu usuário")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        if st.form_submit_button("Entrar"):
            if AUTHORIZED_USERS.get(username) == password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Usuário ou senha inválidos.")
    st.stop()

# App Principal
st.set_page_config(page_title="MTC Insight Pro", layout="wide", page_icon="🌿")

# Sidebar (inalterado)
with st.sidebar:
    st.success("🔓 Autenticado com sucesso!")
    st.markdown("### Menu")
    if st.button("🚪 Sair"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    with st.expander("ℹ️ Instruções"):
        st.markdown("""
        - Preencha dados do terapeuta.
        - Faça upload de PDF ou DOCX.
        - Clique em Validar.
        """)

# Header (inalterado)
st.markdown('<div class="header-icon">🌿</div>', unsafe_allow_html=True)
st.title("MTC Insight Pro")
st.caption("Valide relatórios médicos rapidamente. Suporta PDF e DOCX.")

st.divider()

# Informações do Terapeuta (inalterado)
st.subheader("🧑‍⚕️ Dados do Terapeuta")
col1, col2 = st.columns(2)
therapist_name = col1.text_input("Nome do Terapeuta", placeholder="Ex: Dr. João Silva")
therapist_registry = col2.text_input("Registro Profissional", placeholder="Ex: CRF-12345")

st.divider()

# Upload e Validação
st.subheader("📎 Upload do Relatório")
with st.form(key="upload_form"):
    uploaded_file = st.file_uploader("Selecione PDF ou DOCX", type=["pdf", "docx"])
    submit = st.form_submit_button("⚙️ Validar")

if submit:
    if not therapist_name or not therapist_registry:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not uploaded_file:
        st.warning("⚠️ Selecione um arquivo.")
    else:
        with st.spinner("🔍 Processando..."):
            try:
                # Salva arquivo temporário
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(uploaded_file.read())
                    input_path = tmp.name

                # Converte DOCX para PDF se necessário
                pdf_path = input_path
                if ext == ".docx":
                    pdf_path = os.path.join(tempfile.gettempdir(), "converted.pdf")
                    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", input_path, "--outdir", tempfile.gettempdir()], check=True)

                # Extrai e valida
                parameters = extract_parameters_from_pdf(pdf_path)

                # Debug: Mostra parâmetros extraídos
                with st.expander("🛠 Debug: Parâmetros Extraídos (para verificação)"):
                    if parameters:
                        st.info(f"📊 {len(parameters)} parâmetros únicos extraídos.")
                        for name in sorted(parameters.keys()):
                            data = parameters[name]
                            st.markdown(f"- **{name}**: Valor {data['valor']:.3f} (Range: {data['min']}–{data['max']})")
                    else:
                        st.warning("Nenhum parâmetro extraído. Verifique o PDF.")

                anomalies = validate_parameters(parameters)

                # Feedback
                if not anomalies:
                    st.success("🎉 Todos os parâmetros normais!")
                else:
                    st.error(f"⚠️ {len(anomalies)} anomalias:")
                    for a in anomalies:
                        st.markdown(f"- **{a['item']}**: {a['valor_real']:.3f} ({a['status']}; Normal: {a['normal_min']}–{a['normal_max']})")

                    # Gera e oferece download
                    output_path = os.path.join(tempfile.gettempdir(), "relatorio_anomalias.docx")
                    generate_report(anomalies, therapist_name, therapist_registry, output_path)
                    with open(output_path, "rb") as f:
                        st.download_button("⬇️ Baixar Relatório", f.read(), file_name="relatorio_anomalias.docx")
            except Exception as e:
                st.error(f"Erro: {str(e)}")
            finally:
                # Limpeza
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if ext == ".docx" and os.path.exists(pdf_path):
                    os.unlink(pdf_path)