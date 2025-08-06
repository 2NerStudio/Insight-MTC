import re
from typing import Dict, List, Optional, Tuple
import pdfplumber
from docx import Document
import os
from difflib import SequenceMatcher

# Funções utilitárias
def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\r", " ").replace(",", ".")).strip()

def extract_numbers(text: str) -> List[float]:
    matches = re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)
    return [float(m.replace(",", ".")) for m in matches]

def is_header_line(line: str) -> bool:
    line_lower = line.lower()
    invalid_keywords = [
        "os resultados do teste apenas para referência", "cartão do relatório de análise", "nome: exemplo", "sexo: feminino", "idade: 31", "figura: peso padrão", "período do teste", "resultados reais do teste", "conselho de peritos", "real"
    ]
    return any(kw in line_lower for kw in invalid_keywords) or len(line) < 20 or not re.search(r'[a-zA-Z]{5,}', line)

def is_valid_name(name: str) -> bool:
    name_lower = name.lower()
    invalid_starts = ['(', ')', '-', 'do', 'da', 'de', 'e', 'o', 'a']  # Evita fragmentos
    invalid_ends = [' de', ' do', ' da', ' ncia', ' o', '-']
    if name_lower.startswith(tuple(invalid_starts)) or name_lower.endswith(tuple(invalid_ends)):
        return False
    char_count = len(re.sub(r'[^a-zA-Z]', '', name))
    word_count = len(name.split())
    if char_count < 10 or char_count > 60 or word_count > 8:
        return False
    # Lista branca de termos válidos (baseada no texto original)
    valid_terms = [
        "viscosidade", "cristal de colesterol", "gordura do sangue", "resistência vascular", "elasticidade vascular", "demanda de sangue", "consumo de oxigênio", "volume sistólico", "impedância do bombeamento", "força de bombeamento", "elasticidade da artéria", "pressão de perfusão", "elasticidade dos vasos", "situação do fornecimento", "coeficiente das funções", "metabolismo de proteínas", "função de produção", "função de desintoxicação", "função de secreção", "teor de gordura", "globulin a do soro", "bilirrubina total", "fosfatase alcalina", "ácido biliar total", "bilirrubina", "insulina", "polipeptídeo pancreático", "glucagon", "urobilinogênio", "ácido úrico", "nitrogênio uréico", "proteína urinária", "atividade pulmonar", "capacidade pulmonar total", "resistência das vias", "teor de oxigênio", "fornecimento de sangue", "arterioesclerose cerebral", "condição das funções", "indicador de depressão", "indicador de memória", "coeficiente de oesteoclastos", "perda de cálcio", "grau de hiperplasia", "grau de osteoporose", "densidade óssea", "calcificação coluna", "coeficiente de hiperplasia", "coeficiente de osteoporose", "coeficiente de reumatismo", "coeficiente de secreção", "coeficiente de açúcar", "capacidade de reação", "capacidade cerebral", "falta de água", "hipóxia", "ph", "bebida estimulante", "radiação eletromagnética", "tabaco/nicotina", "resíduos tóxicos", "cálcio", "ferro", "zinco", "selênio", "fósforo", "potássio", "magnésio", "cobre", "cobalto", "manganês", "iodo", "níquel", "flúor", "molibdênio", "vanádio", "estanho", "silício", "estrôncio", "boro", "estrogênio", "gonadotrofina", "prolactina", "progesterona", "coeficiente de vaginite", "coeficiente de inflamação", "coeficiente de anexite", "coeficiente de cervicite", "coeficiente de cisto", "índice dos radicais", "índice de colágeno", "índice de oleosidade", "índice de imunidade", "índice de hidratação", "perda de hidratação", "índice de dilatação", "índice de elasticidade", "índice de melanina", "índice de queratinócitos", "índice de secreção", "índice gonadal", "índice de linfonodo", "índice de imunidade", "índice do baço", "índice do timo", "coeficiente de fibrosidade", "mastite aguda", "mastite crônica", "distúrbios endócrinos", "fibroadenoma", "vitamina", "lisina", "triptofano", "fenilalanina", "metionina", "treonina", "isoleucina", "leucina", "valina", "histidina", "arginina", "fosfatase alcalina", "osteocalcina", "cartilagem grandes", "cartilagem pequenas", "linha epifisária", "bolsas sob os olhos", "colágeno das rugas", "pigmentação da pele", "obstrução linfática", "afrouxamento e", "edema", "atividade das células", "fadiga visual", "chumbo", "mercúrio", "cádmio", "crômio", "arsênico", "antimônio", "tálio", "alumínio", "índice de alergia", "nicotinamida", "biotina", "ácido pantotênico", "ácido fólico", "coenzima q10", "glutationa", "metabolismo anormal", "anormalidades tecido", "hiperinsulinemia", "anomalia hipotálamo", "conteúdo anormal de triglicerídeos", "olhos", "dentes", "cabelo e pele", "sistema endocrino", "circulação de sangue", "estômago e intervalo", "sistema imunologico", "articulações", "tecido muscular", "metabolismo da gordura", "desintoxicação e metabolismo", "sistema reprodutivo", "sistema nervoso", "esqueleto", "peristáltica do intestino", "absorção do cólon", "bactérias intestinais", "pressão intraluminal", "tiroxina livre", "tiroglobulina", "anticorpos antitireoglobulina", "triiodotironina", "ácido linoleico", "α-ácido linolênico", "γ-ácido linolênico", "ácido araquidônico", "estrogénio", "andrógeno", "progesterona", "hormona luteinizante", "prolactina", "hormona estimuladora folícula", "meridiano do pulmão", "intestino grosso", "estômago", "baço", "coração", "intestino delgado", "bexiga", "rins", "pericárdio", "triplo aquecedor", "vesícula biliar", "fígado", "ren mai", "meridiano governador", "meridiano vital", "da mai", "acidente vascular cerebral", "pulso", "resistência periférica", "coeficiente da onda", "saturação do oxigênio", "volume do oxigênio", "pressão do oxigênio", "viscosidade do sangue", "colesterol total", "triglicerídeos", "lipoproteína de alta", "lipoproteína de baixa", "gordura neutra", "complexo imunológico", "hormona beta", "proteína de resposta", "fibrinogênio", "taxa de sedimentação", "barreira tecidual", "células imunitárias", "molécula imunitária", "imunitário celular", "imunidade humoral", "vergonha", "culpa", "apatia", "dor", "medo", "desejo", "raiva", "orgulho", "coragem", "neutralidade", "vontade", "aceitação", "razão", "amor", "alegria", "paz", "iluminismo", "volume maré", "volume inspiratório", "capacidade residual", "volume residual", "fosfolipídico", "esfingolípide", "esfingomielina", "lecitina", "fosfolípide cerebral", "lipossômico", "ácidos gordos saturados", "ácidos gordos não saturados", "ácidos gordos essenciais", "triglicéridos"
    ]
    return any(term in name_lower for term in valid_terms)

def names_are_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio() > threshold

def normalize_name(name: str) -> str:
    return re.sub(r'\s+', ' ', name.lower().replace("(", "").replace(")", "").strip())

# Função principal de extração
def extract_parameters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, float]]:
    parameters = {}
    seen = set()
    buffer = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            for line in lines:
                line = clean_text(line)
                if not line:
                    continue

                if is_header_line(line):
                    buffer = ""  # Reset buffer em cabeçalhos
                    continue

                # Regex non-greedy para nome curto antes do range
                pattern = r"([A-Za-z\sKATEX_INLINE_OPEN/)]{10,60}?)\s*(\d+[.,]\d+)\s*-\s*(\d+[.,]\d+)\s*(\d+[.,]\d+)"
                match = re.search(pattern, line)
                if match:
                    raw_name, min_str, max_str, val_str = match.groups()
                    name = clean_text(buffer + " " + raw_name).strip()
                    if is_valid_name(name):
                        norm_name = normalize_name(name)
                        # Mescla se similar a existente (mantém o nome mais longo)
                        for existing in list(parameters.keys()):
                            if names_are_similar(name, existing):
                                if len(name) > len(existing):
                                    del parameters[existing]
                                    seen.remove(normalize_name(existing))
                                else:
                                    name = existing  # Mantém o existente se mais longo
                                break
                        if norm_name in seen:
                            continue
                        seen.add(norm_name)
                        min_val = float(min_str.replace(",", "."))
                        max_val = float(max_str.replace(",", "."))
                        val = float(val_str.replace(",", "."))
                        if min_val < max_val:
                            parameters[name] = {"min": min_val, "max": max_val, "valor": val}
                    buffer = ""  # Reset após match
                else:
                    # Acumula apenas se curto e válido
                    if len(buffer + " " + line) < 40 and is_valid_name(line):
                        buffer += " " + line
                    else:
                        buffer = ""  # Reset se exceder limite

    return parameters

# Validação (com tolerância para bordas exatas)
def validate_parameters(parameters: Dict[str, Dict[str, float]]) -> List[Dict[str, any]]:
    anomalies = []
    for name, data in parameters.items():
        val = data.get("valor")
        min_val = data.get("min")
        max_val = data.get("max")
        if val is None or min_val is None or max_val is None or min_val >= max_val:
            continue
        if not (min_val <= val <= max_val):
            status = "Abaixo" if val < min_val else "Acima"
            anomalies.append({
                "item": name,
                "valor_real": val,
                "status": status,
                "normal_min": min_val,
                "normal_max": max_val,
            })
    return anomalies

# Geração de relatório (inalterada)
def generate_report(anomalies: List[Dict[str, any]], therapist: str, registry: str, output_path: str) -> None:
    doc = Document()
    doc.add_heading("Relatório de Anomalias", level=1)
    doc.add_paragraph(f"Terapeuta: {therapist}   Registro: {registry}")

    if not anomalies:
        doc.add_paragraph("🎉 Todos os parâmetros dentro da normalidade.")
    else:
        doc.add_paragraph(f"⚠️ {len(anomalies)} anomalias encontradas:")
        for a in anomalies:
            doc.add_paragraph(
                f"• {a['item']}: {a['valor_real']:.3f} "
                f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
            )
    doc.save(output_path)