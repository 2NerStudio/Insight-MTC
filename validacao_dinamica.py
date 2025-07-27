import re
import pdfplumber
from docx import Document
import sys

# ╭──────────────────────── util ────────────────────────╮
def _clean(txt: str) -> str:
    if not txt:
        return ""
    return (
        re.sub(r'\s+', ' ', txt)  # Normaliza espaços
        .replace("\n", " ").replace("\r", " ")
        .replace(",", ".").replace("’", "").replace("'", "")
        .replace("–", "-").replace("--", "-").replace(")", "")  # Remove ) isolados
        .strip()
    )

def _list_numeros(txt: str):
    return re.findall(r"[-+]?\d+(?:[.,]\d+)?", txt or "")

def _num(txt: str):
    try:
        return float(txt.replace(",", "."))
    except Exception:
        return None
# ╰──────────────────────────────────────────────────────╯

def _is_param_row(col3: str, col4: str) -> bool:
    """Linha-parâmetro = 3ª coluna (mín-máx) tem ≥2 números E 4ª coluna tem 1 número."""
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1

def _explode_nome(raw_nome: str):
    """
    Divide nomes colados de forma inteligente: por separadores, depois por padrões de título (maiúsculas).
    Filtra ruídos e agrupa continuações em minúsculas.
    """
    raw_nome = _clean(raw_nome)
    if not raw_nome:
        return []

    # Remove cabeçalhos conhecidos no início
    headers = ["ITEM DE TESTE", "ITEM", "DE", "TESTE"]
    for h in headers:
        if raw_nome.startswith(h):
            raw_nome = raw_nome[len(h):].strip()

    # Divisão primária por separadores
    partes = re.split(r':|KATEX_INLINE_CLOSE\s|\s{2,}|α-', raw_nome)
    partes = [p.strip(" -") for p in partes if p.strip()]

    # Divisão secundária por padrões de título (sequências começando com maiúscula)
    upper_pattern = r'[A-ZÁÀÂÃÉÈÊÍÓÔÕÚÇ][a-záàâãéèêíóôõúç0-9\sKATEX_INLINE_OPENKATEX_INLINE_CLOSE/-]*?(?=[A-ZÁÀÂÃÉÈÊÍÓÔÕÚÇ]|$)'
    exploded = []
    for p in partes:
        subs = re.findall(upper_pattern, p)
        exploded.extend([sub.strip() for sub in subs if sub.strip()])

    # Agrupa continuações em minúsculas ao item anterior
    final = []
    for part in exploded:
        if part and part[0].islower() and final:
            final[-1] += " " + part  # Anexa ao anterior
        else:
            final.append(part)

    # Filtro de duplicatas, ruídos e itens curtos
    ignore = {
        'ITEM', 'DE', 'TESTE', 'Sistema', 'Meridiano', 'Meridiano do', 'do', 
        'da', 'e', 'Afrouxamento e', 'Saturação do oxigênio do', 'Pressão do', 
        'oxigênio do sangue cerebrovascular'  # Adicione mais baseados em padrões
    }
    final = [p for i, p in enumerate(final) if p and len(p) >= 4 and p not in ignore and p not in final[:i]]

    return final

def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão 10 – otimizada para filtrar cabeçalhos e dividir nomes colados de forma inteligente.
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
    buffer_antes = []  # pedaços que vêm antes da 1ª linha-parâmetro
    headers_ignore = {"ITEM", "DE", "TESTE", "ITEM DE TESTE"}  # Ignora cabeçalhos ao acumular
    while i < len(linhas):
        nome, faixa, valor = linhas[i]

        # Se ainda não é linha-parâmetro, acumula no buffer SE NÃO for cabeçalho
        if not _is_param_row(faixa, valor):
            if nome and not any(h in nome for h in headers_ignore):
                buffer_antes.append(nome.strip())
            i += 1
            continue

        # —— encontramos a linha-parâmetro ——————————————
        numeros_faixa = _list_numeros(faixa)
        if len(numeros_faixa) < 2:
            i += 1
            continue
        minimo, maximo = map(_num, numeros_faixa[:2])
        valor_medido = _num(_list_numeros(valor)[0]) if _list_numeros(valor) else None

        # Nome começa com buffer + próprio nome (se não for cabeçalho)
        partes_nome = buffer_antes + ([nome.strip()] if nome and not any(h in nome for h in headers_ignore) else [])
        buffer_antes = []  # zera

        # Junta linhas seguintes que NÃO sejam parâmetro
        j = i + 1
        while j < len(linhas) and not _is_param_row(linhas[j][1], linhas[j][2]):
            nm_next = linhas[j][0]
            if nm_next and not any(h in nm_next for h in headers_ignore):
                partes_nome.append(nm_next.strip())
            j += 1

        nome_completo = " ".join(partes_nome)

        # Divide e associa valores
        for n in _explode_nome(nome_completo):
            resultado[n] = {"min": minimo, "max": maximo, "valor": valor_medido}

        i = j

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