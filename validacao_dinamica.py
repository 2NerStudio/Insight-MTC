import re
import pdfplumber
from docx import Document
import sys

# ╭────────────── utilidades ──────────────╮
def _clean(txt: str) -> str:
    """Remove \n, vírgulas, aspas esquisitas, etc."""
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

def _list_numeros(txt: str):
    return re.findall(r"[-+]?\d+(?:[.,]\d+)?", txt or "")

def _num(txt: str):
    try:
        return float(txt.replace(",", "."))
    except Exception:
        return None
# ╰────────────────────────────────────────╯


# ── helpers para a V8 ─────────────────────────────────
def _is_param_row(col3: str, col4: str) -> bool:
    """
    Linha-parâmetro ⇢ 3ª coluna traz ≥2 números (mín–máx)
                       4ª coluna traz 1 número  (valor medido)
    """
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1


def _explode_nome(raw_nome: str):
    """
    Divide quando vários parâmetros vêm colados na mesma célula.
    Usa 3 heurísticas (:   )␠   duplo espaço).
    """
    if ":" in raw_nome:
        partes = [p.strip(" -") for p in raw_nome.split(":") if p.strip()]
    elif ") " in raw_nome:
        partes = [p.strip(" -") for p in raw_nome.split(") ") if p.strip()]
        partes = [p + (")" if not p.endswith(")") else "") for p in partes]
    elif "  " in raw_nome:
        partes = [p.strip() for p in raw_nome.split("  ") if p.strip()]
    else:
        partes = [raw_nome]

    # remove duplicados preservando ordem
    return [p for i, p in enumerate(partes) if p and p not in partes[:i]]


# ── EXTRAÇÃO (Versão 8 – definitiva) ─────────────────
def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    1. Identifica linha-parâmetro via _is_param_row().
    2. Nome = (todas as linhas SEM números) que:
        • vêm antes da linha-parâmetro (buffer)
        • aparecem depois, até a próxima linha-parâmetro.
    3. Se vários parâmetros estiverem colados na mesma célula,
       divide com _explode_nome().
    Retorna:
        {"Viscosidade do sangue":
             {"min": 48.264, "max": 65.371, "valor": 70.494}, ...}
    """
    resultado = {}

    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # 1) Lê todas as linhas das tabelas em lista simples
    linhas = []  # (nome, faixa, valor)
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables(cfg):
                for row in tb:
                    if len(row) < 4:
                        continue
                    col2, col3, col4 = map(_clean, row[1:4])
                    linhas.append((col2, col3, col4))

    # 2) Varre com índice
    buffer_antes = []   # pedaços antes da 1ª linha-parâmetro
    i = 0
    while i < len(linhas):
        nome, faixa, valor = linhas[i]

        # não é linha-parâmetro ⇒ acumula no buffer
        if not _is_param_row(faixa, valor):
            if nome:
                buffer_antes.append(nome.strip())
            i += 1
            continue

        # linha-parâmetro encontrada
        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
        valor_medido   = _num(_list_numeros(valor)[0])

        partes_nome = buffer_antes + ([nome.strip()] if nome else [])
        buffer_antes = []  # zera para próximo parâmetro

        # junta TODAS as linhas seguintes até a próxima linha-parâmetro
        j = i + 1
        while j < len(linhas) and not _is_param_row(linhas[j][1], linhas[j][2]):
            nm_next = linhas[j][0]
            if nm_next:
                partes_nome.append(nm_next.strip())
            j += 1

        nome_completo = " ".join(partes_nome)

        for n in _explode_nome(nome_completo):
            resultado[n] = {"min": minimo, "max": maximo, "valor": valor_medido}

        i = j  # avança para a próxima linha-parâmetro

    return resultado


# ── VALIDAÇÃO ─────────────────────────────────────────
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


# ── DOCX ──────────────────────────────────────────────
def _to_docx(texto: str, path: str):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    doc.save(path)


def gerar_relatorio(pdf_path, terapeuta, registro,
                    output_path="relatorio_anomalias.docx"):
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


# ── CLI opcional ──────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> "
              "\"Terapeuta\" \"Registro\"")
        sys.exit(1)
    ok, _ = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)