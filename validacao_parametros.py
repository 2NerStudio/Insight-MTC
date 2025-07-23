import sys
import pdfplumber
import re
from io import BytesIO
from docx import Document

def extrair_parametros_e_valores(caminho_pdf):
    """Extrai parâmetros e valores com estratégias robustas"""
    dados = {'parametros': {}, 'valores': {}}
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            # Primeiro tentamos extrair texto cru para análise
            texto = page.extract_text()
            
            # Padrão para encontrar linhas de resultados (ajuste conforme seu PDF)
            padrao = re.compile(
                r'(?P<nome>.+?)\s+'  # Nome do parâmetro
                r'(?P<valor>\d+[\.,]\d+)\s+'  # Valor medido
                r'(?P<unidade>\w*)\s*'  # Unidade (opcional)
                r'(?P<intervalo>[\d\.,]+\s*[-–]\s*[\d\.,]+)'  # Intervalo de referência
            )
            
            for match in padrao.finditer(texto):
                nome = match.group('nome').strip()
                valor = float(match.group('valor').replace(',', '.'))
                intervalo = match.group('intervalo').replace(',', '.').replace(' ', '')
                
                # Processa intervalo
                minimo, maximo = map(float, re.split(r'[-–]', intervalo))
                
                dados['parametros'][nome] = (minimo, maximo)
                dados['valores'][nome] = valor
            
            # Se não encontrou no texto, tenta tabelas com estratégia mais flexível
            if not dados['parametros']:
                tabelas = page.extract_tables({
                    "vertical_strategy": "text", 
                    "horizontal_strategy": "text"
                })
                
                for tabela in tabelas:
                    for linha in tabela:
                        if len(linha) >= 4:
                            nome = (linha[1] or '').strip()
                            intervalo = (linha[2] or '').replace(',', '.').replace('\n', '').strip()
                            valor = (linha[3] or '').replace(',', '.').strip()
                            
                            if nome and intervalo and valor:
                                # Processa intervalo
                                match = re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', intervalo)
                                if match:
                                    minimo, maximo = map(float, match.groups())
                                    try:
                                        valor_float = float(valor)
                                        dados['parametros'][nome] = (minimo, maximo)
                                        dados['valores'][nome] = valor_float
                                    except ValueError:
                                        continue
    
    return dados

def validar_valores(parametros, valores):
    """Valida os valores medidos contra os intervalos de referência"""
    anomalias = []
    
    for item, valor in valores.items():
        if item in parametros:
            minimo, maximo = parametros[item]
            
            if not (minimo <= valor <= maximo):
                status = "Abaixo" if valor < minimo else "Acima"
                anomalias.append({
                    "item": item,
                    "valor_real": valor,
                    "status": status,
                    "normal_min": minimo,
                    "normal_max": maximo
                })
    
    return anomalias

def exportar_para_docx(texto, output_path):
    """Cria um .docx com o texto dado"""
    doc = Document()
    for line in texto.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        # 1) Extrair dados do PDF
        dados = extrair_parametros_e_valores(pdf_path)
        parametros = dados['parametros']
        valores = dados['valores']
        
        if not parametros:
            raise ValueError("Nenhum parâmetro foi encontrado no PDF.")
        if not valores:
            raise ValueError("Nenhum valor medido foi encontrado no PDF.")
        
        # 2) Validar valores
        anomalias = validar_valores(parametros, valores)
        
        # 3) Montar relatório
        lines = [
            "Relatório de Anomalias - Análise Completa",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            f"Total de parâmetros identificados: {len(parametros)}",
            f"Total de valores analisados: {len(valores)}",
            ""
        ]
        
        if not anomalias:
            lines.append("✅ Todos os parâmetros dentro dos intervalos normais.")
        else:
            lines.append(f"⚠️ ATENÇÃO: {len(anomalias)} anomalias detectadas:")
            for idx, a in enumerate(anomalias, 1):
                lines.append(
                    f"{idx}. {a['item']}: {a['valor_real']:.3f} "
                    f"(Valor {a['status']} do normal: {a['normal_min']}–{a['normal_max']})"
                )
        
        # Adiciona resumo estatístico
        lines.extend([
            "",
            "Resumo Estatístico:",
            f"- Parâmetros dentro do normal: {len(valores)-len(anomalias)}/{len(valores)}",
            f"- Percentual de anomalias: {len(anomalias)/len(valores):.1%}",
            ""
        ])
        
        texto = "\n".join(lines)
        
        # 4) Exportar para DOCX
        exportar_para_docx(texto, output_path)
        print(f"✅ Relatório gerado com sucesso: {output_path}")
        
        return True, output_path
        
    except Exception as e:
        print(f"❌ Falha ao gerar relatório: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso correto: python analise_saude.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    
    sucesso, resultado = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)