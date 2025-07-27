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
    Versão 4  –  pega pedaços ANTES e DEPOIS da linha com números.
    Resolve casos como:
       • “Viscosidade do”   (linha com números)
         “sangue”           (linha logo a seguir, sem números)
    """
    resultado = {}

    # Configuração da extração de tabelas
    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    # Primeiro, coletamos todas as linhas numa lista simples
    linhas = []  # cada item -> (nome, faixa, valor, tem_numeros)
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tabela in page.extract_tables(cfg):
                for row in tabela:
                    if len(row) < 4:
                        continue
                    nome  = _clean(row[1])
                    faixa = _clean(row[2])
                    valor = _clean(row[3])

                    tem_faixa = len(_list_numeros(faixa)) >= 2
                    tem_valor = len(_list_numeros(valor)) == 1
                    tem_numeros = tem_faixa and tem_valor

                    linhas.append((nome, faixa, valor, tem_numeros))

    # Agora processamos com ponteiro 'i'
    i = 0
    buffer_antes = []  # pedaços de nome antes da linha-núcleo

    while i < len(linhas):
        nome, faixa, valor, is_num = linhas[i]

        if not is_num:
            # Ainda não chegamos à linha-núcleo → acumulo no buffer
            if nome:
                buffer_antes.append(nome)
            i += 1
            continue

        # Linha-núcleo encontrada  (tem faixa+valor)
        # 1) junta os pedaços anteriores + próprio nome
        partes_nome = buffer_antes + ([nome] if nome else [])
        buffer_antes = []  # zera para o próximo parâmetro

        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
        valor_num      = _num(_list_numeros(valor)[0])

        # 2) olha as linhas logo DEPOIS, enquanto não aparecer nova linha-núcleo
        j = i + 1
        while j < len(linhas) and not linhas[j][3]:
            nome_pos, _, _, _ = linhas[j]
            if nome_pos:
                partes_nome.append(nome_pos)
            j += 1

        nome_completo = " ".join(partes_nome).strip()
        if nome_completo and minimo is not None and maximo is not None:
            resultado[nome_completo] = {
                "min": minimo,
                "max": maximo,
                "valor": valor_num,
            }

        # Continua a partir da próxima linha ainda não processada
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