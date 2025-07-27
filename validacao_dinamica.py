import re
import pdfplumber
from docx import Document
import sys

# ╭──────────────────────── util ────────────────────────╮
def _clean(txt: str) -> str:
    if not txt:
        return ""
    return (
        txt.replace("\n", " ").replace("\r", " ")
        .replace(",", ".").replace("’", "").replace("'", "").strip()
    )

def _list_numeros(txt: str):
    return re.findall(r"[-+]?\d+(?:[.,]\d+)?", txt or "")

def _num(txt: str):
    try:
        return float(txt.replace(",", "."))
    except Exception:
        return None
# ╰──────────────────────────────────────────────────────╯


def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Extrai parâmetros onde:
      • Nome          → 2ª coluna  (pode vir quebrado em várias linhas)
      • Faixa normal  → 3ª coluna  (precisa conter pelo menos 2 números)
      • Valor medido  → 4ª coluna  (precisa conter 1 número)

    Estrutura retornada:
        {"Viscosidade do sangue":
              {"min":48.264, "max":65.371, "valor":70.494}, ...}
    """
    result = {}
    ult_param = None         # mantém a chave do último parâmetro fechado
    ult_foi_numerico = False # True se a linha anterior tinha faixa/valor

    settings = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables(settings):
                for row in tbl:
                    if len(row) < 4:
                        continue

                    nome  = _clean(row[1])
                    faixa = _clean(row[2])
                    valor = _clean(row[3])

                    tem_numeros_faixa = len(_list_numeros(faixa)) >= 2
                    tem_valor         = len(_list_numeros(valor)) == 1

                    # ── Caso 1: linha SÓ de continuação do nome?
                    if nome and not tem_numeros_faixa and not tem_valor:
                        if ult_param and ult_foi_numerico:
                            # anexamos ao nome do último parâmetro
                            novo_nome = (ult_param + " " + nome).strip()
                            result[novo_nome] = result.pop(ult_param)
                            ult_param = novo_nome
                        else:
                            # provavelmente é o início de um novo parâmetro,
                            # mas ainda sem números → aguardamos as próximas linhas
                            ult_param = nome      # inicia pré-param.
                        ult_foi_numerico = False
                        continue

                    # ── Caso 2: linha que traz faixa + valor  → fecha parâmetro
                    if nome and tem_numeros_faixa and tem_valor:
                        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
                        valor_num      = _num(_list_numeros(valor)[0])

                        result[nome] = {"min": minimo, "max": maximo, "valor": valor_num}
                        ult_param = nome
                        ult_foi_numerico = True
                        continue

                    # ── Qualquer outra combinação é irrelevante
                    ult_foi_numerico = False

    return result


def validar_parametros(dados: dict):
    anom = []
    for item, d in dados.items():
        v, mn, mx = d["valor"], d["min"], d["max"]
        if v is None or mn is None or mx is None:
            continue
        if not (mn <= v <= mx):
            anom.append(
                dict(
                    item=item,
                    valor_real=v,
                    status="Abaixo" if v < mn else "Acima",
                    normal_min=mn,
                    normal_max=mx,
                )
            )
    return anom


def _to_docx(texto: str, path: str):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    doc.save(path)


def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        dados = extrair_parametros_valores(pdf_path)
        if not dados:
            raise ValueError("Não foi possível extrair parâmetros do PDF.")

        anom = validar_parametros(dados)

        linhas = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            "",
        ]
        if not anom:
            linhas.append("🎉 Todos os parâmetros dentro da normalidade.")
        else:
            linhas.append(f"⚠️ {len(anom)} anomalias encontradas:")
            for a in anom:
                linhas.append(
                    f"• {a['item']}: {a['valor_real']:.3f} "
                    f"({a['status']} do normal; "
                    f"Normal: {a['normal_min']}–{a['normal_max']})"
                )

        _to_docx("\n".join(linhas), output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)


# CLI (opcional)
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> \"Terapeuta\" \"Registro\"")
        sys.exit(1)
    ok, _ = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)