import re
import pdfplumber
from docx import Document
import sys

# ╭──────────────────────── util ────────────────────────╮
def _clean(txt: str) -> str:
    if not txt:
        return ""
    # Normaliza e preserva parênteses úteis
    txt = re.sub(r'\s+', ' ', txt).strip()
    return (
        txt.replace("\n", " ").replace("\r", " ")
        .replace(",", ".").replace("’", "").replace("'", "")
        .replace("–", "-").replace("--", "-")
        .replace("()", "")  # Remove parênteses vazios, mas mantém (TBA)
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
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1

def _explode_nome(raw_nome: str):
    """
    Divide nomes colados de forma avançada, preservando compostos com parênteses e juntando logicamente.
    """
    raw_nome = _clean(raw_nome)
    if not raw_nome:
        return []

    # Remove cabeçalhos conhecidos no início
    headers = ["ITEM DE TESTE", "ITEM", "DE", "TESTE"]
    for h in headers:
        if raw_nome.startswith(h):
            raw_nome = raw_nome[len(h):].strip()

    # Divisão primária por separadores fortes (corrigido: sem KATEX, usa ) \s)
    partes = re.split(r':|KATEX_INLINE_CLOSE\s{1,}|\s{2,}|α-', raw_nome)
    partes = [p.strip(" -") for p in partes if p.strip()]

    # Divisão secundária: captura frases completas, incluindo parênteses (corrigido: sem KATEX, usa KATEX_INLINE_OPEN()KATEX_INLINE_CLOSE)
    upper_pattern = r'[A-ZÁÀÂÃÉÈÊÍÓÔÕÚÇ][a-záàâãéèêíóôõúç0-9\sKATEX_INLINE_OPENKATEX_INLINE_CLOSE/-]*?(?=\s[A-ZÁÀÂÃÉÈÊÍÓÔÕÚÇ][^a-záàâãéèêíóôõúç]|\Z)'
    exploded = []
    for p in partes:
        subs = re.findall(upper_pattern, p + ' ')  # Adiciona espaço para matching final
        exploded.extend([sub.strip() for sub in subs if sub.strip()])

    # Agrupamento avançado: junta preposições, acrônimos em parênteses, vitaminas, etc.
    final = []
    for part in exploded:
        if not final:
            final.append(part)
            continue
        last = final[-1]
        if (
            part.lower() in {'da', 'do', 'de', 'e'}  # Preposições (removi duplicata 'e')
            or part[0].islower()  # Continuações minúsculas
            or (len(part) < 10 and (last.endswith(' ') or last.endswith('-') or last.endswith('(')))  # Fragmentos ou parênteses abertos
            or (last.endswith('(') and part.endswith(')'))  # Fecha parênteses, ex.: (TBA)
            or ('Vitamina' in last and (part.startswith('B') or part.startswith('K')))  # Vitaminas
            or last.endswith('do') or last.endswith('da')  # Conecta ex.: "Índice do" + "baço"
        ):
            final[-1] = f"{last} {part}".strip()
        else:
            final.append(part)

    # Filtro de duplicatas, ruídos, incompletos e itens curtos (use set para evitar duplicatas)
    ignore = {
        'ITEM', 'DE', 'TESTE', 'Sistema', 'Meridiano', 'Meridiano do', 'Meridiano da', 'do', 'da', 'e',
        'Afrouxamento e', 'Saturação do oxigênio do', 'Pressão do', 'oxigênio do sangue cerebrovascular',
        'Vitamina', 'Índice de', 'Desintoxicação e', 'Shao', 'Tai', 'Yin da mão', 'Yang do', 'Yang da',
        'Triplo', 'Aquecedor', 'Vital', 'queda', 'BA', 'V', 'Sa', 'Yang do Pé Triplo',  # Novos da saída
        'Índice do baço Tiroglobulina', 'Grau de hiperplasia óssea Linha epifisária',  # Agrupamentos ruins
        'Urobilinogênio Nitrogênio uréico Atividade pulmonar'  # Colagens específicas
    }
    final = list(set(  # Evita duplicatas
        p for p in final
        if p and len(p) >= 5 and p not in ignore
        and not p.endswith(('e', ':', 'do', 'da', 'de', ' e'))
    ))

    # Depuração opcional: Descomente para testar
    # print(f"DEBUG: Exploded names for '{raw_nome}': {final}")

    return final

def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão 13 – corrigida para regex válida, mais robustez e depuração.
    """
    resultado = {}

    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # ── carrega todas as linhas da(s) tabelas
    linhas = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pg in pdf.pages:
                for tb in pg.extract_tables(cfg):
                    for row in tb:
                        if len(row) < 4:
                            continue
                        c2, c3, c4 = map(_clean, row[1:4])
                        linhas.append((c2, c3, c4))  # (nome, faixa, valor)
    except Exception as e:
        raise ValueError(f"Erro ao abrir PDF: {str(e)}")

    if not linhas:
        raise ValueError("Nenhuma linha de tabela encontrada no PDF. Verifique o arquivo.")

    # ── percorre com índice i
    i = 0
    buffer_antes = []  # pedaços que vêm antes da 1ª linha-parâmetro
    headers_ignore = {"ITEM", "DE", "TESTE", "ITEM DE TESTE"}
    while i < len(linhas):
        nome, faixa, valor = linhas[i]

        # Se ainda não é linha-parâmetro, acumula no buffer SE NÃO for cabeçalho ou muito curto
        if not _is_param_row(faixa, valor):
            if nome and len(nome) >= 5 and not any(h in nome for h in headers_ignore) and nome not in headers_ignore:
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

        # Nome começa com buffer + próprio nome (se válido)
        partes_nome = buffer_antes + ([nome.strip()] if nome and len(nome) >= 5 and not any(h in nome for h in headers_ignore) else [])
        buffer_antes = []  # zera

        # Junta linhas seguintes que NÃO sejam parâmetro
        j = i + 1
        while j < len(linhas) and not _is_param_row(linhas[j][1], linhas[j][2]):
            nm_next = linhas[j][0]
            if nm_next and len(nm_next) >= 5 and not any(h in nm_next for h in headers_ignore):
                partes_nome.append(nm_next.strip())
            j += 1

        nome_completo = " ".join(partes_nome).strip()

        # Se o nome completo for ignorável ou vazio, pula
        if not nome_completo or all(part in headers_ignore for part in nome_completo.split()):
            i = j
            continue

        # Divide e associa valores, evitando duplicatas por valor
        nomes_divididos = _explode_nome(nome_completo)
        for n in nomes_divididos:
            key = (n, valor_medido)  # Evita duplicatas por nome+valor
            if key not in resultado:
                resultado[key] = {"min": minimo, "max": maximo, "valor": valor_medido}

    # Converte de volta para dict simples (remove tupla key)
    return {k[0]: v for k, v in resultado.items()}

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