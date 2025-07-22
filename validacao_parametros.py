import sys
import pdfplumber
from docx import Document

def extrair_valores_do_pdf(caminho_pdf):
    """
    Extrai intervalos normais (Coluna 3) e valores reais (Coluna 4) do PDF.
    """
    dados = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            tabelas = page.extract_tables()
            
            for tabela in tabelas:
                for linha in tabela:
                    if len(linha) >= 4:
                        item_teste = linha[1].strip()  # Coluna 2 (apenas para referência)
                        intervalo_normal = linha[2].strip()  # Coluna 3
                        valor_real = linha[3].strip()  # Coluna 4
                        
                        # Limpa e formata os valores
                        valor_real = valor_real.replace(",", ".")
                        intervalo_normal = intervalo_normal.replace(",", ".")
                        
                        # Extrai mínimo e máximo do intervalo normal (ex: "48.264 - 65.371")
                        if " - " in intervalo_normal:
                            minimo, maximo = map(float, intervalo_normal.split(" - "))
                        else:
                            continue  # Ignora linhas sem intervalo válido
                        
                        if valor_real.replace(".", "", 1).isdigit():
                            dados.append({
                                "item": item_teste,
                                "valor_real": float(valor_real),
                                "normal_min": minimo,
                                "normal_max": maximo
                            })
    
    return dados

def validar_valores(dados):
    """
    Valida os valores reais contra os intervalos normais.
    """
    anomalias = []
    for item in dados:
        valor_real = item["valor_real"]
        minimo = item["normal_min"]
        maximo = item["normal_max"]
        
        if valor_real < minimo:
            status = "Abaixo"
        elif valor_real > maximo:
            status = "Acima"
        else:
            continue  # Dentro do normal
        
        anomalias.append({
            "item": item["item"],
            "valor_real": valor_real,
            "status": status,
            "normal_min": minimo,
            "normal_max": maximo
        })
    
    return anomalias

def exportar_para_docx(texto, output_path):
    """
    Exporta o relatório para DOCX.
    """
    doc = Document()
    doc.add_paragraph(texto)
    doc.save(output_path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        # Extrai dados do PDF
        dados = extrair_valores_do_pdf(pdf_path)
        if not dados:
            raise ValueError("Nenhum dado válido foi extraído do PDF.")
        
        # Valida os valores
        anomalias = validar_valores(dados)
        
        # Gera o relatório
        lines = [
            "Relatório de Anomalias (Comparação: Intervalo Normal vs. Valor Real)",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            ""
        ]
        
        if not anomalias:
            lines.append("✅ Todos os parâmetros dentro da normalidade.")
        else:
            lines.append(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in anomalias:
                lines.append(
                    f"• {a['item']}: {a['valor_real']:.3f}  "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                )
        
        texto = "\n".join(lines)
        
        # Exporta para DOCX
        exportar_para_docx(texto, output_path)
        print(f"✅ Relatório gerado: {output_path}")
        return True, output_path
    
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python script.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    
    sucesso, resultado = gerer_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)