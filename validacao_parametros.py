# validacao_parametros.py

import sys
import pdfplumber
from io import BytesIO
from docx import Document

PARAMETROS = {
"Viscosidade do sangue": (48.264, 65.371),
"Cristal de colesterol": (56.749, 67.522),
"Elasticidade vascular": (1.672, 1.978),
"Elasticidade dos vasos sanguíneos do cérebro": (0.708, 1.942),
"Situação do fornecimento de sangue ao tecido cerebral": (6.138, 21.396),
"Coeficiente de secreção de pepsina": (59.847, 65.234),
"Coeficiente das funções peristálticas gástricas": (58.425, 61.213),
"Coeficiente das funções de absorção do intestino delgado": (3.572, 6.483),
"Metabolismo de proteínas": (116.34, 220.62),
"Função de produção de energia": (0.713, 0.992),
"Teor de gordura do fígado": (0.097, 0.419 ),
"Globulina do soro sanguíneo (A/G)": (126, 159),
"Insulina": (2.845, 4.017),
"Polipeptídeo pancreático (PP)": (3.210, 6.854),
"Urobilinogênio": (2.762, 5.424),
"Ácido úrico": (1.435, 1.987),
"Atividade pulmonar VC": (3348, 3529),
"Capacidade pulmonar total TLC": (4301, 4782),
"Fornecimento de sangue ao cérebro": (143.37, 210.81),
"Coeficiente de oestecelastos": (86.73, 180.97),
"Calcificação coluna cervical": (421, 490),
"Coeficiente de secreção de insulina": (2.967, 3.528),
"Capacidade de reação física": (59.786, 65.424),
"Falta de água": (33.967, 37.642),
"Bebida estimulante": (0.209, 0.751),
"Tabaco/nicotina e outros": (0.124, 0.453),
"Cálcio": (1.219, 3.021),
"Ferro": (1.151, 1.847),
"Zinco": (1.143, 1.989),
"Selênio": (0.847, 2.045),
"Cobre": (0.474, 0.749),
"Manganês": (0.497, 0.879),
"Níquel": (2.462, 5.753),
"Fidor": (1.954, 4.543),
"Silício": (1.425, 5.872),
"Estrogênio": (3.296, 8.840),
"Gonadotrofina": (4.886, 8.931),
"Prolactina": (3.142, 7.849),
"Progesterona": (6.818, 16.743),
"Coeficiente de cervicite": (2.845, 4.017),
"Índice dos radicais livres da pele": (0.124, 3.453),
"Índice de colágeno da pele": (4.471, 6.079),
"Índice de oleosidade da pele": (14.477, 21.348),
"Índice de imunidade da pele": (1.035, 3.230),
"Índice de elasticidade da pele": (2.717, 3.512),
"Índice de queratinócitos da pele": (0.842, 1.858),
"Índice de secreção da tireóide": (2.954, 5.543),
"Índice de secreção da paratireóide": (2.845, 4.017),
"Índice de secreção da glândula supra-renal": (2.412, 2.974),
"Índice de secreção da pituitária": (2.163, 7.340),
"Índice de imunidade da mucosa": (4.111, 18.741),
"Índice de linfonodo": (133.437, 140.470),
"Índice de imunidade das amígdalas": (0.124, 0.453),
"Índice do baço": (34.367, 35.642),
"Coeficiente de fibrosidade da glândula mamária": (0.202, 0.991),
"Coeficiente de mastite aguda": (0.713, 0.992),
"Coeficiente de distúrbios endócrinos": (1.684, 4.472),
"Vitamina A": (0.346, 0.401),
"Vitamina B3": (14.477, 21.348),
"Vitamina E": (4.826, 6.013),
"Lisina": (0.253, 0.659),
"Triptofano": (1.213, 3.709),
"Treonina": (0.422, 0.817),
"Valina": (2.012, 4.892),
"Fosfatase alcalina óssea": (0.433, 0.796),
"Osteocalcina": (0.525, 0.817),
"Linha epifisária": (0.432, 0.826),
"Bolsas sob os olhos": (0.510, 3.109),
"Colágeno das rugas nos olhos": (2.031, 3.107),
"Afrouxamento e queda": (0.233, 0.559),
"Fadiga visual": (2.017, 5.157),
"Chumbo": (0.052, 0.643),
"Mercúrio": (0.013, 0.336),
"Arsênico": (0.153, 0.621),
"Alumínio": (0.192, 0.412),
"Índice de alergia a medicamentos": (0.431, 1.329),
"Fibra química": (0.842, 1.643),
"Índice de alergia a poeira": (0.543, 1.023),
"Alergia a corante de tintas cabelo": (0.717, 1.486),
"Índice alergia de contato": (0.124, 1.192),
"Nicotinamida": (2.074, 3.309),
"Coenzima Q10": (0.831, 1.588),
"Coeficiente de metabolismo anormal de lipidos": (1.992, 3.713),
"Coeficiente de conteúdo anormal de triglicerídeos": (1.341, 1.991),
"Colágeno - Olhos": (6.352, 8.325),
"Circulação de sangue do coração e do cérebro": (3.586, 4.337),
"Sistema imunologico": (3.376, 4.582),
"Tecido muscular": (6.552, 8.268),
"Metabolismo da gordura": (6.338, 8.368),
"Esqueleto": (6.256, 8.682),
"Hormona luteinizante(LH)": (0.679, 1.324),
"Meridiano baco/pancreas tai yn do pe": (0.327, 0.937),
"Meridiano da Bexiga Tai Yang do Pé": (4.832, 5.147),
"Pericárdio": (1.338, 1.672),
"Meridiano da Vesícula Billar Shao Yang do Pé": (1.554, 1.988),
"Ren Mai": (11.719, 18.418),
"Coeficiente da onda de pulso K": (0.316, 0.401),
"Pressão do oxigênio do sangue cerebrovascular (PaO2)": (5.017, 5.597),
"Lipoproteína de alta densidade (HDL-C)": (1.449, 2.246),
"Complexo imunológico circulatório (CIC)": (13.012, 17.291),
"Taxa de sedimentação": (6.326, 8.018),
"Índice imunitário celular": (5.769, 7.643),
"Índice de imunidade humoral": (6.424, 8.219),
"Dor": (1.845, 3.241),
"Medo": (2.155, 4.031),
"Neutralidade": (2.471, 3.892),
"Vontade": (2.216, 4.094),
"Aceitação": (1.668, 4.053),
"Razão": (1.352, 3.436),
"Amor": (2.138, 3.754),
"Volume inspiratório(TI)": (4.126, 6.045),
"Capacidade residual funcional(FRC)": (5.147, 6.219),
"Índice esfingolípide": (3.121, 3.853),
"Índice de esfingomielilina": (3.341, 4.214),
"Índice lipossômico": (3.112, 4.081),
"Índice de ácidos gordos não saturados": (2.224, 3.153),
"Índice de ácidos gordos essenciais": (2.144, 3.238)
}

def extrair_valores_do_pdf(caminho_pdf):
    """
    Extrai os valores da 4ª coluna na ordem correta, com tratamento robusto
    """
    valores_reais = []
    comecar_coleta = False
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            # Configurações melhoradas para extração
            settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_y_tolerance": 10,
                "join_tolerance": 10
            }
            
            tabelas = page.extract_tables(table_settings=settings)
            
            for tabela in tabelas:
                for linha in tabela:
                    # Verifica se é o cabeçalho para iniciar coleta
                    if len(linha) > 1 and "Item de Teste" in (linha[1] or ""):
                        comecar_coleta = True
                        continue
                        
                    if comecar_coleta and len(linha) >= 4:
                        valor = (linha[3] or "").strip()
                        # Limpeza mais robusta do valor
                        valor = valor.replace(",", ".").replace(" ", "").replace("'", "")
                        if valor and valor.replace(".", "", 1).isdigit():
                            try:
                                valores_reais.append(float(valor))
                            except ValueError:
                                continue
    
    # Verificação crítica de quantidade
    if len(valores_reais) != len(PARAMETROS):
        print(f"Aviso: Esperados {len(PARAMETROS)} valores, encontrados {len(valores_reais)}")
    
    return dict(zip(PARAMETROS.keys(), valores_reais[:len(PARAMETROS)]))

def validar_valores(valores):
    """
    Validação rigorosa com tratamento de erros completo
    """
    anomalias = []
    
    for item, valor in valores.items():
        if item not in PARAMETROS:
            continue
            
        try:
            # Conversão segura para float
            valor_float = float(valor) if not isinstance(valor, float) else valor
            minimo, maximo = PARAMETROS[item]
            
            # Verificação de limites com tolerância numérica
            if abs(valor_float - minimo) < 0.0001 or abs(valor_float - maximo) < 0.0001:
                continue  # Considera valor igual ao limite como normal
                
            if valor_float < minimo:
                status = "Abaixo"
            elif valor_float > maximo:
                status = "Acima"
            else:
                continue
                
            anomalias.append({
                "item": item,
                "valor_real": valor_float,
                "status": status,
                "normal_min": minimo,
                "normal_max": maximo
            })
            
        except (TypeError, ValueError) as e:
            print(f"Erro ao validar {item}: {str(e)}")
            continue
    
    return anomalias

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        # 1) Extração com verificação
        valores = extrair_valores_do_pdf(pdf_path)
        if not valores:
            raise ValueError("Nenhum valor válido foi extraído do PDF")
            
        print(f"Total de valores extraídos: {len(valores)}/{len(PARAMETROS)}")
        
        # 2) Validação rigorosa
        anomalias = validar_valores(valores)
        
        # 3) Geração de relatório detalhado
        doc = Document()
        doc.add_heading('Relatório de Anomalias', level=1)
        doc.add_paragraph(f"Terapeuta: {terapeuta}\tRegistro: {registro}")
        
        if not anomalias:
            doc.add_paragraph("✅ Todos os parâmetros dentro da normalidade", style='Intense Quote')
        else:
            doc.add_paragraph(f"⚠️ Foram encontradas {len(anomalias)} anomalias:", style='Heading 2')
            
            tabela = doc.add_table(rows=1, cols=5)
            tabela.style = 'Light Shading'
            cabecalho = tabela.rows[0].cells
            cabecalho[0].text = 'Parâmetro'
            cabecalho[1].text = 'Valor'
            cabecalho[2].text = 'Status'
            cabecalho[3].text = 'Mínimo'
            cabecalho[4].text = 'Máximo'
            
            for anomalia in sorted(anomalias, key=lambda x: x['item']):
                celulas = tabela.add_row().cells
                celulas[0].text = anomalia['item']
                celulas[1].text = f"{anomalia['valor_real']:.3f}"
                celulas[2].text = anomalia['status']
                celulas[3].text = f"{anomalia['normal_min']}"
                celulas[4].text = f"{anomalia['normal_max']}"
        
        doc.save(output_path)
        print(f"Relatório gerado em: {output_path}")
        return True, output_path
        
    except Exception as e:
        print(f"Erro crítico: {str(e)}")
        return False, str(e)