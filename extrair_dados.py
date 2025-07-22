import pdfplumber

def extrair_dados_do_pdf(arquivo_streamlit):
    dados_extraidos = []

    with pdfplumber.open(arquivo_streamlit) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                sistema_atual = None
                for linha in tabela:
                    # pula linhas vazias ou não-tabelares
                    if not linha or all((cell is None or cell.strip()=="") for cell in linha):
                        continue

                    # garante pelo menos 5 colunas
                    linha = (linha + [""]*5)[:5]
                    sistema, item, intervalo, valor, conselho = [ (c or "").strip() for c in linha ]

                    # se a célula 'Sistema' estiver preenchida, definimos o contexto
                    if sistema and not sistema.lower().startswith("sistema"):
                        sistema_atual = sistema

                    # pula cabeçalhos
                    if item.lower().startswith("item"):
                        continue
                    # pula linhas sem item
                    if not item:
                        continue

                    dados_extraidos.append({
                        "sistema": sistema_atual,
                        "item": item,
                        "intervalo": intervalo,
                        "valor": valor,
                        "conselho": conselho
                    })
    return dados_extraidos
