import sys
import pdfplumber
from docx import Document

# Dicionário de parâmetros (chave = mínimo do intervalo)
PARAMETROS = {
    48.264: ("Viscosidade do sangue", (48.264, 65.371)),
    56.749: ("Cristal de colesterol", (56.749, 67.522)),
    1.672: ("Elasticidade vascular", (1.672, 1.978)),
    0.708: ("Elasticidade dos vasos sanguíneos do cérebro", (0.708, 1.942)),
    6.138: ("Situação do fornecimento de sangue ao tecido cerebral", (6.138, 21.396)),
    59.847: ("Coeficiente de secreção de pepsina", (59.847, 65.234)),
    58.425: ("Coeficiente das funções peristálticas gástricas", (58.425, 61.213)),
    3.572: ("Coeficiente das funções de absorção do intestino delgado", (3.572, 6.483)),
    116.34: ("Metabolismo de proteínas", (116.34, 220.62)),
    0.713: ("Função de produção de energia", (0.713, 0.992)),
    0.097: ("Teor de gordura do fígado", (0.097, 0.419)),
    126: ("Globulina do soro sanguíneo (A/G)", (126, 159)),
    2.845: ("Insulina", (2.845, 4.017)),
    3.210: ("Polipeptídeo pancreático (PP)", (3.210, 6.854)),
    2.762: ("Urobilinogênio", (2.762, 5.424)),
    1.435: ("Ácido úrico", (1.435, 1.987)),
    3348: ("Atividade pulmonar VC", (3348, 3529)),
    4301: ("Capacidade pulmonar total TLC", (4301, 4782)),
    143.37: ("Fornecimento de sangue ao cérebro", (143.37, 210.81)),
    86.73: ("Coeficiente de oestecelastos", (86.73, 180.97)),
    421: ("Calcificação coluna cervical", (421, 490)),
    2.967: ("Coeficiente de secreção de insulina", (2.967, 3.528)),
    59.786: ("Capacidade de reação física", (59.786, 65.424)),
    33.967: ("Falta de água", (33.967, 37.642)),
    0.209: ("Bebida estimulante", (0.209, 0.751)),
    0.124: ("Tabaco/nicotina e outros", (0.124, 0.453)),
    1.219: ("Cálcio", (1.219, 3.021)),
    1.151: ("Ferro", (1.151, 1.847)),
    1.143: ("Zinco", (1.143, 1.989)),
    0.847: ("Selênio", (0.847, 2.045)),
    0.474: ("Cobre", (0.474, 0.749)),
    0.497: ("Manganês", (0.497, 0.879)),
    2.462: ("Níquel", (2.462, 5.753)),
    1.954: ("Fidor", (1.954, 4.543)),
    1.425: ("Silício", (1.425, 5.872)),
    3.296: ("Estrogênio", (3.296, 8.840)),
    4.886: ("Gonadotrofina", (4.886, 8.931)),
    3.142: ("Prolactina", (3.142, 7.849)),
    6.818: ("Progesterona", (6.818, 16.743)),
    0.124: ("Índice dos radicais livres da pele", (0.124, 3.453)),
    4.471: ("Índice de colágeno da pele", (4.471, 6.079)),
    14.477: ("Índice de oleosidade da pele", (14.477, 21.348)),
    1.035: ("Índice de imunidade da pele", (1.035, 3.230)),
    2.717: ("Índice de elasticidade da pele", (2.717, 3.512)),
    0.842: ("Índice de queratinócitos da pele", (0.842, 1.858)),
    2.954: ("Índice de secreção da tireóide", (2.954, 5.543)),
    2.412: ("Índice de secreção da glândula supra-renal", (2.412, 2.974)),
    2.163: ("Índice de secreção da pituitária", (2.163, 7.340)),
    4.111: ("Índice de imunidade da mucosa", (4.111, 18.741)),
    133.437: ("Índice de linfonodo", (133.437, 140.470)),
    34.367: ("Índice do baço", (34.367, 35.642)),
    0.202: ("Coeficiente de fibrosidade da glândula mamária", (0.202, 0.991)),
    1.684: ("Coeficiente de distúrbios endócrinos", (1.684, 4.472)),
    0.346: ("Vitamina A", (0.346, 0.401)),
    4.826: ("Vitamina E", (4.826, 6.013)),
    0.253: ("Lisina", (0.253, 0.659)),
    1.213: ("Triptofano", (1.213, 3.709)),
    0.422: ("Treonina", (0.422, 0.817)),
    2.012: ("Valina", (2.012, 4.892)),
    0.433: ("Fosfatase alcalina óssea", (0.433, 0.796)),
    0.525: ("Osteocalcina", (0.525, 0.817)),
    0.432: ("Linha epifisária", (0.432, 0.826)),
    0.510: ("Bolsas sob os olhos", (0.510, 3.109)),
    2.031: ("Colágeno das rugas nos olhos", (2.031, 3.107)),
    0.233: ("Afrouxamento e queda", (0.233, 0.559)),
    2.017: ("Fadiga visual", (2.017, 5.157)),
    0.052: ("Chumbo", (0.052, 0.643)),
    0.013: ("Mercúrio", (0.013, 0.336)),
    0.153: ("Arsênico", (0.153, 0.621)),
    0.192: ("Alumínio", (0.192, 0.412)),
    0.431: ("Índice de alergia a medicamentos", (0.431, 1.329)),
    0.842: ("Fibra química", (0.842, 1.643)),
    0.543: ("Índice de alergia a poeira", (0.543, 1.023)),
    0.717: ("Alergia a corante de tintas cabelo", (0.717, 1.486)),
    2.074: ("Nicotinamida", (2.074, 3.309)),
    0.831: ("Coenzima Q10", (0.831, 1.588)),
    1.992: ("Coeficiente de metabolismo anormal de lipidos", (1.992, 3.713)),
    1.341: ("Coeficiente de conteúdo anormal de triglicerídeos", (1.341, 1.991)),
    6.352: ("Colágeno - Olhos", (6.352, 8.325)),
    3.586: ("Circulação de sangue do coração e do cérebro", (3.586, 4.337)),
    3.376: ("Sistema imunológico", (3.376, 4.582)),
    6.552: ("Tecido muscular", (6.552, 8.268)),
    6.338: ("Metabolismo da gordura", (6.338, 8.368)),
    6.256: ("Esqueleto", (6.256, 8.682)),
    0.679: ("Hormona luteinizante (LH)", (0.679, 1.324)),
    0.327: ("Meridiano baco/pancreas tai yn do pe", (0.327, 0.937)),
    4.832: ("Meridiano da Bexiga Tai Yang do Pé", (4.832, 5.147)),
    1.338: ("Pericárdio", (1.338, 1.672)),
    1.554: ("Meridiano da Vesícula Biliar Shao Yang do Pé", (1.554, 1.988)),
    11.719: ("Ren Mai", (11.719, 18.418)),
    0.316: ("Coeficiente da onda de pulso K", (0.316, 0.401)),
    5.017: ("Pressão do oxigênio do sangue cerebrovascular (PaO2)", (5.017, 5.597)),
    1.449: ("Lipoproteína de alta densidade (HDL-C)", (1.449, 2.246)),
    13.012: ("Complexo imunológico circulatório (CIC)", (13.012, 17.291)),
    6.326: ("Taxa de sedimentação", (6.326, 8.018)),
    5.769: ("Índice imunitário celular", (5.769, 7.643)),
    6.424: ("Índice de imunidade humoral", (6.424, 8.219)),
    1.845: ("Dor", (1.845, 3.241)),
    2.155: ("Medo", (2.155, 4.031)),
    2.471: ("Neutralidade", (2.471, 3.892)),
    2.216: ("Vontade", (2.216, 4.094)),
    1.668: ("Aceitação", (1.668, 4.053)),
    1.352: ("Razão", (1.352, 3.436)),
    2.138: ("Amor", (2.138, 3.754)),
    4.126: ("Volume inspiratório (TI)", (4.126, 6.045)),
    5.147: ("Capacidade residual funcional (FRC)", (5.147, 6.219)),
    3.121: ("Índice esfingolípide", (3.121, 3.853)),
    3.341: ("Índice de esfingomielilina", (3.341, 4.214)),
    3.112: ("Índice lipossômico", (3.112, 4.081)),
    2.224: ("Índice de ácidos gordos não saturados", (2.224, 3.153)),
    2.144: ("Índice de ácidos gordos essenciais", (2.144, 3.238))
}

def extrair_valores_do_pdf(caminho_pdf):
    """
    Extrai o mínimo do intervalo (Coluna 3) para identificar o parâmetro
    e o valor real (Coluna 4) para comparação.
    """
    dados = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            tabelas = page.extract_tables()
            
            for tabela in tabelas:
                for linha in tabela:
                    if len(linha) >= 4 and linha[2] and linha[3]:
                        intervalo_normal = linha[2].strip()  # Coluna 3
                        valor_real = linha[3].strip()       # Coluna 4
                        
                        # Limpa e formata os valores
                        valor_real = valor_real.replace(",", ".")
                        intervalo_normal = intervalo_normal.replace(",", ".")
                        
                        # Extrai o mínimo do intervalo (trata ambos os formatos)
                        if " - " in intervalo_normal:
                            partes = intervalo_normal.split(" - ")
                            minimo_str = partes[0]
                            
                            try:
                                minimo = float(minimo_str)
                                
                                # Identifica o parâmetro usando o mínimo como chave
                                if minimo in PARAMETROS:
                                    nome_parametro, (min_intervalo, max_intervalo) = PARAMETROS[minimo]
                                    
                                    # Converte o valor real para float
                                    if valor_real.replace(".", "", 1).isdigit():
                                        dados.append({
                                            "parametro": nome_parametro,
                                            "valor_real": float(valor_real),
                                            "normal_min": min_intervalo,
                                            "normal_max": max_intervalo
                                        })
                            except (ValueError, IndexError):
                                continue  # Ignora linhas com formatos inválidos
    
    return dados

def validar_valores(dados):
    """
    Compara o valor real com o intervalo normal.
    """
    anomalias = []
    for item in dados:
        valor_real = item["valor_real"]
        minimo = item["normal_min"]
        maximo = item["normal_max"]
        
        if valor_real < minimo:
            status = "Abaixo"
        elif valor_real > maximo:
            status = "Acima"
        else:
            continue  # Dentro do normal
        
        anomalias.append({
            "parametro": item["parametro"],
            "valor_real": valor_real,
            "status": status,
            "normal_min": minimo,
            "normal_max": maximo
        })
    
    return anomalias

def exportar_para_docx(texto, output_path):
    doc = Document()
    doc.add_paragraph(texto)
    doc.save(output_path)

def gerar_relatorio(pdf_path, terapeuta, registro, output_path="relatorio_anomalias.docx"):
    try:
        dados = extrair_valores_do_pdf(pdf_path)
        if not dados:
            raise ValueError("Nenhum dado válido extraído do PDF.")
        
        anomalias = validar_valores(dados)
        
        lines = [
            "Relatório de Anomalias (Identificação pelo Mínimo do Intervalo)",
            f"Terapeuta: {terapeuta}   Registro: {registro}",
            ""
        ]
        
        if not anomalias:
            lines.append("✅ Todos os parâmetros dentro da normalidade.")
        else:
            lines.append(f"⚠️ {len(anomalias)} anomalias encontradas:")
            for a in anomalias:
                lines.append(
                    f"• {a['parametro']}: {a['valor_real']:.3f}  "
                    f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
                )
        
        exportar_para_docx("\n".join(lines), output_path)
        print(f"✅ Relatório gerado: {output_path}")
        return True, output_path
    
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python script.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)
    
    sucesso, resultado = gerar_relatorio(sys.argv[1], sys.argv[2], sys.argv[3])
    if not sucesso:
        sys.exit(1)