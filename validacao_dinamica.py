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

def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão 5 – robusta para:
        • Quebra antes + depois
        • Linha-núcleo com números em QUALQUER coluna
        • Vários parâmetros colados na mesma célula
    """
    resultado = {}
    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # 1) Carrega todas as linhas da(s) tabela(s)
    linhas = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables(cfg):
                for row in tbl:
                    if len(row) < 4:
                        continue
                    col2, col3, col4 = map(_clean, row[1:4])
                    linha_txt = " ".join([col2, col3, col4])
                    nums = _row_numbers(linha_txt)
                    linhas.append(
                        dict(nome=col2, faixa=col3, valor=col4, nums=nums)
                    )

    # 2) Percorre com índice, acumulando partes de nome
    buffer = []
    i = 0
    while i < len(linhas):
        ln = linhas[i]

        if len(ln["nums"]) < 3:
            # ainda não chegou a uma linha com 3 números ⇒ só acumula nome
            if ln["nome"]:
                buffer.append(ln["nome"])
            i += 1
            continue

        # Linha-núcleo: tem pelo menos 3 números
        min_, max_, val = ln["nums"][:3]

        # Nome completo = buffer antes + nome desta linha
        nome_base = " ".join(buffer + [ln["nome"]]).strip()
        buffer = []  # limpa

        # Também pegar pedaços DEPOIS desta linha até nova linha-núcleo
        j = i + 1
        pos_pieces = []
        while j < len(linhas) and len(linhas[j]["nums"]) < 3:
            if linhas[j]["nome"]:
                pos_pieces.append(linhas[j]["nome"])
            j += 1
        nome_todo = " ".join([nome_base] + pos_pieces).strip()

        # Divide caso contenha vários parâmetros colados
        for nome in _explode_nome(nome_todo):
            resultado[nome] = {"min": min_, "max": max_, "valor": val}

        i = j  # avança

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