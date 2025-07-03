import pdfplumber

def extrair_dados_do_pdf(arquivo_streamlit):
    dados_extraidos = []

    with pdfplumber.open(arquivo_streamlit) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    if linha[0] == "Item" or None in linha:
                        continue

                    item, intervalo, valor, conselho = linha

                    dados_extraidos.append({
                        "item": item.strip(),
                        "intervalo": intervalo.strip(),
                        "valor": valor.strip(),
                        "conselho": conselho.strip()
                    })

    return dados_extraidos
