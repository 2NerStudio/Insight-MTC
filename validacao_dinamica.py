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

def _is_param_row(faixa: str, valor: str) -> bool:
    """Verifica se uma linha contém os dados numéricos de um parâmetro."""
    return len(_list_numeros(faixa)) >= 2 and len(_list_numeros(valor)) == 1
# ╰──────────────────────────────────────────────────────╯


def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão final e robusta que lida com nomes de múltiplas linhas e descarta
    cabeçalhos de categoria, prevenindo a concatenação incorreta.
    """
    resultado = {}
    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    with pdfplumber.open(pdf_path) as pdf:
        # Buffer para armazenar partes de nomes de itens que vêm em linhas anteriores
        buffer_nome = []

        for pg in pdf.pages:
            tabelas = pg.extract_tables(cfg)
            if not tabelas:
                continue

            for tb in tabelas:
                for row in tb:
                    if len(row) < 4:
                        continue

                    nome, faixa, valor = map(_clean, (row[1], row[2], row[3]))

                    # Se a linha atual contém os dados numéricos
                    if _is_param_row(faixa, valor):
                        # Constrói o nome completo usando o buffer + o nome da linha atual
                        nome_completo_parts = buffer_nome
                        if nome:
                            nome_completo_parts.append(nome)
                        
                        nome_completo = " ".join(nome_completo_parts).strip()

                        if nome_completo:
                            numeros_faixa = _list_numeros(faixa)
                            numero_valor = _list_numeros(valor)
                            minimo = _num(numeros_faixa[0])
                            maximo = _num(numeros_faixa[1])
                            valor_medido = _num(numero_valor[0])

                            if all(v is not None for v in [minimo, maximo, valor_medido]):
                                resultado[nome_completo] = {
                                    "min": minimo,
                                    "max": maximo,
                                    "valor": valor_medido
                                }
                        
                        # Limpa o buffer pois o item foi processado
                        buffer_nome = []

                    # Se for uma linha apenas com texto (sem dados numéricos)
                    elif nome:
                        # Se o buffer já continha texto, a linha anterior era um cabeçalho.
                        # Descarta o cabeçalho e começa um novo buffer com o texto atual.
                        # Se o buffer estava vazio, apenas adiciona o texto.
                        buffer_nome = [nome]

    return resultado


def validar_parametros(dados: dict):
    """
    Compara o valor medido com o intervalo de normalidade e retorna uma lista de anomalias.
    """
    anomalias = []
    for item, d in dados.items():
        v, mn, mx = d["valor"], d["min"], d["max"]
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
            raise ValueError("Não foi possível extrair parâmetros válidos do arquivo PDF.")

        anomalias = validar_parametros(dados)
        anomalias_sorted = sorted(anomalias, key=lambda x: x['item']) # Ordena para consistência

        linhas = [
            "Relatório de Anomalias",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            "",
        ]
        if not anomalias_sorted:
            linhas.append("🎉 Todos os parâmetros encontrados estão dentro do intervalo de normalidade.")
        else:
            linhas.append(f"⚠️ {len(anomalias_sorted)} anomalias encontradas:")
            for a in anomalias_sorted:
                # Formata os números para 3 casas decimais para uma exibição limpa
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
    if len(sys.argv) < 2:
        print("Uso: python validacao_dinamica.py <arquivo.pdf> [\"Terapeuta\"] [\"Registro\"]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    terapeuta_nome = sys.argv[2] if len(sys.argv) > 2 else "Terapeuta Teste"
    terapeuta_reg = sys.argv[3] if len(sys.argv) > 3 else "Reg-001"

    print(f"Processando arquivo: {pdf_file}")
    dados_extraidos = extrair_parametros_valores(pdf_file)
    anomalias_encontradas = validar_parametros(dados_extraidos)

    print(f"\n--- {len(anomalias_encontradas)} Anomalias Encontradas ---")
    for anomalia in sorted(anomalias_encontradas, key=lambda x: x['item']):
        print(
            f"- {anomalia['item']}: {anomalia['valor_real']:.3f} "
            f"({anomalia['status']} do normal; Normal: {anomalia['normal_min']:.3f}–{anomalia['normal_max']:.3f})"
        )

    ok, path_or_err = gerar_relatorio(pdf_file, terapeuta_nome, terapeuta_reg, "relatorio_cli.docx")
    if ok:
        print(f"\nRelatório salvo em: {path_or_err}")
        sys.exit(0)
    else:
        print(f"\nErro ao gerar relatório: {path_or_err}")
        sys.exit(1)