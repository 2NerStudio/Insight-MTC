import sys
import pdfplumber
from io import BytesIO
from docx import Document

def extrair_parametros_e_valores(caminho_pdf):
    """Extrai os intervalos normais (3ª coluna) e valores medidos (4ª coluna) com tratamento robusto"""
    parametros = {}
    valores_medidos = {}
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            # Configuração otimizada para tabelas com bordas visíveis
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_y_tolerance": 10
            }
            
            tabelas = page.extract_tables(table_settings)
            
            for tabela in tabelas:
                for linha in tabela:
                    # Verificação segura de colunas e valores
                    try:
                        # Garante que temos pelo menos 4 colunas e que não são None
                        if len(linha) < 4:
                            continue
                            
                        item = linha[1] if linha[1] is not None else ""
                        intervalo = linha[2] if linha[2] is not None else ""
                        valor = linha[3] if linha[3] is not None else ""
                        
                        # Limpeza dos valores
                        item = item.strip()
                        intervalo = intervalo.strip()
                        valor = valor.strip()
                        
                        if not item or not intervalo or not valor:
                            continue
                            
                        # Processa o intervalo normal (3ª coluna)
                        intervalo = (intervalo.replace("\n", " ")
                                     .replace(",", ".")
                                     .replace(" ", ""))
                        
                        if " - " in intervalo or "-" in intervalo:
                            # Trata ambos os formatos "X.XXX - Y.YYY" e "X.XXX-Y.YYY"
                            separador = " - " if " - " in intervalo else "-"
                            minimo, maximo = map(float, intervalo.split(separador))
                            
                            # Processa o valor medido (4ª coluna)
                            valor = (valor.replace(",", ".")
                                      .replace(" ", "")
                                      .replace("\n", "")
                                      .replace("'", ""))
                            
                            if valor.replace(".", "", 1).isdigit():
                                parametros[item] = (minimo, maximo)
                                valores_medidos[item] = float(valor)
                    except (ValueError, AttributeError):
                        continue
    
    return parametros, valores_medidos

def validar_valores(parametros, valores):
    """Validação rigorosa usando os parâmetros extraídos"""
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
    """Cria um .docx com o texto dado e salva em output_path"""
    doc = Document()
    for line in texto.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        # 1) Extrair parâmetros e valores
        parametros, valores = extrair_parametros_e_valores(pdf_path)
        if not parametros or not valores:
            raise ValueError("Nenhum parâmetro ou valor válido foi extraído do PDF.")
        
        # 2) Validar valores
        anomalias = validar_valores(parametros, valores)
        
        # 3) Montar texto do relatório
        lines = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            f"Total de parâmetros analisados: {len(parametros)}",
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
        
        texto = "\n".join(lines)
        
        # 4) Exportar para DOCX
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