import re
import sys
import pdfplumber
from io import BytesIO
from docx import Document

# ──────────────────────────────────────────────
# 1. EXTRAÇÃO DINÂMICA
# ──────────────────────────────────────────────
def _clean(txt: str) -> str:
    """
    Remove quebras de linha, espaços duplos e
    troca vírgula por ponto para facilitar o float().
    """
    if not txt:
        return ""
    return (
        txt.replace("\n", " ")
           .replace(",", ".")
           .replace("’", "")
           .replace("'", "")
           .strip()
    )

def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Retorna:
        {
            "Viscosidade do sangue": {"min": 48.264, "max": 65.371, "valor": 51.884},
            ...
        }
    """
    resultado = {}

    # Estratégia de tabela baseada em linhas visíveis
    table_settings = {
        "vertical_strategy":   "lines",
        "horizontal_strategy": "lines",
        "intersection_y_tolerance": 10
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tabela in page.extract_tables(table_settings):
                for linha in tabela:
                    if len(linha) < 4:
                        continue  # não é uma linha completa

                    nome   = _clean(linha[1])
                    faixa  = _clean(linha[2])
                    valor_ = _clean(linha[3])

                    if not (nome and faixa and valor_):
                        continue

                    # ---- Faixa normal (mín–máx) ----
                    # Captura TODOS os números da string
                    numeros = re.findall(r"[-+]?\d+(?:[.,]\d+)?", faixa)
                    if len(numeros) < 2:
                        # Falhou em encontrar 2 números ⇒ pula
                        continue

                    minimo = float(numeros[0].replace(",", "."))
                    maximo = float(numeros[1].replace(",", "."))

                    # ---- Valor medido ----
                    try:
                        valor = float(valor_)
                    except ValueError:
                        continue  # célula não-numérica

                    resultado[nome] = {"min": minimo, "max": maximo, "valor": valor}

    return resultado


# ──────────────────────────────────────────────
# 2.  VALIDAÇÃO
# ──────────────────────────────────────────────
def validar_parametros(dados: dict) -> list:
    """
    Recebe o dicionário gerado acima.
    Retorna lista de anomalias:
        [
            {"item": "...", "valor_real": 70, "status": "Acima",
             "normal_min": 48, "normal_max": 65},
            ...
        ]
    """
    anomalias = []

    for item, info in dados.items():
        v, mn, mx = info["valor"], info["min"], info["max"]
        if not (mn <= v <= mx):
            status = "Abaixo" if v < mn else "Acima"
            anomalias.append(
                {
                    "item": item,
                    "valor_real": v,
                    "status": status,
                    "normal_min": mn,
                    "normal_max": mx,
                }
            )
    return anomalias


# ──────────────────────────────────────────────
# 3.  RELATÓRIO .DOCX
# ──────────────────────────────────────────────
def _para_docx(texto: str, output_path: str):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    doc.save(output_path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        dados = extrair_parametros_valores(pdf_path)
        if not dados:
            raise ValueError("Não foi possível extrair parâmetros / valores do PDF.")

        anomalias = validar_parametros(dados)

        linhas = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            "",
        ]

        if not anomalias:
            linhas.append("🎉 Todos os parâmetros dentro da normalidade.")
        else:
            linhas.append(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in anomalias:
                linhas.append(
                    f"• {a['item']}: {a['valor_real']:.3f} "
                    f"({a['status']} do normal; "
                    f"Normal: {a['normal_min']}–{a['normal_max']})"
                )

        _para_docx("\n".join(linhas), output_path)
        print(f"✅ Relatório gerado em {output_path}")
        return True, output_path

    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        return False, str(e)


# ──────────────────────────────────────────────
# 4. CLI (opcional)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)

    ok, msg = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)