import re
import logging
import pdfplumber
from docx import Document

logging.basicConfig(level=logging.INFO)

def extrair_parametros_valores(pdf_path):
    dados = []
    sistema_atual = None
    item_acumulado = ""
    conselhos_acumulado = ""

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "min_words_vertical": 3,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings)
                for table in tables:
                    for row in table:
                        # Limpa e junta células, removendo artifacts como "****"
                        row = [re.sub(r'\*+', '', cell.strip()) if cell else "" for cell in row]
                        row_text = " ".join(row).strip()
                        if not row_text:
                            continue

                        logging.info(f"Row extraída: {row_text}")  # Depuração

                        # Detecta sistema: linhas sem números, com palavras chave
                        if not re.search(r'\d', row_text) and re.search(r'(Função|Índice|Coeficiente|Sistema|Meridiano|Pulso|Cardiovascular)', row_text):
                            if item_acumulado and conselhos_acumulado:  # Só salva se houver acumulado válido
                                dado = _criar_dado(sistema_atual, item_acumulado, conselhos_acumulado)
                                if dado['normal_min'] is not None and dado['valor_real'] is not None:
                                    dados.append(dado)
                            sistema_atual = row_text
                            item_acumulado = ""
                            conselhos_acumulado = ""
                            continue

                        # Acumula para multi-linha: se não houver números, adiciona ao item ou conselhos
                        if not re.search(r'\d', row_text):
                            if item_acumulado:
                                conselhos_acumulado += " " + row_text
                            else:
                                item_acumulado += " " + row_text
                            continue

                        # Parseia linha completa com regex flexível para item longo, intervalo, valor, conselhos
                        match = re.match(r'(.*?)\s*(\d+[.,]?\d*)\s*-\s*(\d+[.,]?\d*)\s*(\d+[.,]?\d*)\s*(.*)', row_text.replace(',', '.'))
                        if match:
                            novo_item = match.group(1).strip()
                            try:
                                normal_min = float(match.group(2))
                                normal_max = float(match.group(3))
                                valor_real = float(match.group(4))
                            except ValueError:
                                logging.warning(f"Row ignorada: valores inválidos em {row_text}")
                                continue

                            novo_conselhos = match.group(5).strip()

                            # Salva acumulado anterior se existir
                            if item_acumulado:
                                dado = _criar_dado(sistema_atual, item_acumulado, conselhos_acumulado)
                                if dado['normal_min'] is not None and dado['valor_real'] is not None:
                                    dados.append(dado)

                            item_acumulado = novo_item
                            conselhos_acumulado = novo_conselhos
                            # Salva imediatamente o novo (já que tem valores)
                            dado = _criar_dado(sistema_atual, item_acumulado, conselhos_acumulado, normal_min, normal_max, valor_real)
                            if dado['normal_min'] is not None and dado['valor_real'] is not None:
                                dados.append(dado)
                            item_acumulado = ""  # Reseta após salvar
                            conselhos_acumulado = ""
                        else:
                            # Acumula em conselhos se não match
                            conselhos_acumulado += " " + row_text
                            logging.info(f"Acumulado em conselhos: {row_text}")

                # Fallback: texto plano se não houver tabelas
                if not tables:
                    texto = page.extract_text()
                    if texto:
                        linhas = re.split(r'\n', texto)
                        for linha in linhas:
                            linha = linha.strip().replace(',', '.')
                            match = re.match(r'(.*?)\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)', linha)
                            if match:
                                item = match.group(1).strip()
                                try:
                                    normal_min = float(match.group(2))
                                    normal_max = float(match.group(3))
                                    valor_real = float(match.group(4))
                                except ValueError:
                                    continue
                                conselhos = match.group(5).strip()
                                dado = _criar_dado(sistema_atual, item, conselhos, normal_min, normal_max, valor_real)
                                if dado['normal_min'] is not None and dado['valor_real'] is not None:
                                    dados.append(dado)

        # Salva o último acumulado, se válido
        if item_acumulado:
            dado = _criar_dado(sistema_atual, item_acumulado, conselhos_acumulado)
            if dado['normal_min'] is not None and dado['valor_real'] is not None:
                dados.append(dado)

        # Limpa dados inválidos
        dados = [d for d in dados if d['normal_min'] is not None and d['valor_real'] is not None]

        if not dados:
            raise ValueError("Nenhum dado parseado. Verifique o PDF.")

        logging.info(f"Extraídos {len(dados)} itens.")
        return dados

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        raise

def _criar_dado(sistema, item, conselhos, min_val=None, max_val=None, valor=None):
    if min_val is not None and max_val is not None and min_val > max_val:
        min_val, max_val = max_val, min_val
    return {
        'sistema': sistema or 'Desconhecido',
        'item': item,
        'normal_min': min_val,
        'normal_max': max_val,
        'valor_real': valor,
        'conselhos': conselhos
    }

# validar_parametros e gerar_relatorio permanecem iguais ao código anterior
def validar_parametros(dados):
    anomalias = []
    for d in dados:
        if 'valor_real' not in d or d['valor_real'] is None:
            continue
        valor = d['valor_real']
        min_val = d['normal_min']
        max_val = d['normal_max']

        if valor < min_val:
            status = 'abaixo'
        elif valor > max_val:
            status = 'acima'
        else:
            continue

        anomalias.append({
            'item': f"{d['sistema']}: {d['item']}",
            'valor_real': valor,
            'status': status,
            'normal_min': min_val,
            'normal_max': max_val,
            'conselhos': d['conselhos']
        })
    return anomalias

def gerar_relatorio(pdf_path, nome_terapeuta, registro_terapeuta, output_path):
    dados = extrair_parametros_valores(pdf_path)
    anomalias = validar_parametros(dados)
    
    doc = Document()
    doc.add_heading('Relatório de Anomalias - MTC Insight', 0)
    
    p = doc.add_paragraph()
    p.add_run(f"Terapeuta: {nome_terapeuta}\nRegistro: {registro_terapeuta}\n").bold = True
    
    doc.add_heading('Anomalias Detectadas', level=1)
    if not anomalias:
        doc.add_paragraph('Nenhuma anomalia encontrada.')
    else:
        for a in anomalias:
            doc.add_paragraph(
                f"- {a['item']}: {a['valor_real']} ({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})\n"
                f"  Conselhos: {a['conselhos']}"
            )
    
    doc.add_heading('Dados Completos', level=1)
    for d in dados:
        doc.add_paragraph(
            f"Sistema: {d['sistema']}\nItem: {d['item']}\nNormal: {d['normal_min']}–{d['normal_max']}\nValor: {d['valor_real']}\nConselhos: {d['conselhos']}\n"
        )
    
    doc.save(output_path)