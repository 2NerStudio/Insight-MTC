import sys
import pdfplumber
from docx import Document
import re

# Função unificada para extrair parâmetros e valores via regex de texto

def extrair_parametros_e_valores(caminho_pdf):
    """
    Extrai de cada linha: Nome do teste, intervalo (min-max) e valor medido.
    Retorna dois dicionários:
      parametros: {item: (min, max)}
      valores: {item: valor}
    """
    parametros = {}
    valores = {}
    pattern = re.compile(r"^\s*(?P<item>.+?)\s+(?P<min>[0-9]+(?:[\.,][0-9]+)?)\s*[–-]\s*(?P<max>[0-9]+(?:[\.,][0-9]+)?)\s+(?P<val>[0-9]+(?:[\.,][0-9]+)?)\s*$")

    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.splitlines():
                m = pattern.match(line)
                if m:
                    item = m.group('item').strip()
                    mn = float(m.group('min').replace(',', '.'))
                    mx = float(m.group('max').replace(',', '.'))
                    val = float(m.group('val').replace(',', '.'))
                    parametros[item] = (mn, mx)
                    valores[item] = val
    return parametros, valores

# Validação permanece igual

def validar_valores(valores, parametros):
    anomalias = []
    for item, valor in valores.items():
        if item not in parametros:
            continue
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

# Exportação para DOCX

def exportar_para_docx(texto, output_path):
    doc = Document()
    for line in texto.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

# Gera relatório usando extração unificada

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        parametros, valores = extrair_parametros_e_valores(pdf_path)
        if not parametros:
            raise ValueError("Nenhum parâmetro foi extraído. Verifique o formato do PDF.")
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
