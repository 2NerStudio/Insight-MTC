import streamlit as st
from extrair_dados import extrair_dados_do_pdf
from utils import transformar_relatorio, exportar_para_docx

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
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")
    st.stop()  # garante que não executa o restante

# ========================================
# APP PRINCIPAL (APÓS LOGIN)
# ========================================
st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")

# Logout
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
st.caption("Transforme relatórios técnicos em análises energéticas pela Medicina Tradicional Chinesa")

# Dados do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Upload do relatório
st.subheader("📎 Upload do Relatório Original")
arquivo = st.file_uploader("Envie o relatório (.pdf, .txt ou .docx)", type=["pdf", "txt", "docx"])

# Botão de transformação
if st.button("⚙️ Transformar Relatório"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Envie o relatório original.")
    else:
        with st.spinner("Processando..."):
            # Se for PDF, extrai a tabela estruturada
            if arquivo.name.lower().endswith(".pdf"):
                dados = extrair_dados_do_pdf(arquivo)

                st.write("🧪 Dados extraídos do PDF:")
                st.write(dados)  # debug

                texto_final = ""
                for d in dados:
                    texto_final += f"**{d['sistema']}** – {d['item']}\n"
                    texto_final += f"Valor: {d['valor']} (Normal: {d['intervalo']})\n"
                    texto_final += f"Conselho: {d['conselho']}\n\n"
                texto_final += f"---\nRelatório elaborado por {nome_terapeuta} — Registro: {registro_terapeuta}"
                texto_transformado = texto_final

            else:
                # TXT ou DOCX simples
                texto_transformado = transformar_relatorio(arquivo, nome_terapeuta, registro_terapeuta)

        st.success("✅ Relatório gerado com sucesso!")
        buffer_docx = exportar_para_docx(texto_transformado)

        st.download_button(
            "⬇️ Baixar relatório (.docx)",
            data=buffer_docx,
            file_name="relatorio_mtc.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
