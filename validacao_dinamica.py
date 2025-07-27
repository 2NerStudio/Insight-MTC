import re
import logging
import pdfplumber
from docx import Document

logging.basicConfig(level=logging.INFO)

def extrair_parametros_valores(pdf_path):
    """
    Extrai tabelas do PDF usando pdfplumber e parseia para obter sistemas, itens, intervalos normais, valores reais e conselhos.
    Retorna lista de dicts: [{'sistema': str, 'item': str, 'normal_min': float, 'normal_max': float, 'valor_real': float, 'conselhos': str}]
    """
    dados = []
    sistema_atual = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extrai tabelas da página
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Ignora linhas vazias ou cabeçalhos
                        row = [cell.strip() if cell else "" for cell in row]
                        if not any(row):
                            continue

                        # Detecta sistema: linhas com 1-2 células, sem números, parecendo cabeçalhos
                        if len(row) <= 2 and not re.search(r'\d', row[0][:20]) and re.search(r'(Função|Índice|Coeficiente|Sistema|Meridiano|Pulso)', row[0]):
                            sistema_atual = row[0]
                            continue

                        # Assume estrutura de 5 colunas: SISTEMA (opcional), ITEM, INTERVALO, VALOR, CONSELHOS
                        # Mas como pode variar, usa posições flexíveis
                        if len(row) >= 4:
                            item = row[1] if len(row) > 1 else ""
                            intervalo = row[2] if len(row) > 2 else ""
                            valor_str = row[3] if len(row) > 3 else ""
                            conselhos = " ".join(row[4:]) if len(row) > 4 else ""

                            # Parseia intervalo: "min - max"
                            match_intervalo = re.match(r'(\d+[.,]?\d*)\s*-\s*(\d+[.,]?\d*)', intervalo.replace(',', '.'))
                            if not match_intervalo:
                                continue
                            normal_min = float(match_intervalo.group(1))
                            normal_max = float(match_intervalo.group(2))

                            # Parseia valor real
                            valor_str = valor_str.replace(',', '.')
                            match_valor = re.match(r'\d+[.]?\d*', valor_str)
                            if not match_valor:
                                continue
                            valor_real = float(match_valor.group(0))

                            # Corrige min > max
                            if normal_min > normal_max:
                                normal_min, normal_max = normal_max, normal_min

                            dados.append({
                                'sistema': sistema_atual or 'Desconhecido',
                                'item': item,
                                'normal_min': normal_min,
                                'normal_max': normal_max,
                                'valor_real': valor_real,
                                'conselhos': conselhos
                            })

                # Fallback: se não houver tabelas, tenta extrair texto plano
                if not tables:
                    texto = page.extract_text()
                    if texto:
                        # Usa parsing de texto plano similar ao anterior (para robustez)
                        linhas = texto.splitlines()
                        for linha in linhas:
                            linha = linha.strip().replace(',', '.')
                            match = re.match(r'(.+?)\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)', linha)
                            if match:
                                item = match.group(1)
                                normal_min = float(match.group(2))
                                normal_max = float(match.group(3))
                                valor_real = float(match.group(4))
                                conselhos = match.group(5)
                                if normal_min > normal_max:
                                    normal_min, normal_max = normal_max, normal_min
                                dados.append({
                                    'sistema': sistema_atual or 'Desconhecido',
                                    'item': item,
                                    'normal_min': normal_min,
                                    'normal_max': normal_max,
                                    'valor_real': valor_real,
                                    'conselhos': conselhos
                                })

        if not dados:
            raise ValueError("Nenhum dado parseado do PDF. Pode ser um PDF baseado em imagens ou formato não suportado. Tente depurar o texto extraído ou adicione OCR.")

        logging.info(f"Extraídos {len(dados)} itens do PDF.")
        return dados

    except Exception as e:
        logging.error(f"Erro na extração: {str(e)}")
        raise

# Funções validar_parametros e gerar_relatorio (iguais ao anterior, com pequenos ajustes para robustez)
def validar_parametros(dados):
    anomalias = []
    for d in dados:
        if 'valor_real' not in d or 'normal_min' not in d or 'normal_max' not in d:
            continue
        try:
            valor = float(d['valor_real'])
            min_val = float(d['normal_min'])
            max_val = float(d['normal_max'])
        except ValueError:
            continue

        if valor < min_val:
            status = 'abaixo'
        elif valor > max_val:
            status = 'acima'
        else:
            continue

        anomalias.append({
            'item': d.get('item', 'Desconhecido'),
            'valor_real': valor,
            'status': status,
            'normal_min': min_val,
            'normal_max': max_val,
            'conselhos': d.get('conselhos', 'N/A')
        })

    logging.info(f"Encontradas {len(anomalias)} anomalias.")
    return anomalias

def gerar_relatorio(pdf_path, nome_terapeuta, registro_terapeuta, output_path):
    try:
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
                f"Sistema: {d.get('sistema', 'N/A')}\nItem: {d.get('item', 'N/A')}\nNormal: {d.get('normal_min', 'N/A')}–{d.get('normal_max', 'N/A')}\nValor: {d.get('valor_real', 'N/A')}\nConselhos: {d.get('conselhos', 'N/A')}\n"
            )
        
        doc.save(output_path)
        logging.info(f"Relatório gerado em {output_path}")
    
    except Exception as e:
        logging.error(f"Erro na geração: {str(e)}")
        raise

# OPCIONAL: Para PDFs com imagens (OCR) - descomente e instale pytesseract e pdf2image se necessário
# import pytesseract
# from pdf2image import convert_from_path
# def extrair_texto_com_ocr(pdf_path):
#     images = convert_from_path(pdf_path)
#     texto = ""
#     for image in images:
#         texto += pytesseract.image_to_string(image) + "\n"
#     return texto
# # Então, no extrair_parametros_valores, se pdfplumber falhar, chame extrair_texto_com_ocr e parseie o texto.