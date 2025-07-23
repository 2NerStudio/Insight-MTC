import streamlit as st
import tempfile
import os
import subprocess
from validacao_parametros import extrair_parametros_do_pdf, extrair_valores_do_pdf, validar_valores, gerar_relatorio

# ========================================
# CONFIGURAÇÃO INICIAL E LOGIN
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
    st.stop()

# ========================================
# INTERFACE PRINCIPAL
# ========================================
st.set_page_config(page_title="MTC Insight", layout="centered", page_icon="🌿")
st.sidebar.success("🔓 Autenticado")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.experimental_rerun()

st.title("🌿 MTC Insight Pro")
st.caption("Sistema avançado de análise de relatórios de saúde")

# Seção de informações do terapeuta
st.subheader("🧑‍⚕️ Informações do Terapeuta")
with st.expander("Preencha seus dados profissionais", expanded=True):
    nome_terapeuta = st.text_input("Nome completo do terapeuta")
    registro_terapeuta = st.text_input("CRF / CRTH / Registro profissional")

# Seção de upload do arquivo
st.subheader("📎 Upload do Relatório")
arquivo = st.file_uploader(
    "Selecione o arquivo do relatório (PDF ou DOCX)",
    type=["pdf", "docx"],
    help="Arquivos DOCX serão convertidos para PDF automaticamente"
)

# Seção de visualização de parâmetros
if arquivo and st.button("🔍 Visualizar Parâmetros"):
    with st.spinner("Analisando estrutura do arquivo..."):
        try:
            # Processamento temporário do arquivo
            ext = os.path.splitext(arquivo.name)[1].lower()
            tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp_input.write(arquivo.read())
            tmp_input.close()

            # Conversão para PDF se necessário
            if ext == ".docx":
                tmp_pdf = tmp_input.name.replace(".docx", ".pdf")
                subprocess.run([
                    "libreoffice", "--headless", "--convert-to", "pdf", tmp_input.name,
                    "--outdir", os.path.dirname(tmp_input.name)
                ], check=True)
                pdf_path = tmp_pdf
            else:
                pdf_path = tmp_input.name

            # Extrai parâmetros para visualização
            parametros = extrair_parametros_do_pdf(pdf_path)
            
            if parametros:
                st.success(f"✅ {len(parametros)} parâmetros identificados no relatório")
                st.dataframe(
                    data=[{"Parâmetro": k, "Mínimo": v[0], "Máximo": v[1]} for k, v in parametros.items()],
                    height=300,
                    use_container_width=True
                )
            else:
                st.warning("⚠️ Não foram encontrados parâmetros no formato esperado")

            # Limpeza
            os.unlink(tmp_input.name)
            if ext == ".docx" and os.path.exists(pdf_path):
                os.unlink(pdf_path)

        except Exception as e:
            st.error(f"Erro ao analisar arquivo: {str(e)}")

# Seção de validação principal
if st.button("⚙️ Validar Parâmetros", type="primary"):
    if not nome_terapeuta or not registro_terapeuta:
        st.warning("⚠️ Preencha os dados do terapeuta antes de validar.")
    elif not arquivo:
        st.warning("⚠️ Nenhum arquivo foi carregado.")
    else:
        with st.spinner("Processando relatório..."):
            try:
                # 1) Salva upload em arquivo temporário
                ext = os.path.splitext(arquivo.name)[1].lower()
                tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_input.write(arquivo.read())
                tmp_input.close()

                # 2) Conversão para PDF se necessário
                if ext == ".docx":
                    tmp_pdf = tmp_input.name.replace(".docx", ".pdf")
                    subprocess.run([
                        "libreoffice", "--headless", "--convert-to", "pdf", tmp_input.name,
                        "--outdir", os.path.dirname(tmp_input.name)
                    ], check=True)
                    pdf_path = tmp_pdf
                else:
                    pdf_path = tmp_input.name

                # 3) Processamento completo
                parametros = extrair_parametros_do_pdf(pdf_path)
                valores = extrair_valores_do_pdf(pdf_path)
                
                if not parametros or not valores:
                    st.error("❌ Não foi possível extrair dados do relatório. Verifique o formato.")
                    st.stop()
                
                # 4) Validação e exibição de resultados
                anomalias = validar_valores(parametros, valores)
                
                # Resultado da análise
                st.subheader("📊 Resultados da Análise")
                st.metric("Total de Parâmetros Analisados", len(parametros))
                
                if not anomalias:
                    st.success("🎉 Todos os parâmetros estão dentro dos intervalos normais!")
                else:
                    st.error(f"⚠️ {len(anomalias)} parâmetros fora do intervalo normal")
                    
                    # Tabela de anomalias
                    st.dataframe(
                        data=[{
                            "Parâmetro": a['item'],
                            "Valor": f"{a['valor_real']:.3f}",
                            "Status": a['status'],
                            "Intervalo Normal": f"{a['normal_min']} - {a['normal_max']}"
                        } for a in anomalias],
                        height=min(400, len(anomalias)*35),
                        use_container_width=True
                    )

                    # 5) Geração do relatório DOCX
                    output_path = os.path.join(tempfile.gettempdir(), "relatorio_anomalias.docx")
                    sucesso, _ = gerar_relatorio(pdf_path, nome_terapeuta, registro_terapeuta, output_path)
                    
                    if sucesso:
                        with open(output_path, "rb") as f:
                            st.download_button(
                                "⬇️ Baixar Relatório Completo (.docx)",
                                data=f.read(),
                                file_name=f"Relatorio_Anomalias_{nome_terapeuta.split()[0]}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                help="Relatório detalhado com todas as anomalias encontradas"
                            )
                    else:
                        st.warning("Não foi possível gerar o relatório completo em DOCX.")

            except subprocess.CalledProcessError:
                st.error("❌ Erro na conversão do documento. Verifique se o LibreOffice está instalado.")
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")
            finally:
                # Limpeza dos arquivos temporários
                if os.path.exists(tmp_input.name):
                    os.unlink(tmp_input.name)
                if ext == ".docx" and os.path.exists(pdf_path):
                    os.unlink(pdf_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

# Rodapé
st.markdown("---")
st.caption("MTC Insight Pro v2.0 - Sistema de análise de relatórios de saúde")