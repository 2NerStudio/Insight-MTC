import pdfplumber

def extrair_dados_do_pdf(arquivo_streamlit):
    import pdfplumber
    dados_extraidos = []

    with pdfplumber.open(arquivo_streamlit) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Ignora cabeçalho ou linhas incompletas
                    if linha is None or len(linha) != 4:
                        continue

                    item, intervalo, valor, conselho = linha

                    # Ignora linhas que não são dados válidos
                    if item.strip().lower() == "item":
                        continue

                    dados_extraidos.append({
                        "item": item.strip(),
                        "intervalo": intervalo.strip(),
                        "valor": valor.strip(),
                        "conselho": conselho.strip()
                    })

    return dados_extraidos
