import sys
import pdfplumber
from docx import Document

# Dicionário de parâmetros (agora com intervalos como chaves)
PARAMETROS = {
    (48.264, 65.371): "Viscosidade do sangue",
    (56.749, 67.522): "Cristal de colesterol",
    (1.672, 1.978): "Elasticidade vascular",
    (0.708, 1.942): "Elasticidade dos vasos sanguíneos do cérebro",
    (6.138, 21.396): "Situação do fornecimento de sangue ao tecido cerebral",
    (59.847, 65.234): "Coeficiente de secreção de pepsina",
    (58.425, 61.213): "Coeficiente das funções peristálticas gástricas",
    (3.572, 6.483): "Coeficiente das funções de absorção do intestino delgado",
    (116.34, 220.62): "Metabolismo de proteínas",
    (0.713, 0.992): "Função de produção de energia",
    (0.097, 0.419): "Teor de gordura do fígado",
    (126, 159): "Globulina do soro sanguíneo (A/G)",
    (2.845, 4.017): "Insulina",
    (3.210, 6.854): "Polipeptídeo pancreático (PP)",
    (2.762, 5.424): "Urobilinogênio",
    (1.435, 1.987): "Ácido úrico",
    (3348, 3529): "Atividade pulmonar VC",
    (4301, 4782): "Capacidade pulmonar total TLC",
    (143.37, 210.81): "Fornecimento de sangue ao cérebro",
    (86.73, 180.97): "Coeficiente de oestecelastos",
    (421, 490): "Calcificação coluna cervical",
    (2.967, 3.528): "Coeficiente de secreção de insulina",
    (59.786, 65.424): "Capacidade de reação física",
    (33.967, 37.642): "Falta de água",
    (0.209, 0.751): "Bebida estimulante",
    (0.124, 0.453): "Tabaco/nicotina e outros",
    (1.219, 3.021): "Cálcio",
    (1.151, 1.847): "Ferro",
    (1.143, 1.989): "Zinco",
    (0.847, 2.045): "Selênio",
    (0.474, 0.749): "Cobre",
    (0.497, 0.879): "Manganês",
    (2.462, 5.753): "Níquel",
    (1.954, 4.543): "Fidor",
    (1.425, 5.872): "Silício",
    (3.296, 8.840): "Estrogênio",
    (4.886, 8.931): "Gonadotrofina",
    (3.142, 7.849): "Prolactina",
    (6.818, 16.743): "Progesterona",
    (2.845, 4.017): "Coeficiente de cervicite",
    (0.124, 3.453): "Índice dos radicais livres da pele",
    (4.471, 6.079): "Índice de colágeno da pele",
    (14.477, 21.348): "Índice de oleosidade da pele",
    (1.035, 3.230): "Índice de imunidade da pele",
    (2.717, 3.512): "Índice de elasticidade da pele",
    (0.842, 1.858): "Índice de queratinócitos da pele",
    (2.954, 5.543): "Índice de secreção da tireóide",
    (2.845, 4.017): "Índice de secreção da paratireóide",
    (2.412, 2.974): "Índice de secreção da glândula supra-renal",
    (2.163, 7.340): "Índice de secreção da pituitária",
    (4.111, 18.741): "Índice de imunidade da mucosa",
    (133.437, 140.470): "Índice de linfonodo",
    (0.124, 0.453): "Índice de imunidade das amígdalas",
    (34.367, 35.642): "Índice do baço",
    (0.202, 0.991): "Coeficiente de fibrosidade da glândula mamária",
    (0.713, 0.992): "Coeficiente de mastite aguda",
    (1.684, 4.472): "Coeficiente de distúrbios endócrinos",
    (0.346, 0.401): "Vitamina A",
    (14.477, 21.348): "Vitamina B3",
    (4.826, 6.013): "Vitamina E",
    (0.253, 0.659): "Lisina",
    (1.213, 3.709): "Triptofano",
    (0.422, 0.817): "Treonina",
    (2.012, 4.892): "Valina",
    (0.433, 0.796): "Fosfatase alcalina óssea",
    (0.525, 0.817): "Osteocalcina",
    (0.432, 0.826): "Linha epifisária",
    (0.510, 3.109): "Bolsas sob os olhos",
    (2.031, 3.107): "Colágeno das rugas nos olhos",
    (0.233, 0.559): "Afrouxamento e queda",
    (2.017, 5.157): "Fadiga visual",
    (0.052, 0.643): "Chumbo",
    (0.013, 0.336): "Mercúrio",
    (0.153, 0.621): "Arsênico",
    (0.192, 0.412): "Alumínio",
    (0.431, 1.329): "Índice de alergia a medicamentos",
    (0.842, 1.643): "Fibra química",
    (0.543, 1.023): "Índice de alergia a poeira",
    (0.717, 1.486): "Alergia a corante de tintas cabelo",
    (0.124, 1.192): "Índice alergia de contato",
    (2.074, 3.309): "Nicotinamida",
    (0.831, 1.588): "Coenzima Q10",
    (1.992, 3.713): "Coeficiente de metabolismo anormal de lipidos",
    (1.341, 1.991): "Coeficiente de conteúdo anormal de triglicerídeos",
    (6.352, 8.325): "Colágeno - Olhos",
    (3.586, 4.337): "Circulação de sangue do coração e do cérebro",
    (3.376, 4.582): "Sistema imunologico",
    (6.552, 8.268): "Tecido muscular",
    (6.338, 8.368): "Metabolismo da gordura",
    (6.256, 8.682): "Esqueleto",
    (0.679, 1.324): "Hormona luteinizante(LH)",
    (0.327, 0.937): "Meridiano baco/pancreas tai yn do pe",
    (4.832, 5.147): "Meridiano da Bexiga Tai Yang do Pé",
    (1.338, 1.672): "Pericárdio",
    (1.554, 1.988): "Meridiano da Vesícula Billar Shao Yang do Pé",
    (11.719, 18.418): "Ren Mai",
    (0.316, 0.401): "Coeficiente da onda de pulso K",
    (5.017, 5.597): "Pressão do oxigênio do sangue cerebrovascular (PaO2)",
    (1.449, 2.246): "Lipoproteína de alta densidade (HDL-C)",
    (13.012, 17.291): "Complexo imunológico circulatório (CIC)",
    (6.326, 8.018): "Taxa de sedimentação",
    (5.769, 7.643): "Índice imunitário celular",
    (6.424, 8.219): "Índice de imunidade humoral",
    (1.845, 3.241): "Dor",
    (2.155, 4.031): "Medo",
    (2.471, 3.892): "Neutralidade",
    (2.216, 4.094): "Vontade",
    (1.668, 4.053): "Aceitação",
    (1.352, 3.436): "Razão",
    (2.138, 3.754): "Amor",
    (4.126, 6.045): "Volume inspiratório(TI)",
    (5.147, 6.219): "Capacidade residual funcional(FRC)",
    (3.121, 3.853): "Índice esfingolípide",
    (3.341, 4.214): "Índice de esfingomielilina",
    (3.112, 4.081): "Índice lipossômico",
    (2.224, 3.153): "Índice de ácidos gordos não saturados",
    (2.144, 3.238): "Índice de ácidos gordos essenciais"
}

def extrair_valores_do_pdf(caminho_pdf):
    """
    Extrai a terceira coluna (intervalo normal) para identificar o parâmetro
    e a quarta coluna (valor real) para comparação.
    """
    dados = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            tabelas = page.extract_tables()
            
            for tabela in tabelas:
                for linha in tabela:
                    if len(linha) >= 4:
                        intervalo_normal = linha[2].strip()  # Terceira coluna
                        valor_real = linha[3].strip()       # Quarta coluna
                        
                        # Limpa e formata os valores
                        valor_real = valor_real.replace(",", ".")
                        intervalo_normal = intervalo_normal.replace(",", ".")
                        
                        # Extrai mínimo e máximo do intervalo (ex: "48.264 - 65.371")
                        if " - " in intervalo_normal:
                            minimo, maximo = map(float, intervalo_normal.split(" - "))
                            
                            # Identifica o nome do parâmetro com base no intervalo
                            parametro = PARAMETROS.get((minimo, maximo), "Desconhecido")
                            
                            if valor_real.replace(".", "", 1).isdigit():
                                dados.append({
                                    "parametro": parametro,
                                    "valor_real": float(valor_real),
                                    "normal_min": minimo,
                                    "normal_max": maximo
                                })
    
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
            "Relatório de Anomalias (Identificação por Intervalo Normal)",
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