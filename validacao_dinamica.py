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
    Versão 3 – junta *todos* os pedaços de nome que aparecem
    antes da linha que contém faixa+valor.
    """
    resultado = {}
    buffer_nome = []          # pedaços acumulados

    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tabela in page.extract_tables(cfg):
                for linha in tabela:
                    if len(linha) < 4:
                        continue

                    nome  = _clean(linha[1])
                    faixa = _clean(linha[2])
                    valor = _clean(linha[3])

                    tem_faixa = len(_list_numeros(faixa)) >= 2
                    tem_valor = len(_list_numeros(valor)) == 1

                    # 1) Linha só com texto (sem números)  → empilha
                    if nome and not tem_faixa and not tem_valor:
                        buffer_nome.append(nome)
                        continue

                    # 2) Linha que contém os números  → fecha o parâmetro
                    if nome and tem_faixa and tem_valor:
                        nome_completo = " ".join(buffer_nome + [nome]).strip()
                        buffer_nome = []  # zera para o próximo

                        minimo, maximo = map(_num, _list_numeros(faixa)[:2])
                        valor_num      = _num(_list_numeros(valor)[0])

                        if nome_completo and minimo is not None and maximo is not None:
                            resultado[nome_completo] = {
                                "min": minimo,
                                "max": maximo,
                                "valor": valor_num,
                            }
                        continue

                    # 3) Qualquer outra linha inesperada → ignora
                    #    (mas se quisermos ser ainda mais conservadores,
                    #     poderíamos: if nome: buffer_nome.append(nome))
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