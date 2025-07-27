import re
import logging
import pdfplumber
from docx import Document
from difflib import get_close_matches  # Para correção baseada em similaridade

logging.basicConfig(level=logging.INFO)

# Lista de referência da tabela original para correção pós-parsing (baseada no seu input inicial)
REFERENCIA_SISTEMAS = [
    "Cardiovascular e Cerebrovascular", "Função Gastrointestinal", "Função do Fígado",
    "Grande Função do Intestino", "Função da Vesícula Biliar", "Função Pancreática",
    "Função Renal", "Função Pulmonar", "Sistema Nervoso", "Densidade Mineral Óssea",
    "Índice de Crescimento Ósseo", "Minerais", "Vitaminas", "Aminoácidos", "Coenzima",
    "Ácido Graxo", "Sistema Endócrino", "Sistema Imunológico", "Tiroide", "Metais Pesados",
    "Alérgenos", "Obesidade", "Pele", "Olhos", "Colágeno", "Acupuntura", "Pulso do Coração e Cerebro",
    "Lipidos Sangue", "Ginecologia", "Seios"
]
REFERENCIA_ITENS = [  # Itens comuns para matching
    "Viscosidade do sangue", "Elasticidade dos vasos sanguíneos do cérebro", "Coeficiente de secreção de pepsina",
    "Metabolismo de proteínas", "Coeficiente de absorção do cólon", "Globulina do soro sanguíneo (A/G)",
    "Ácido biliar total do soro sanguíneo (TBA)", "Insulina", "Urobilinogênio", "Nitrogênio uréico",
    "Atividade pulmonar VC", "Resistência das vias aéreas RAM", "Condição das funções neurológicas",
    "Coeficiente de oesteoclastos", "Grau de hiperplasia óssea", "Linha epifisária", "Níquel", "Flúor",
    "Vitamina B6", "Vitamina B12", "Vitamina K", "Treonina", "Isoleucina", "Arginina", "Ácido pantotênico",
    "α-Ácido linolênico", "Índice de secreção da pituitária", "Índice do baço", "Tiroglobulina",
    "Cádmio", "Tálio", "Índice de alergia ao pólen", "Índice de alergia a poeira", "Alergia a acessorios de metal",
    "Índice alergia marisco", "Coeficiente de hiperinsulinemia", "Índice de imunidade da pele", "Afrouxamento e queda",
    "Edema", "Cabelo e pele", "Sistema imunologico", "Desintoxicação e metabolismo", "Sistema reprodutivo",
    "Meridiano do Intestino Grosso Yangming da Mão", "Meridiano do Coração Shao Yin da mão",
    "Meridiano da Bexiga Tai Yang do Pé", "Triplo Aquecedor Shao Yang da Mão", "Meridiano Governador",
    "Meridiano Vital", "Pulso (SV)", "Saturação do oxigênio do sangue cerebrovascular (Sa)",
    "Pressão do oxigênio do sangue cerebrovascular (PaO2)", "Colesterol total (TC)",
    "Lipoproteína de baixa densidade (LDL-C)", "Complexo imunológico circulatório (CIC)", "Progesterona",
    "Coeficiente de distúrbios endócrinos"
]

def extrair_parametros_valores(pdf_path):
    dados = []
    estado = 'buscando_sistema'
    sistema_atual = None
    item_acumulado = ""
    conselhos_acumulado = ""
    normal_min = None
    normal_max = None
    valor_real = None

    table_settings = {
        "vertical_strategy": "lines_strict",
        "horizontal_strategy": "lines_strict",
        "snap_tolerance": 5,
        "join_tolerance": 5,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings)
                for table in tables:
                    for row in table:
                        row = [re.sub(r'\*+', '', cell.strip()) if cell else "" for cell in row]
                        row_text = " ".join([r for r in row if r]).strip().replace(',', '.')
                        if not row_text:
                            continue

                        logging.info(f"Row extraída: {row_text}")

                        # Máquina de estados
                        if estado == 'buscando_sistema':
                            match_sistema = get_close_matches(row_text, REFERENCIA_SISTEMAS, n=1, cutoff=0.6)
                            if match_sistema and not re.search(r'\d', row_text):
                                sistema_atual = match_sistema[0]
                                estado = 'buscando_item'
                                continue

                        if estado in ['buscando_item', 'acumulando_conselhos']:
                            # Regex para item completo: texto até intervalo, valor, então conselhos
                            match = re.match(r'(.+?)\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)', row_text)
                            if match:
                                # Salva anterior se acumulado
                                if item_acumulado:
                                    dados.append(_criar_dado(sistema_atual, item_acumulado, conselhos_acumulado, normal_min, normal_max, valor_real))
                                # Novo item
                                item_acumulado = _corrigir_item(match.group(1).strip())
                                normal_min = float(match.group(2))
                                normal_max = float(match.group(3))
                                valor_real = float(match.group(4))
                                conselhos_acumulado = match.group(5).strip()
                                estado = 'acumulando_conselhos'
                                continue
                            else:
                                # Acumula em item ou conselhos
                                if estado == 'buscando_item':
                                    item_acumulado += " " + row_text
                                else:
                                    conselhos_acumulado += " " + row_text

                # Fallback texto plano
                if not tables:
                    texto = page.extract_text() or ""
                    linhas = re.split(r'\n', texto)
                    for linha in linhas:
                        linha = linha.strip().replace(',', '.')
                        match = re.match(r'(.+?)\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)', linha)
                        if match:
                            item = _corrigir_item(match.group(1).strip())
                            min_val = float(match.group(2))
                            max_val = float(match.group(3))
                            val = float(match.group(4))
                            cons = match.group(5).strip()
                            dados.append(_criar_dado(sistema_atual, item, cons, min_val, max_val, val))

        # Salva último
        if item_acumulado:
            dados.append(_criar_dado(sistema_atual, item_acumulado, conselhos_acumulado, normal_min, normal_max, valor_real))

        # Filtro final
        dados = [d for d in dados if d['item'] and d['normal_min'] is not None and d['valor_real'] is not None]

        if not dados:
            raise ValueError("Nenhum dado parseado.")

        logging.info(f"Extraídos {len(dados)} itens.")
        return dados

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        raise

def _corrigir_item(item):
    # Corrige com matching de referência
    match = get_close_matches(item, REFERENCIA_ITENS, n=1, cutoff=0.7)
    return match[0] if match else item

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

# validar_parametros e gerar_relatorio (com sistema no item)
def validar_parametros(dados):
    anomalias = []
    for d in dados:
        if d['valor_real'] is None:
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