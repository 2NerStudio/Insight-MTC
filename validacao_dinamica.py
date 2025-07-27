import re
import pdfplumber
from docx import Document
import sys

# ╭──────────────────────── util ────────────────────────╮
def _clean(txt: str) -> str:
    """Limpa a string, substituindo quebras de linha e vírgulas por pontos."""
    if not txt:
        return ""
    return txt.replace("\n", " ").replace("\r", " ").replace(",", ".").strip()

def _list_numeros(txt: str):
    """Extrai todos os números (inteiros ou decimais) de uma string."""
    return re.findall(r"[-+]?\d+(?:\.\d+)?", txt or "")

def _num(txt: str):
    """Converte uma string para float, lidando com possíveis erros."""
    try:
        return float(txt.replace(",", "."))
    except (ValueError, TypeError):
        return None
# ╰──────────────────────────────────────────────────────╯

def _is_param_row(col3: str, col4: str) -> bool:
    """
    Verifica se uma linha é uma linha de parâmetro.
    Regra: A 3ª coluna (intervalo) deve ter 2 números (mín-máx) e
           a 4ª coluna (valor) deve ter 1 número.
    """
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1

def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão corrigida: Extrai parâmetros do PDF de forma precisa.
    Itera por todas as linhas da tabela e processa apenas aquelas que
    correspondem ao formato de um item de teste com valores, ignorando
    cabeçalhos de categoria e outras linhas.
    """
    resultado = {}
    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            # Tenta extrair tabelas. Se falhar, continua para a próxima página.
            tabelas = pg.extract_tables(cfg)
            if not tabelas:
                continue

            for tb in tabelas:
                for row in tb:
                    # Garante que a linha tenha colunas suficientes
                    if len(row) < 4:
                        continue

                    # Limpa as colunas relevantes: Item, Intervalo, Valor
                    nome_item, faixa, valor = map(_clean, (row[1], row[2], row[3]))

                    # Processa a linha APENAS se for uma linha de parâmetro válida
                    if nome_item and _is_param_row(faixa, valor):
                        numeros_faixa = _list_numeros(faixa)
                        numero_valor = _list_numeros(valor)

                        minimo = _num(numeros_faixa[0])
                        maximo = _num(numeros_faixa[1])
                        valor_medido = _num(numero_valor[0])

                        # Adiciona ao resultado se todos os valores forem válidos
                        if all(v is not None for v in [minimo, maximo, valor_medido]):
                            resultado[nome_item] = {
                                "min": minimo,
                                "max": maximo,
                                "valor": valor_medido
                            }
    return resultado

def validar_parametros(dados: dict):
    """
    Compara o valor medido com o intervalo de normalidade e retorna uma lista de anomalias.
    """
    anomalias = []
    for item, d in dados.items():
        v, mn, mx = d["valor"], d["min"], d["max"]

        # Pula itens com dados inválidos
        if v is None or mn is None or mx is None:
            continue

        if not (mn <= v <= mx):
            anomalias.append(
                dict(
                    item=item,
                    valor_real=v,
                    status="Abaixo" if v < mn else "Acima",
                    normal_min=mn,
                    normal_max=mx,
                )
            )
    return anomalias

def _to_docx(texto: str, path: str):
    """Cria um documento .docx a partir de um texto."""
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    doc.save(path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    """
    Gera um relatório final em formato .docx com as anomalias encontradas.
    """
    try:
        dados = extrair_parametros_valores(pdf_path)
        if not dados:
            # Adiciona uma verificação para o caso de nenhum parâmetro ser extraído
            raise ValueError("Não foi possível extrair parâmetros válidos do arquivo PDF.")

        anomalias = validar_parametros(dados)

        linhas = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            "",
        ]
        if not anomalias:
            linhas.append("🎉 Todos os parâmetros encontrados estão dentro do intervalo de normalidade.")
        else:
            linhas.append(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in sorted(anomalias, key=lambda x: x['item']): # Ordena para consistência
                linhas.append(
                    f"• {a['item']}: {a['valor_real']:.3f} "
                    f"({a['status']} do normal; "
                    f"Normal: {a['normal_min']:.3f}–{a['normal_max']:.3f})"
                )

        _to_docx("\n".join(linhas), output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)


# Bloco para execução via linha de comando (CLI), mantido para testes
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> \"Nome do Terapeuta\" \"Registro Profissional\"")
        sys.exit(1)

    pdf_file, terapeuta_nome, terapeuta_reg = sys.argv[1], sys.argv[2], sys.argv[3]
    dados_extraidos = extrair_parametros_valores(pdf_file)
    anomalias_encontradas = validar_parametros(dados_extraidos)

    print(f"--- {len(anomalias_encontradas)} Anomalias Encontradas ---")
    for anomalia in sorted(anomalias_encontradas, key=lambda x: x['item']):
        print(
            f"- {anomalia['item']}: {anomalia['valor_real']} "
            f"({anomalia['status']} do normal; Normal: {anomalia['normal_min']}–{anomalia['normal_max']})"
        )

    ok, path_or_err = gerar_relatorio(pdf_file, terapeuta_nome, terapeuta_reg, "relatorio_cli.docx")
    if ok:
        print(f"\nRelatório salvo em: {path_or_err}")
        sys.exit(0)
    else:
        print(f"\nErro ao gerar relatório: {path_or_err}")
        sys.exit(1)