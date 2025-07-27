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

def _is_param_row(col3: str, col4: str) -> bool:
    """Linha-parâmetro = 3ª coluna (mín-máx) tem ≥2 números  E  4ª coluna tem 1 número."""
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1


def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão 8 – definitiva
    • identifica a linha-parâmetro como acima
    • junta TODAS as linhas sem números entre esta e a próxima linha-parâmetro
    • mantém as partes antes (caso ‘Viscosidade do’   +   linha-parâmetro)
    """
    resultado = {}

    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # ── carrega todas as linhas da(s) tabelas
    linhas = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables(cfg):
                for row in tb:
                    if len(row) < 4:
                        continue
                    c2, c3, c4 = map(_clean, row[1:4])
                    linhas.append((c2, c3, c4))  # (nome, faixa, valor)

    # ── percorre com índice i
    i = 0
    buffer_antes = []          # pedaços que vêm antes da 1ª linha-parâmetro
    while i < len(linhas):
        nome, faixa, valor = linhas[i]

        # Se ainda não é linha-parâmetro, acumula no buffer e segue
        if not _is_param_row(faixa, valor):
            if nome:
                buffer_antes.append(nome.strip())
            i += 1
            continue

        # —— encontramos a linha-parâmetro ——————————————
        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
        valor_medido   = _num(_list_numeros(valor)[0])

        # Nome começa com o que estava antes + próprio nome da linha
        partes_nome = buffer_antes + ([nome.strip()] if nome else [])
        buffer_antes = []  # zera para próximo ciclo

        # Junta TODAS as linhas seguintes que NÃO sejam parâmetro
        j = i + 1
        while j < len(linhas) and not _is_param_row(linhas[j][1], linhas[j][2]):
            nm_next = linhas[j][0]
            if nm_next:
                partes_nome.append(nm_next.strip())
            j += 1

        nome_completo = " ".join(partes_nome)

        # Se vieram 2+ itens na mesma célula, divide por ':'  ') '  '  '
        for n in _explode_nome(nome_completo):
            resultado[n] = {"min": minimo, "max": maximo, "valor": valor_medido}

        i = j  # continua a partir da próxima linha-parâmetro

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