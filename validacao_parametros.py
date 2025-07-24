import sys
import pdfplumber
from docx import Document
from io import BytesIO
import re

# Função para extrair parâmetros e valores a partir de tabelas do PDF

def extrair_parametros_e_valores(caminho_pdf):
    """
    Extrai de cada tabela do PDF:
      - item (coluna 2)
      - intervalo normal (coluna 3, ex: 'min - max')
      - valor medido (coluna 4)
    Retorna:
      parametros: dict[item] = (min, max)
      valores: dict[item] = valor
    """
    parametros = {}
    valores = {}

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_y_tolerance": 5
    }

    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            tabelas = page.extract_tables(table_settings)
            for tabela in tabelas:
                for linha in tabela:
                    # validar colunas: precisa ter ao menos 4
                    if not linha or len(linha) < 4:
                        continue
                    item = linha[1].strip() if linha[1] else None
                    intervalo = linha[2].strip() if linha[2] else None
                    valor_raw = linha[3].strip() if linha[3] else None
                    if not item or not intervalo or not valor_raw:
                        continue
                    # limpar strings
                    intervalo_clean = intervalo.replace(' ', '').replace(',', '.')
                    # suporta tanto '-' quanto '–'
                    parts = re.split(r"[–-]", intervalo_clean)
                    if len(parts) != 2:
                        continue
                    try:
                        minimo = float(parts[0])
                        maximo = float(parts[1])
                    except ValueError:
                        continue
                    # valor
                    val_clean = valor_raw.replace(' ', '').replace(',', '.')
                    # extrair numero no inicio da string
                    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)", val_clean)
                    if not m:
                        continue
                    try:
                        valor = float(m.group(1))
                    except ValueError:
                        continue
                    # atribuir
                    parametros[item] = (minimo, maximo)
                    valores[item] = valor
    return parametros, valores

# Validação de valores usando dicionários extraídos

def validar_valores(valores, parametros):
    anomalias = []
    for item, valor in valores.items():
        if item not in parametros:
            continue
        minimo, maximo = parametros[item]
        try:
            v = float(valor)
        except (ValueError, TypeError):
            continue
        if v < minimo or v > maximo:
            status = "Abaixo" if v < minimo else "Acima"
            anomalias.append({
                "item": item,
                "valor_real": v,
                "status": status,
                "normal_min": minimo,
                "normal_max": maximo
            })
    return anomalias

# Exportar relatório para DOCX

def exportar_para_docx(texto, output_path):
    doc = Document()
    for line in texto.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

# Geração de relatório

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        parametros, valores = extrair_parametros_e_valores(pdf_path)
        if not parametros:
            raise ValueError("Nenhum parâmetro extraído. Verifique o formato do PDF.")
        anomalias = validar_valores(valores, parametros)

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
        exportar_para_docx(texto, output_path)
        print(f"✅ Relatório gerado: {output_path}")
        return True, output_path
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_parametros.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    sucesso, resultado = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)
