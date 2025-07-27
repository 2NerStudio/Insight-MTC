import re
import logging
import pdfplumber
from docx import Document
from difflib import get_close_matches
from pdf2image import convert_from_path
import pytesseract

# Configure o caminho do Tesseract (ajuste para o seu sistema)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Exemplo para Linux/Mac; para Windows: r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(level=logging.INFO)

# Listas de referência expandidas para matching (baseadas na sua tabela original)
REFERENCIA_SISTEMAS = [
    "Cardiovascular e Cerebrovascular", "Função Gastrointestinal", "Função do Fígado",
    "Grande Função do Intestino", "Função da Vesícula Biliar", "Função Pancreática",
    "Função Renal", "Função Pulmonar", "Sistema Nervoso", "Densidade Mineral Óssea",
    "Índice de Crescimento Ósseo", "Minerais", "Vitaminas", "Aminoácidos", "Coenzima",
    "Ácido Graxo", "Sistema Endócrino", "Sistema Imunológico", "Tiroide", "Metais Pesados",
    "Alérgenos", "Obesidade", "Pele", "Olhos", "Colágeno", "Acupuntura", "Pulso do Coração e Cerebro",
    "Lipidos Sangue", "Ginecologia", "Seios", "Sistema reprodutivo", "Desintoxicação e metabolismo",
    "Sistema imunologico", "Cabelo e pele"
]

REFERENCIA_ITENS = [
    "Viscosidade do sangue", "Elasticidade dos vasos sanguíneos do cérebro", "Coeficiente de secreção de pepsina",
    "Metabolismo de proteínas", "Coeficiente de absorção do cólon", "Globulina do soro sanguíneo (A/G)",
    "Ácido biliar total do soro sanguíneo (TBA)", "Insulina", "Urobilinogênio", "Nitrogênio uréico",
    "Atividade pulmonar VC", "Resistência das vias aéreas RAM", "Condição das funções neurológicas",
    "Fornecimento de sangue ao cérebro", "Coeficiente de oesteoclastos", "Grau de hiperplasia óssea",
    "Linha epifisária", "Níquel", "Flúor", "Vitamina B6", "Vitamina B12", "Vitamina K", "Treonina",
    "Isoleucina", "Arginina", "Ácido pantotênico", "α-Ácido linolênico", "Índice de secreção da pituitária",
    "Índice do baço", "Tiroglobulina", "Cádmio", "Tálio", "Índice de alergia ao pólen",
    "Índice de alergia a poeira", "Alergia a acessorios de metal", "Índice alergia marisco",
    "Coeficiente de hiperinsulinemia", "Índice de imunidade da pele", "Afrouxamento e queda", "Edema",
    "Cabelo e pele", "Sistema imunologico", "Desintoxicação e metabolismo", "Sistema reprodutivo",
    "Meridiano do Intestino Grosso Yangming da Mão", "Meridiano do Coração Shao Yin da mão",
    "Meridiano da Bexiga Tai Yang do Pé", "Triplo Aquecedor Shao Yang da Mão", "Meridiano Governador",
    "Meridiano Vital", "Pulso (SV)", "Saturação do oxigênio do sangue cerebrovascular (Sa)",
    "Pressão do oxigênio do sangue cerebrovascular (PaO2)", "Colesterol total (TC)",
    "Lipoproteína de baixa densidade (LDL-C)", "Complexo imunológico circulatório (CIC)", "Progesterona",
    "Coeficiente de distúrbios endócrinos"
]

def extrair_parametros_valores(pdf_path):
    # Passo 1: Extrai texto completo (tenta texto nativo, fallback para OCR se vazio)
    texto_completo = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texto_completo += page_text + "\n"
    
    if len(texto_completo.strip()) < 100:  # Se texto nativo falhar (ex: PDF imagem), usa OCR
        logging.info("Texto nativo insuficiente - usando OCR.")
        images = convert_from_path(pdf_path)
        for image in images:
            texto_completo += pytesseract.image_to_string(image, lang='por') + "\n"  # 'por' para português, ajuste se necessário

    texto_completo = re.sub(r'\s+', ' ', texto_completo).replace(',', '.').strip()
    logging.info(f"Texto extraído (primeiros 500 chars): {texto_completo[:500]}")

    # Passo 2: Parsing com máquina de estados
    dados = []
    sistema_atual = None
    item_atual = None
    conselhos_atual = ""
    linhas = texto_completo.splitlines()

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # Detecta sistema
        match_sistema = get_close_matches(linha, REFERENCIA_SISTEMAS, n=1, cutoff=0.7)
        if match_sistema and not re.search(r'\d', linha[:30]):
            if item_atual:  # Salva anterior
                dados.append(_criar_dado(sistema_atual, item_atual, conselhos_atual))
            sistema_atual = match_sistema[0]
            item_atual = None
            conselhos_atual = ""
            continue

        # Detecta item: nome + min - max + valor + início de conselhos
        match = re.match(r'(.+?)\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(\d+\.?\d*)\s*(.*)', linha)
        if match:
            if item_atual:  # Salva anterior
                dados.append(_criar_dado(sistema_atual, item_atual, conselhos_atual))
            item_raw = match.group(1).strip()
            item_atual = get_close_matches(item_raw, REFERENCIA_ITENS, n=1, cutoff=0.7)
            item_atual = item_atual[0] if item_atual else item_raw
            normal_min = float(match.group(2))
            normal_max = float(match.group(3))
            valor_real = float(match.group(4))
            conselhos_atual = match.group(5).strip()
            # Salva imediatamente com valores
            dados.append(_criar_dado(sistema_atual, item_atual, conselhos_atual, normal_min, normal_max, valor_real))
            conselhos_atual = ""  # Reseta para acumulação
            continue

        # Acumula conselhos se há item atual
        if item_atual:
            conselhos_atual += " " + linha

    # Salva último
    if item_atual:
        dados.append(_criar_dado(sistema_atual, item_atual, conselhos_atual))

    # Filtro: Remove inválidos (ex: min/max absurdos ou itens vazios)
    dados = [d for d in dados if d['item'] and d['normal_min'] <= d['normal_max'] and d['valor_real'] is not None]

    if not dados:
        raise ValueError("Nenhum dado parseado do PDF. Verifique o formato ou tente OCR manual.")

    logging.info(f"Extraídos {len(dados)} itens válidos.")
    return dados

def _criar_dado(sistema, item, conselhos, min_val=None, max_val=None, valor=None):
    if min_val is not None and max_val is not None and min_val > max_val:
        min_val, max_val = max_val, min_val
    return {
        'sistema': sistema or 'Desconhecido',
        'item': item,
        'normal_min': min_val,
        'normal_max': max_val,
        'valor_real': valor,
        'conselhos': conselhos.strip()
    }

def validar_parametros(dados):
    anomalias = []
    seen = set()  # Evita duplicatas
    for d in dados:
        key = (d['item'], d['valor_real'])
        if key in seen:
            continue
        seen.add(key)
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
    try:
        dados = extrair_parametros_valores(pdf_path)
        anomalias = validar_parametros(dados)
        
        doc = Document()
        doc.add_heading('Relatório de Anomalias - MTC Insight', 0)
        
        p = doc.add_paragraph()
        p.add_run(f"Terapeuta: {nome_terapeuta}\nRegistro: {registro_terapeuta}\n").bold = True
        
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