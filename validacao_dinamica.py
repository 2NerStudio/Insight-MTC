import re
import logging
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Pt

logging.basicConfig(level=logging.INFO)

def extrair_parametros_valores(pdf_path):
    """
    Extrai texto do PDF e parseia para obter sistemas, itens, intervalos normais, valores reais e conselhos.
    Retorna lista de dicts: [{'sistema': str, 'item': str, 'normal_min': float, 'normal_max': float, 'valor_real': float, 'conselhos': str}]
    """
    try:
        reader = PdfReader(pdf_path)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() + "\n"

        # Normaliza texto: remove quebras extras, substitui vírgulas por pontos para floats
        texto_completo = re.sub(r'\s+', ' ', texto_completo).replace(',', '.')
        
        dados = []
        sistema_atual = None
        linhas = texto_completo.splitlines()
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            # Detecta sistema (cabeçalhos como "Cardiovascular e Cerebrovascular")
            if re.match(r'^[A-Z][a-z]+\s', linha) and 'Função' in linha or 'Índice' in linha or 'Coeficiente' in linha:
                sistema_atual = linha
                continue
            
            # Padrão para item: "Item intervalo_min - intervalo_max valor_real Conselhos..."
            match = re.match(r'(.+?)\s+(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s+(\d+\.?\d*)\s+(.*)', linha)
            if match:
                item = match.group(1).strip()
                normal_min = float(match.group(2))
                normal_max = float(match.group(3))
                valor_real = float(match.group(4))
                conselhos = match.group(5).strip()
                
                # Corrige se min > max (inverte)
                if normal_min > normal_max:
                    normal_min, normal_max = normal_max, normal_min
                
                dados.append({
                    'sistema': sistema_atual,
                    'item': item,
                    'normal_min': normal_min,
                    'normal_max': normal_max,
                    'valor_real': valor_real,
                    'conselhos': conselhos
                })
        
        if not dados:
            raise ValueError("Nenhum dado parseado do PDF. Verifique o formato.")
        
        logging.info(f"Extraídos {len(dados)} itens do PDF.")
        return dados
    
    except Exception as e:
        logging.error(f"Erro na extração: {str(e)}")
        raise

def validar_parametros(dados):
    """
    Valida cada item comparando valor_real com [normal_min, normal_max].
    Retorna lista de anomalias: [{'item': str, 'valor_real': float, 'status': 'abaixo'/'acima', 'normal_min': float, 'normal_max': float, 'conselhos': str}]
    """
    anomalias = []
    for d in dados:
        if not isinstance(d['valor_real'], (int, float)) or not isinstance(d['normal_min'], (int, float)) or not isinstance(d['normal_max'], (int, float)):
            continue  # Ignora inválidos
        
        if d['valor_real'] < d['normal_min']:
            status = 'abaixo'
        elif d['valor_real'] > d['normal_max']:
            status = 'acima'
        else:
            continue
        
        anomalias.append({
            'item': d['item'],
            'valor_real': d['valor_real'],
            'status': status,
            'normal_min': d['normal_min'],
            'normal_max': d['normal_max'],
            'conselhos': d['conselhos']
        })
    
    logging.info(f"Encontradas {len(anomalias)} anomalias.")
    return anomalias

def gerar_relatorio(pdf_path, nome_terapeuta, registro_terapeuta, output_path):
    """
    Gera um DOCX com relatório de anomalias e dados completos.
    """
    try:
        dados = extrair_parametros_valores(pdf_path)  # Re-extrai para consistência
        anomalias = validar_parametros(dados)
        
        doc = Document()
        doc.add_heading('Relatório de Anomalias - MTC Insight', 0)
        
        # Cabeçalho terapeuta
        p = doc.add_paragraph()
        p.add_run(f"Terapeuta: {nome_terapeuta}\nRegistro: {registro_terapeuta}\n").bold = True
        
        # Seção de Anomalias
        doc.add_heading('Anomalias Detectadas', level=1)
        if not anomalias:
            doc.add_paragraph('Nenhuma anomalia encontrada. Todos os parâmetros estão normais.')
        else:
            for a in anomalias:
                doc.add_paragraph(
                    f"- {a['item']}: {a['valor_real']} ({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})\n"
                    f"  Conselhos: {a['conselhos']}",
                    style='List Bullet'
                )
        
        # Seção de Dados Completos (para referência)
        doc.add_heading('Dados Extraídos Completos', level=1)
        for d in dados:
            doc.add_paragraph(
                f"Sistema: {d['sistema']}\nItem: {d['item']}\nNormal: {d['normal_min']}–{d['normal_max']}\nValor Real: {d['valor_real']}\nConselhos: {d['conselhos']}\n",
                style='Normal'
            )
        
        doc.save(output_path)
        logging.info(f"Relatório gerado em {output_path}")
    
    except Exception as e:
        logging.error(f"Erro na geração do relatório: {str(e)}")
        raise