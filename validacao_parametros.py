import sys
import pdfplumber
from io import BytesIO
from docx import Document

def extrair_parametros_e_valores(caminho_pdf):
    """Extrai os parâmetros (intervalos normais) e valores medidos do PDF"""
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
                    # Verifica se a linha tem pelo menos 4 colunas e contém dados relevantes
                    if len(linha) >= 4 and linha[1] and linha[2] and linha[3]:
                        item_teste = linha[1].strip()
                        intervalo_normal = linha[2].strip()
                        valor_medido = linha[3].strip()
                        
                        # Processa o intervalo normal (terceira coluna)
                        if " - " in intervalo_normal:
                            try:
                                # Remove possíveis quebras de linha e processa os valores
                                intervalo_normal = intervalo_normal.replace("\n", "")
                                minimo, maximo = map(float, intervalo_normal.split(" - "))
                                
                                # Processa o valor medido (quarta coluna)
                                valor_medido = (valor_medido.replace(",", ".")
                                                  .replace(" ", "")
                                                  .replace("\n", "")
                                                  .replace("'", ""))
                                valor_medido = float(valor_medido)
                                
                                # Armazena os parâmetros e valores
                                parametros[item_teste] = (minimo, maximo)
                                valores_medidos[item_teste] = valor_medido
                            except (ValueError, AttributeError):
                                continue
    
    return parametros, valores_medidos

def validar_valores(parametros, valores):
    """Valida os valores medidos contra os parâmetros de referência"""
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
            raise ValueError("Não foi possível extrair parâmetros e valores do PDF. Verifique o formato do arquivo.")
        
        # 2) Validar valores
        anomalias = validar_valores(parametros, valores)
        
        # 3) Montar texto do relatório
        lines = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
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