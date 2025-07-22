import streamlit as st
from extrair_dados import extrair_valores_apenas
from validacao_parametros import validar_valores, gerar_relatorio_anomalias  # importamos a geração de docx
from utils import exportar_para_docx

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

# Cabeçalho
st.title("🌿 MTC Insight Pro")
st.caption("Extração e validação de parâmetros fora da normalidade")

# Dados do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
nome_terapeuta = st.text_input("Nome completo do terapeuta")
registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Upload do PDF
st.subheader("📎 Upload do Relatório Original")
arquivo = st.file_uploader("Envie o relatório (.pdf)", type=["pdf"])

# Botão de validação
if st.button("⚙️ Validar Parâmetros"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta.")
    elif not arquivo:
        st.warning("⚠️ Envie o relatório original.")
    else:
        with st.spinner("🔍 Extraindo e validando..."):
            # 1) extrai apenas os valores
            valores = extrair_valores_apenas(arquivo)
            # 2) filtra os itens fora do normal
            anomalias = validar_valores(valores)

        if not anomalias:
            st.success("🎉 Todos os parâmetros estão dentro do intervalo normal.")
        else:
            st.error(f"⚠️ Encontradas {len(anomalias)} anomalias:")
            for a in anomalias:
                st.markdown(
                    f"- **{a['item']}**: {a['valor_real']}  "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                )

            # 3) gerar o .docx com anomalias e oferecer download
            texto = f"Relatório de Anomalias\nTerapeuta: {nome_terapeuta} | Registro: {registro_terapeuta}\n\n"
            for a in anomalias:
                texto += (
                    f"• {a['item']}: {a['valor_real']} "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})\n"
                )
            buffer = exportar_para_docx(texto)
            st.download_button(
                "⬇️ Baixar relatório de anomalias (.docx)",
                data=buffer,
                file_name="relatorio_anomalias.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
