import streamlit as st
from utils import transformar_relatorio, exportar_para_docx

st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")

# Logo (se existir)
try:
    st.image("assets/logo.png", width=200)
except:
    pass

st.title("🌿 MTC Insight Pro")
st.caption("Transforme relatórios técnicos em análises energéticas pela Medicina Tradicional Chinesa")

# Dados do terapeuta
st.subheader("🧑‍⚕️ Dados do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("Número do CRF / CRTH / registro profissional")

# Upload do relatório
st.subheader("📄 Upload do relatório")
arquivo = st.file_uploader("Envie o relatório original (.pdf, .txt ou .docx)", type=["pdf", "txt", "docx"])

# Botão de processamento
if st.button("⚙️ Transformar Relatório"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("Por favor, preencha o nome do terapeuta e o número de registro.")
    elif not arquivo:
        st.warning("Por favor, envie um relatório original.")
    else:
        with st.spinner("Analisando e traduzindo..."):
            texto_transformado = transformar_relatorio(arquivo, nome_terapeuta, registro_terapeuta)

        st.success("✅ Relatório modificado com sucesso!")
        buffer_docx = exportar_para_docx(texto_transformado)

        st.download_button("⬇️ Baixar novo relatório (.docx)",
                           data=buffer_docx,
                           file_name="relatorio_mtc.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
