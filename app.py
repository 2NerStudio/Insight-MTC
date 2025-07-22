import streamlit as st
import tempfile
import os
from validacao_parametros import extrair_valores_do_pdf, validar_valores, gerar_relatorio

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
        else:
            st.error("❌ Usuário ou senha inválidos.")
    st.stop()

# ========================================
# APP PRINCIPAL
# ========================================
st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")
st.sidebar.success("🔓 Autenticado")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False

st.title("🌿 MTC Insight Pro")
st.caption("Extrai só a 4ª coluna (Valor Real) e valida contra os parâmetros")

# Dados do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Upload do PDF
st.subheader("📎 Upload do Relatório Original (.pdf)")
arquivo = st.file_uploader("Selecione o arquivo", type=["pdf"])

if st.button("⚙️ Validar Parâmetros"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Envie o relatório original.")
    else:
        with st.spinner("🔍 Processando..."):
            # grava o upload em um temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(arquivo.read())
            tmp.close()

            # 1) Extrai só coluna 4
            valores = extrair_valores_do_pdf(tmp.name)
            # 2) Valida
            anomalias = validar_valores(valores)

        if not anomalias:
            st.success("🎉 Todos os parâmetros dentro da normalidade.")
        else:
            st.error(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in anomalias:
                st.markdown(
                    f"- **{a['item']}**: {a['valor_real']}  "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                )

            # 3) Gera e disponibiliza download do .docx
            output_path = os.path.join(tempfile.gettempdir(), "relatorio_anomalias.docx")
            gerar_relatorio(tmp.name, nome_terapeuta, registro_terapeuta, output_path)

            with open(output_path, "rb") as f:
                st.download_button(
                    "⬇️ Baixar relatório de anomalias (.docx)",
                    data=f.read(),
                    file_name="relatorio_anomalias.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        # remove temp file
        os.unlink(tmp.name)
