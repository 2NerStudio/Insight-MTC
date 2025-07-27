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


def _row_numbers(texto: str):
    "Retorna lista de todos os floats contidos na string."
    return [_num(x) for x in re.findall(r"[-+]?\d+(?:[.,]\d+)?", texto)]

def _explode_nome(raw_nome: str):
    """
    Se o nome contiver vários parâmetros colados,
    tenta separá-los por ':'  ou ') '  ou  '  '  (dois espaços).
    """
    if ":" in raw_nome:
        partes = [p.strip(" -") for p in raw_nome.split(":") if p.strip()]
    elif ") " in raw_nome:
        partes = [p.strip(" -") for p in raw_nome.split(") ") if p.strip()]
        partes = [p + (")" if not p.endswith(")") else "") for p in partes]
    else:
        partes = [raw_nome]
    # remove duplicidades ocasionais
    return [p for i, p in enumerate(partes) if p and p not in partes[:i]]

def _is_param_row(col3: str, col4: str):
    """Verdadeiro se col3 tiver ≥2 números (faixa) e col4 tiver 1 número (valor)."""
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1


def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão 7 — regras:
        • linha-parâmetro = col3 (mín, máx) + col4 (valor)
        • junta somente as linhas imediatamente DEPOIS que não contenham
          números e comecem por minúscula / '('  (continuação do nome).
    """
    resultado = {}

    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # ── carrega todas as linhas já “limpas” numa lista
    linhas = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables(cfg):
                for r in tb:
                    if len(r) < 4:
                        continue
                    col2, col3, col4 = map(_clean, r[1:4])
                    linhas.append((col2, col3, col4))

    i = 0
    while i < len(linhas):
        nome, faixa, valor = linhas[i]

        # se não é linha-parâmetro → pula
        if not _is_param_row(faixa, valor):
            i += 1
            continue

        # pega intervalo e valor
        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
        valor_medido   = _num(_list_numeros(valor)[0])

        # nome base
        partes = [nome.strip()] if nome else []

        # olha somente as PRÓXIMAS linhas sem números (continuação)
        j = i + 1
        while j < len(linhas):
            nm_next, faixa_next, valor_next = linhas[j]
            if nm_next and not (_list_numeros(faixa_next) or _list_numeros(valor_next)):
                if nm_next[0].islower() or nm_next[0] == "(":
                    partes.append(nm_next.strip())
                    j += 1
                    continue
            break  # parou na 1ª linha que não é continuação

        nome_completo = " ".join(partes)

        # se, MESMA célula, vierem 2+ itens colados → divide
        for n in _explode_nome(nome_completo):
            resultado[n] = {"min": minimo, "max": maximo, "valor": valor_medido}

        i = j  # continua depois das linhas consumidas

    return resultado


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