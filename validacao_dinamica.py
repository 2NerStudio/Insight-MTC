import re
import pdfplumber
from docx import Document
import sys

# ╭──────────────────────── util ────────────────────────╮
def _clean(txt: str) -> str:
    """Limpa a string, substituindo quebras de linha e vírgulas por pontos."""
    if not txt:
        return ""
    # Remove quebras de linha, acentos problemáticos e troca vírgula por ponto.
    return txt.replace("\n", " ").replace("\r", " ").replace(",", ".").replace("’", "").replace("'", "").strip()

def _list_numeros(txt: str):
    """Extrai todos os números (inteiros ou decimais) de uma string."""
    return re.findall(r"[-+]?\d+(?:\.\d+)?", txt or "")

def _num(txt: str):
    """Converte uma string para float, lidando com possíveis erros."""
    try:
        return float(txt.replace(",", "."))
    except (ValueError, TypeError):
        return None

def _explode_nome(raw_nome: str):
    """
    Se o nome contiver vários parâmetros colados, tenta separá-los.
    Isso lida com casos onde o PDF agrupa itens como 'Níquel Flúor'.
    A heurística tenta quebrar a string se uma palavra começa com letra maiúscula
    no meio da string (indicando um novo item).
    """
    # Regex para encontrar palavras que começam com maiúscula (e não são a primeira palavra)
    # Isso quebra "NiquelFluor" em "Niquel", "Fluor"
    # ou "Índice de alergia ao pólen Índice de alergia a poeira" em duas partes.
    parts = re.split(r'\s+(?=[A-ZÁÉÍÓÚ])', raw_nome)
    
    # Caso especial para texto como 'Insulina)' que o regex pode não pegar bem
    if ') ' in raw_nome:
        parts = [p.strip() for p in raw_nome.split(') ')]
        parts = [p + (')' if not p.endswith(')') else '') for p in parts if p]

    return [p.strip() for p in parts if p.strip()]

def _is_param_row(col3: str, col4: str) -> bool:
    """
    Verifica se uma linha é uma linha de parâmetro.
    Regra: A 3ª coluna (intervalo) deve ter 2 números (mín-máx) e
           a 4ª coluna (valor) deve ter 1 número.
    """
    return len(_list_numeros(col3)) >= 2 and len(_list_numeros(col4)) == 1
# ╰──────────────────────────────────────────────────────╯


def extrair_parametros_valores(pdf_path: str) -> dict:
    """
    Versão final e robusta.
    Usa uma lógica de buffer para montar corretamente nomes de itens que
    se estendem por várias linhas, processando-os quando a linha com
    os dados numéricos é encontrada.
    """
    resultado = {}
    cfg = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        intersection_y_tolerance=10,
    )

    with pdfplumber.open(pdf_path) as pdf:
        partes_nome_buffer = []
        for pg in pdf.pages:
            tabelas = pg.extract_tables(cfg)
            if not tabelas:
                continue

            for tb in tabelas:
                for row in tb:
                    if len(row) < 4:
                        continue

                    # Limpa as colunas relevantes
                    nome_item, faixa, valor = map(_clean, (row[1], row[2], row[3]))

                    # Se a linha ATUAL contém os dados numéricos, é hora de processar.
                    if _is_param_row(faixa, valor):
                        # Junta o buffer com o texto da linha atual para formar o nome completo
                        if nome_item:
                            partes_nome_buffer.append(nome_item)
                        
                        nome_completo = " ".join(partes_nome_buffer)

                        # Extrai os dados numéricos
                        numeros_faixa = _list_numeros(faixa)
                        numero_valor = _list_numeros(valor)
                        minimo = _num(numeros_faixa[0])
                        maximo = _num(numeros_faixa[1])
                        valor_medido = _num(numero_valor[0])

                        # A função _explode_nome lida com casos como "Níquel Flúor"
                        # que podem ter sido agrupados na mesma linha de texto.
                        nomes_individuais = _explode_nome(nome_completo)

                        # Se explodiu em vários nomes, assume que os dados pertencem ao PRIMEIRO.
                        # Isso é uma heurística necessária para o formato do seu PDF.
                        # Para os demais itens, não temos os valores, então não podemos adicioná-los.
                        item_principal = nomes_individuais[0]

                        if all(v is not None for v in [minimo, maximo, valor_medido]):
                             resultado[item_principal] = {
                                "min": minimo,
                                "max": maximo,
                                "valor": valor_medido
                            }

                        # CRUCIAL: Reseta o buffer para o próximo item
                        partes_nome_buffer = []

                    # Se não é uma linha com dados, e tem texto, acumula no buffer.
                    elif nome_item:
                        partes_nome_buffer.append(nome_item)
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
        
        # Ordena as anomalias alfabeticamente pelo nome do item para um relatório consistente
        anomalias_sorted = sorted(anomalias, key=lambda x: x['item'])

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