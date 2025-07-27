import re
import sys
import pdfplumber
from docx import Document


# ────────────────────────────────
# utilidades
# ────────────────────────────────
def _clean(txt: str) -> str:
    """
    Remove quebras de linha, normaliza vírgula/ponto
    e apaga aspas estranhas.
    """
    if not txt:
        return ""
    return (
        txt.replace("\n", " ")
        .replace("\r", " ")
        .replace(",", ".")
        .replace("’", "")
        .replace("'", "")
        .strip()
    )


def _str_to_float(num_str: str):
    try:
        return float(num_str.replace(",", "."))
    except Exception:
        return None


def _tem_dois_numeros(faixa: str):
    return len(re.findall(r"[-+]?\d+(?:[.,]\d+)?", faixa)) >= 2


def _pega_dois_numeros(faixa: str):
    nums = re.findall(r"[-+]?\d+(?:[.,]\d+)?", faixa)
    return _str_to_float(nums[0]), _str_to_float(nums[1])


def _eh_numero(valor: str):
    return bool(re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", valor))


# ────────────────────────────────
# 1) EXTRAÇÃO DINÂMICA
# ────────────────────────────────
def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Retorna:
        {
            "Viscosidade do sangue": {
                "min": 48.264, "max": 65.371, "valor": 70.494
            },
            ...
        }
    Agora suporta nomes quebrados em 2-3 linhas.
    """
    resultado = {}
    nome_em_andamento = []  # partes acumuladas do nome

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_y_tolerance": 10,
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tabela in page.extract_tables(table_settings):
                for linha in tabela:
                    if len(linha) < 4:
                        continue  # linha muito curta

                    # limpeza
                    nome_cell = _clean(linha[1])
                    faixa_cell = _clean(linha[2])
                    valor_cell = _clean(linha[3])

                    # Acumula a parte do nome (sempre existe algo na col. 2)
                    if nome_cell:
                        nome_em_andamento.append(nome_cell)

                    # Verifico se ESTA linha já tem faixa e valor válidos
                    cond_faixa_ok = _tem_dois_numeros(faixa_cell)
                    cond_valor_ok = _eh_numero(valor_cell)

                    if cond_faixa_ok and cond_valor_ok:
                        # Fechamos um parâmetro completo
                        nome_completo = " ".join(nome_em_andamento).strip()
                        nome_em_andamento = []  # zera para o próximo

                        minimo, maximo = _pega_dois_numeros(faixa_cell)
                        valor = _str_to_float(valor_cell)

                        if nome_completo and minimo is not None and maximo is not None:
                            resultado[nome_completo] = {
                                "min": minimo,
                                "max": maximo,
                                "valor": valor,
                            }

                # Segurança: se terminar a página com nome pendente, força reset
                if nome_em_andamento and len(nome_em_andamento) > 5:
                    nome_em_andamento = []

    return resultado


# ────────────────────────────────
# 2) VALIDAÇÃO
# ────────────────────────────────
def validar_parametros(dados: dict):
    anomalias = []
    for item, info in dados.items():
        v, mn, mx = info["valor"], info["min"], info["max"]
        if v is None:
            continue
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


# ────────────────────────────────
# 3) DOCX
# ────────────────────────────────
def _para_docx(texto, output_path):
    doc = Document()
    for l in texto.split("\n"):
        doc.add_paragraph(l)
    doc.save(output_path)


def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        dados = extrair_parametros_valores(pdf_path)
        if not dados:
            raise ValueError("Não foi possível extrair parâmetros.")

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
        return True, output_path

    except Exception as e:
        return False, str(e)


# CLI opcional
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> \"Terapeuta\" \"Registro\"")
        sys.exit(1)
    ok, _ = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)