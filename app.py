import sys
import pdfplumber
import re
from io import BytesIO
from docx import Document

def extrair_parametros_do_pdf(caminho_pdf):
    """Extrai os parâmetros e seus intervalos de referência com melhor tratamento dos nomes"""
    parametros = {}
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            # Configuração otimizada para tabelas com bordas visíveis
            table_settings = {
                "vertical_strategy": "text",  # Alterado para "text" para melhor captura
                "horizontal_strategy": "text",
                "intersection_y_tolerance": 15
            }
            
            tabelas = page.extract_tables(table_settings)
            
            for tabela in tabelas:
                for linha in tabela:
                    # Verifica se a linha tem pelo menos 4 colunas (nome, item de teste, intervalo, valor)
                    if len(linha) >= 4:
                        # O nome completo do parâmetro pode estar combinado nas colunas 0 e 1
                        nome_parametro = (linha[0] or "") + " " + (linha[1] or "")
                        nome_parametro = nome_parametro.strip()
                        
                        intervalo = linha[2].strip() if len(linha) > 2 and linha[2] else ""
                        
                        if nome_parametro and intervalo:
                            # Limpeza e processamento do intervalo
                            intervalo = (intervalo.replace(",", ".")
                                      .replace("\n", "")
                                      .replace(" ", ""))
                            
                            # Extrai os valores mínimo e máximo usando regex
                            match = re.match(r"([\d.]+)\-([\d.]+)", intervalo)
                            if match:
                                minimo = float(match.group(1))
                                maximo = float(match.group(2))
                                parametros[nome_parametro] = (minimo, maximo)
    
    return parametros

def extrair_valores_do_pdf(caminho_pdf):
    """Extrai os valores medidos com tratamento melhorado dos nomes"""
    valores = {}
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_y_tolerance": 15
            }
            
            tabelas = page.extract_tables(table_settings)
            
            for tabela in tabelas:
                for linha in tabela:
                    if len(linha) >= 4:
                        # Combina as primeiras colunas para obter o nome completo
                        nome_parametro = (linha[0] or "") + " " + (linha[1] or "")
                        nome_parametro = nome_parametro.strip()
                        
                        valor_medido = linha[3].strip() if len(linha) > 3 and linha[3] else ""
                        
                        if nome_parametro and valor_medido:
                            # Limpeza do valor medido
                            valor_medido = (valor_medido.replace(",", ".")
                                          .replace(" ", "")
                                          .replace("\n", "")
                                          .replace("'", ""))
                            
                            if valor_medido.replace(".", "", 1).isdigit():
                                valores[nome_parametro] = float(valor_medido)
    
    return valores

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
        # 1) Extrair parâmetros e seus intervalos
        parametros = extrair_parametros_do_pdf(pdf_path)
        if not parametros:
            raise ValueError("Nenhum parâmetro foi encontrado no PDF. Verifique o formato do arquivo.")
        
        # 2) Extrair valores medidos
        valores = extrair_valores_do_pdf(pdf_path)
        if not valores:
            raise ValueError("Nenhum valor medido foi encontrado no PDF.")
        
        # 3) Validar valores
        anomalias = validar_valores(parametros, valores)
        
        # 4) Montar relatório
        lines = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            f"Total de parâmetros analisados: {len(parametros)}",
            f"Total de valores medidos: {len(valores)}",
            ""
        ]
        
        if not anomalias:
            lines.append("🎉 Todos os parâmetros dentro da normalidade.")
        else:
            lines.append(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in anomalias:
                lines.append(
                    f"• {a['item']}: {a['valor_real']:.3f}  "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                )
        
        # Adiciona lista completa de parâmetros para debug
        lines.extend(["", "Lista completa de parâmetros extraídos:", ""])
        for param, (min_val, max_val) in parametros.items():
            lines.append(f"- {param}: {min_val} - {max_val}")
        
        texto = "\n".join(lines)
        
        # 5) Exportar para DOCX
        exportar_para_docx(texto, output_path)
        print(f"✅ Relatório gerado: {output_path}")
        
        return True, output_path
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_parametros.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    
    sucesso, resultado = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)