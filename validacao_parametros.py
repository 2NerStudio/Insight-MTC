import sys
import pdfplumber
from io import BytesIO
from docx import Document

# Função para extrair dinamicamente parâmetros do PDF de exemplo

def extrair_parametros_do_pdf(caminho_pdf):
    """
    Extrai os nomes dos testes (coluna 2) e seus intervalos normais (coluna 3)
    e retorna um dicionário no formato {item: (min, max)}.
    """
    parametros = {}
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_y_tolerance": 10
            }
            tabelas = page.extract_tables(table_settings)
            for tabela in tabelas:
                for linha in tabela:
                    # Esperamos pelo menos 4 colunas (SISTEMA, ITEM, INTERVALO, VALOR, ...)
                    if len(linha) >= 4:
                        item = linha[1].strip() if linha[1] else None
                        intervalo = linha[2].strip() if linha[2] else None
                        if item and intervalo:
                            # Limpa texto e extrai dois números separados por '-'
                            intervalo_clean = intervalo.replace(' ', '').replace(',', '.')
                            parts = intervalo_clean.split('-')
                            if len(parts) == 2:
                                try:
                                    minimo = float(parts[0])
                                    maximo = float(parts[1])
                                    parametros[item] = (minimo, maximo)
                                except ValueError:
                                    # ignora linhas com intervalo inválido
                                    continue
    return parametros

# Função existente para extrair valores (4ª coluna) usando o dicionário de parâmetros

def extrair_valores_do_pdf(caminho_pdf, chaves_parametros):
    """Extrai os valores da 4ª coluna correspondentes às chaves fornecidas"""
    valores = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_y_tolerance": 10
            }
            tabelas = page.extract_tables(table_settings)
            for tabela in tabelas:
                for linha in tabela:
                    if len(linha) >= 4:
                        valor = linha[3].strip() if linha[3] else ""
                        valor = (valor.replace(",", ".")
                                   .replace(" ", "")
                                   .replace("\n", "")
                                   .replace("'", ""))
                        if valor and valor.replace('.', '', 1).isdigit():
                            valores.append(float(valor))
    # Mapeia cada chave à seu valor na ordem de aparição
    return dict(zip(chaves_parametros, valores[:len(chaves_parametros)]))

# Função de validação permanece igual

def validar_valores(valores, parametros):
    anomalias = []
    for item, valor in valores.items():
        if item not in parametros:
            continue
        minimo, maximo = parametros[item]
        try:
            v = float(valor)
            if not (minimo <= v <= maximo):
                status = "Abaixo" if v < minimo else "Acima"
                anomalias.append({
                    "item": item,
                    "valor_real": v,
                    "status": status,
                    "normal_min": minimo,
                    "normal_max": maximo
                })
        except (ValueError, TypeError):
            continue
    return anomalias

# Exportação para DOCX

def exportar_para_docx(texto, output_path):
    doc = Document()
    for line in texto.split("\n"):
        doc.add_paragraph(line)
    doc.save(output_path)

# Gerar relatório usando parâmetros extraídos

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        # 1) Extrair parâmetros do próprio PDF
        parametros = extrair_parametros_do_pdf(pdf_path)
        if not parametros:
            raise ValueError("Nenhum parâmetro foi extraído do PDF. Verifique o formato.")
        # 2) Extrair valores
        valores = extrair_valores_do_pdf(pdf_path, list(parametros.keys()))
        if not valores:
            raise ValueError("Nenhum valor foi extraído do PDF. Verifique o formato.")
        # 3) Validar
        anomalias = validar_valores(valores, parametros)
        # 4) Montar texto
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

# Execução principal

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_parametros.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    sucesso, resultado = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)
