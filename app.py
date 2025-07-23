import streamlit as st
import tempfile
import os
import subprocess
from validacao_parametros import extrair_dados_pdf, gerar_relatorio_anomalias, analyze_results


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
            dados = extrair_dados_pdf(pdf_path)
            parametros = dados['parametros']
            
            if parametros:
                st.success(f"✅ {len(parametros)} parâmetros identificados no relatório")
                
                # Mostra os primeiros 10 parâmetros como amostra
                sample_params = [{
                    "Sistema/Item": k.split(" | ")[0],
                    "Parâmetro": k.split(" | ")[1] if " | " in k else k,
                    "Mínimo": v[0],
                    "Máximo": v[1]
                } for k, v in list(parametros.items())[:10]]
                
                st.dataframe(
                    data=sample_params,
                    height=300,
                    use_container_width=True,
                    column_config={
                        "Sistema/Item": st.column_config.TextColumn(width="medium"),
                        "Parâmetro": st.column_config.TextColumn(width="large")
                    }
                )
                
                if len(parametros) > 10:
                    st.info(f"Mostrando 10 de {len(parametros)} parâmetros. Todos serão incluídos na análise completa.")
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
                dados = extrair_dados_pdf(pdf_path)
                
                if not dados['parametros'] or not dados['valores']:
                    st.error("❌ Não foi possível extrair dados do relatório. Verifique o formato.")
                    st.stop()
                
                # Adiciona informações do terapeuta aos dados
                dados['terapeuta'] = {
                    'nome': nome_terapeuta,
                    'registro': registro_terapeuta
                }
                
                # 4) Análise completa
                analise = analyze_results(dados)
                
                # Resultado da análise
                st.subheader("📊 Resultados da Análise")
                
                # Métricas principais
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Parâmetros", analise['total_parametros'])
                col2.metric("Dentro do Normal", len(analise['normais']))
                col3.metric("Anomalias", analise['total_anomalias'], 
                           delta=f"{analise['total_anomalias']/analise['total_parametros']:.1%}")
                
                if not analise['anomalias']:
                    st.success("🎉 Todos os parâmetros estão dentro dos intervalos normais!")
                else:
                    # Tabela de anomalias com recomendações
                    st.error(f"⚠️ {len(analise['anomalias'])} parâmetros fora do intervalo normal")
                    
                    # Agrupa por sistema para melhor organização
                    sistemas = {}
                    for anomalia in analise['anomalias']:
                        sistema = anomalia['parametro'].split(" | ")[0]
                        if sistema not in sistemas:
                            sistemas[sistema] = []
                        sistemas[sistema].append(anomalia)
                    
                    for sistema, itens in sistemas.items():
                        with st.expander(f"🔴 {sistema} ({len(itens)} anomalias)", expanded=True):
                            for item in itens:
                                st.markdown(f"**{item['parametro'].split(' | ')[1]}**")
                                cols = st.columns([1,1,1,2])
                                cols[0].metric("Valor", f"{item['valor']:.3f}")
                                cols[1].metric("Intervalo", item['intervalo'])
                                cols[2].metric("Status", item['status'])
                                if item['conselho']:
                                    cols[3].info("💡 Recomendação: " + item['conselho'])
                                st.divider()

                    # 5) Geração do relatório DOCX
                    with st.spinner("Gerando relatório completo..."):
                        report_name = f"Relatorio_{dados['paciente']['nome'].replace(' ', '_')}.docx"
                        report_path = gerar_relatorio_anomalias(dados, report_name)
                        
                        with open(report_path, "rb") as f:
                            st.download_button(
                                "⬇️ Baixar Relatório Completo (.docx)",
                                data=f.read(),
                                file_name=report_name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                help="Relatório completo com todos os parâmetros e recomendações"
                            )

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
                if 'report_path' in locals() and os.path.exists(report_path):
                    os.unlink(report_path)

# Rodapé
st.markdown("---")
st.caption("MTC Insight Pro v3.0 - Sistema de análise de relatórios de saúde")