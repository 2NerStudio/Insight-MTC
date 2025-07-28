import streamlit as st
import tempfile
import os
import subprocess

# Novo import (assumindo que você tem esse módulo)
from validacao_dinamica import (
    extrair_parametros_valores,
    validar_parametros,
    gerar_relatorio,
)

# CSS personalizado para estética
st.markdown("""
    <style>
    /* Tema geral: Verde suave para MTC Insight */
    .stApp {
        background-color: #f0f7f4; /* Fundo claro verde-água */
        color: #2e7d32; /* Verde escuro para texto */
    }
    .stButton > button {
        background-color: #4caf50; /* Verde botão */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5em 1em;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #388e3c; /* Hover mais escuro */
    }
    .stTextInput > div > input {
        border: 1px solid #81c784; /* Borda verde clara */
        border-radius: 4px;
    }
    .stAlert {
        border-radius: 8px;
        padding: 1em;
    }
    h1, h2, h3 {
        color: #1b5e20; /* Verde título */
    }
    /* Ícone no header */
    .header-icon {
        font-size: 3em;
        text-align: center;
        margin-bottom: 0.5em;
    }
    </style>
""", unsafe_allow_html=True)

# ╔════════ LOGIN SIMPLES ════════╗
usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10",
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - MTC Insight", layout="centered")
    st.markdown('<div class="header-icon">🔐</div>', unsafe_allow_html=True)
    st.title("Área de Login - MTC Insight")
    st.caption("Acesse sua ferramenta de validação de relatórios")
    
    with st.form(key="login_form"):
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", help="Seu nome de usuário cadastrado")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", help="Mantenha segura!")
        submit = st.form_submit_button("Entrar", help="Clique para autenticar")
        if submit:
            if usuarios_autorizados.get(usuario) == senha:
                st.session_state.autenticado = True
                st.experimental_rerun()
            else:
                st.error("❌ Usuário ou senha inválidos.")
    st.stop()
# ╚═══════════════════════════════╝

# ╔════════ APP PRINCIPAL ════════╗
st.set_page_config(page_title="MTC Insight", layout="wide", page_icon="🌿")

# Sidebar melhorada
with st.sidebar:
    st.success("🔓 Autenticado com sucesso!")
    st.markdown("### Menu")
    st.caption("Bem-vindo ao MTC Insight Pro")
    if st.button("🚪 Sair", help="Clique para logout"):
        st.session_state.autenticado = False
        st.experimental_rerun()
    st.divider()
    with st.expander("ℹ️ Instruções Rápidas"):
        st.markdown("""
        - Preencha seus dados.
        - Faça upload de PDF ou DOCX.
        - Clique em Validar para análise.
        """)

# Header principal
st.markdown('<div class="header-icon">🌿</div>', unsafe_allow_html=True)
st.title("MTC Insight Pro")
st.caption("Valide parâmetros de relatórios médicos de forma rápida e segura. Suporta PDF e DOCX.")

st.divider()

# Seção de Informações do Terapeuta (em colunas para melhor layout)
st.subheader("🧑‍⚕️ Informações do Terapeuta")
col1, col2 = st.columns(2)
with col1:
    nome_terapeuta = st.text_input("Nome completo do terapeuta", placeholder="Ex: Dr. João Silva", help="Seu nome completo")
with col2:
    registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional", placeholder="Ex: CRF-12345", help="Número de registro profissional")

st.divider()

# Seção de Upload e Validação (em form para submissão única)
st.subheader("📎 Upload do Relatório (.pdf ou .docx)")
with st.form(key="upload_form"):
    arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "docx"], help="Arraste ou clique para selecionar")
    submit_validar = st.form_submit_button("⚙️ Validar Parâmetros", help="Inicie a validação")

if submit_validar:
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta antes de prosseguir.")
    elif not arquivo:
        st.warning("⚠️ Envie um arquivo PDF ou DOCX para análise.")
    else:
        with st.spinner("🔍 Processando o relatório..."):
            try:
                # 1) Salvar upload
                ext = os.path.splitext(arquivo.name)[1].lower()
                tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_input.write(arquivo.read())
                tmp_input.close()

                # 2) Converter DOCX para PDF se necessário
                if ext == ".docx":
                    tmp_pdf = tmp_input.name.replace(".docx", ".pdf")
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
                    )
                    pdf_path = tmp_pdf
                else:
                    pdf_path = tmp_input.name

                # 3) Extrair e validar
                dados = extrair_parametros_valores(pdf_path)
                anomalias = validar_parametros(dados)

                # 4) Feedback ao usuário
                if not anomalias:
                    st.success("🎉 Todos os parâmetros estão dentro do intervalo normal! Nenhum problema detectado.")
                else:
                    st.error(f"⚠️ {len(anomalias)} anomalias encontradas. Veja os detalhes abaixo:")
                    for a in anomalias:
                        st.markdown(
                            f"- **{a['item']}**: {a['valor_real']}  "
                            f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                        )

                    # 5) Gerar relatório e permitir download
                    output_path = os.path.join(
                        tempfile.gettempdir(), "relatorio_anomalias.docx"
                    )
                    gerar_relatorio(
                        pdf_path, nome_terapeuta, registro_terapeuta, output_path
                    )
                    with open(output_path, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar Relatório de Anomalias (.docx)",
                            data=f.read(),
                            file_name="relatorio_anomalias.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            help="Baixe o relatório gerado para revisão offline"
                        )
            finally:
                # 6) Limpeza de temporários
                os.unlink(tmp_input.name)
                if ext == ".docx" and os.path.exists(pdf_path):
                    os.unlink(pdf_path)
# ╚═══════════════════════════════╝