import streamlit as st
import tempfile
import os
import pdfplumber

from analisador_exames import (
    extract_patient_info,
    extract_exam_data,
    analyze_results,
    create_report
)

# ========== LOGIN SIMPLES ==========
usuarios_autorizados = {
    "yan": "1234",
    "cliente1": "senha123",
    "Dolorice20": "Rebeca10"
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.set_page_config(page_title="Login - Analisador MTC", layout="centered")
    st.title("🔐 Área de Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuarios_autorizados.get(usuario) == senha:
            st.session_state.autenticado = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")
    st.stop()

# ========== APP PRINCIPAL ==========
st.set_page_config(page_title="Analisador de Exames MTC", layout="wide", page_icon="🌿")
st.sidebar.success("🔓 Autenticado")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.experimental_rerun()

st.title("🌿 Analisador de Exames MTC")
st.caption("Extração, análise e relatório automático de exames em .pdf")

# Upload do PDF
st.subheader("📎 Upload do Relatório Original (.pdf)")
uploaded = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])
if not uploaded:
    st.info("Envie um PDF para começar.")
    st.stop()

# Processar
if st.button("⚙️ Processar Exame"):
    with st.spinner("🔍 Extraindo texto e analisando..."):
        # Grava temporariamente
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(uploaded.read())
        tmp.flush()

        # Extrai texto completo
        with pdfplumber.open(tmp.name) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Extrai dados de paciente e exame
        paciente = extract_patient_info(full_text)
        exame = extract_exam_data(full_text)
        exame["paciente"] = paciente

        # Analisa resultados
        analysis = analyze_results(exame)

    # Exibição do resumo
    st.markdown("## 📝 Resumo")
    st.write(f"- **Paciente:** {paciente['nome']}  |  **Sexo:** {paciente['sexo']}  |  **Idade:** {paciente['idade']}")
    st.write(f"- **Data do Exame:** {paciente['data_exame']}")
    st.write(f"- **Total de parâmetros analisados:** {analysis['total_parametros']}")
    st.write(f"- **Anomalias detectadas:** {analysis['total_anomalias']}")

    # Tabela de anomalias
    if analysis["anomalias"]:
        st.markdown("### ⚠️ Parâmetros com Anomalias")
        st.table([
            {
                "Parâmetro": a["parametro"],
                "Valor": f"{a['valor']:.3f}",
                "Normal": a["intervalo"],
                "Status": a["status"],
                "Recomendações": a["conselho"]
            }
            for a in analysis["anomalias"]
        ])
    else:
        st.success("🎉 Nenhuma anomalia encontrada.")

    # Gera e oferece download do relatório .docx
    report_name = f"Relatorio_{paciente['nome'].replace(' ', '_')}.docx"
    report_path = create_report(exame, analysis, report_name)

    with open(report_path, "rb") as f:
        st.download_button(
            "⬇️ Baixar relatório completo (.docx)",
            data=f.read(),
            file_name=report_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # Limpeza
    tmp.close()
    os.unlink(tmp.name)
