import re
from typing import Dict, List, Optional
import pdfplumber
from docx import Document
import os
from difflib import SequenceMatcher  # Para similaridade de nomes

# Funções utilitárias
def clean_text(text: Optional[str]) -> str:
    """Limpa texto removendo quebras de linha e normalizando."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\r", " ").replace(",", ".")).strip()

def extract_numbers(text: str) -> List[float]:
    """Extrai números de uma string."""
    matches = re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)
    return [float(m.replace(",", ".")) for m in matches]

def is_valid_name(name: str) -> bool:
    """Verifica se é um nome válido (10-50 chars, não cabeçalho, parece parâmetro)."""
    name_lower = name.lower()
    invalid_keywords = [
        "intervalo normal", "valor de medição", "resultado do teste", "item de teste", "conselho de peritos", "real",
        "nome: exemplo", "sexo: feminino", "idade: 31", "figura: peso padrão", "período do teste", "os resultados do teste",
        "cartão do relatório", "análise", "resultados reais do teste"
    ]
    word_count = len(name.split())
    char_count = len(re.sub(r'[^a-zA-Z]', '', name))
    if char_count < 10 or char_count > 50 or word_count > 10 or any(kw in name_lower for kw in invalid_keywords):
        return False
    # Deve conter padrões de parâmetro (ex: "Coeficiente", "Índice", nomes de órgãos)
    valid_patterns = re.search(r'(coeficiente|índice|grau|vitamina|ácido|hormona|meridiano|elasticidade|viscosidade|gordura|demanda|consumo|impedância|força|pressão|situação|metabolismo|função|teor|atividade|capacidade|resistência|fornecimento|condição|perda|calcificação|secreção|bilirrubina|insulina|polipeptídeo|glucagon|urobilinogênio|nitrogênio|proteína|arterioesclerose|indicador|osteoclastos|hiperplasia|osteoporose|densidade|reumatismo|açúcar|reação|falta|hipóxia|ph|bebida|radiação|tabaco|resíduos|cálcio|ferro|zinco|selênio|fósforo|potássio|magnésio|cobre|cobalto|manganês|iodo|níquel|flúor|molibdênio|vanádio|estanho|silício|estrôncio|boro|estrogênio|gonadotrofina|prolactina|progesterona|vaginite|inflamação|anexite|cervicite|cisto|radicais|colágeno|oleosidade|imunidade|hidratação|dilatação|elasticidade|melanina|queratinócitos|tireóide|paratireóide|supra-renal|pituitária|pineal|timo|gonadal|linfonodo|amígdalas|medula|baço|imunoglobulina|respiratório|gastrointestinal|mucosa|fibrosidade|mastite|distúrbios|fibroadenoma|lisina|triptofano|fenilalanina|metionina|treonina|isoleucina|leucina|valina|histidina|arginina|fosfatase|osteocalcina|cartilagem|epifisária|bolsas|pigmentação|obstrução|afrouxamento|edema|células|fadiga|chumbo|mercúrio|cádmio|crômio|arsênico|antimônio|tálio|alumínio|alergia|nicotinamida|biotina|pantotênico|fólico|q10|glutationa|lipidos|anormalidades|hiperinsulinemia|anomalia|triglicerídeos|olhos|dentes|cabelo|pele|endocrino|circulação|estômago|intestino|imunologico|articulações|muscular|gordura|desintoxicação|reprodutivo|nervoso|esqueleto|peristáltica|absorção|bactérias|pressão|tiroxina|tiroglobulina|anticorpos|triiodotironina|linoleico|linolênico|araquidônico|estrogénio|andrógeno|progesterona|luteinizante|prolactina|folícula|pulmão|intestino|estômago|baço|coração|delgado|bexiga|rims|pericárdio|aquecedor|vesícula|fígado|ren|mai|governador|vital|acidente|pulso|resistência|onda|saturação|volume|pressão|viscosidade|colesterol|triglicerídeos|lipoproteína|gordura|complexo|hormona|beta|fibrinogênio|sedimentação|barreira|células|molécula|celular|humoral|vergonha|culpa|apatia|dor|medo|desejo|raiva|orgulho|coragem|neutralidade|vontade|aceitação|razão|amor|alegria|paz|iluminismo|maré|inspiratório|residual|fosfolipídico|esfingolípide|esfingomielina|lecitina|lipossômico|gordos|saturados|não saturados|essenciais|triglicéridos|medidas|hidratação|volume|muscular|massa|corporal|magro|peso|subpadrão|padrão|sobrepadrão|altura|nota|homem|mulher|propriedade|conteúdo|gordura|porcentagem|razão|abdominal|nutrição|grau|obesidade|bmi|bmr|bcm|tipo|musculatura|ausente|bom|excessivo|proteínas|gorduras|sais|equilíbrio|superior|inferior|membros|simetria|controle|alvo|forma|avaliação|geral|explicação|padrões|aprovado|bom|excelente)', name_lower)
    return bool(valid_patterns)

def normalize_name(name: str) -> str:
    """Normaliza nome para deduplicação (lowercase, remove parênteses extras)."""
    return re.sub(r'\s+', ' ', name.lower().replace("(", "").replace(")", "").strip())

# Função principal de extração (ajustada: por linha + regex melhorada)
def extract_parameters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, float]]:
    """
    Extrai parâmetros processando texto linha por linha com regex aprimorada.
    Retorna: {"Nome Completo": {"min": float, "max": float, "valor": float}}
    """
    parameters = {}
    seen = set()  # Deduplica por nome normalizado
    buffer = ""  # Acumula texto para nomes multi-linha

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

                # Regex: Captura nome (greedy, >=10 chars), seguido de min - max valor
                pattern = r"([A-Za-z\sKATEX_INLINE_OPEN/)]{10,})\s*(\d+[.,]\d+)\s*-\s*(\d+[.,]\d+)\s*(\d+[.,]\d+)"
                match = re.search(pattern, line)
                if match:
                    raw_name, min_str, max_str, val_str = match.groups()
                    name = clean_text(buffer + " " + raw_name).strip()
                    if is_valid_name(name):
                        norm_name = normalize_name(name)
                        if norm_name in seen:
                            continue
                        seen.add(norm_name)
                        min_val = float(min_str.replace(",", "."))
                        max_val = float(max_str.replace(",", "."))
                        val = float(val_str.replace(",", "."))
                        if min_val < max_val:
                            parameters[name] = {"min": min_val, "max": max_val, "valor": val}
                    buffer = ""  # Reseta após match
                else:
                    # Acumula em buffer se for texto potencial (não numérico)
                    if is_valid_name(line):
                        buffer += " " + line

    return parameters

# Validação (ajustada para ignorar se valor == min ou max exatamente, se for borda)
def validate_parameters(parameters: Dict[str, Dict[str, float]]) -> List[Dict[str, any]]:
    """Retorna lista de anomalias."""
    anomalies = []
    for name, data in parameters.items():
        val = data.get("valor")
        min_val = data.get("min")
        max_val = data.get("max")
        if val is None or min_val is None or max_val is None or min_val >= max_val:
            continue
        # Tolerância para bordas (ex: se val == max, considera normal)
        if min_val < val < max_val:
            continue
        status = "Abaixo" if val < min_val else "Acima"
        anomalies.append({
            "item": name,
            "valor_real": val,
            "status": status,
            "normal_min": min_val,
            "normal_max": max_val,
        })
    return anomalies

# Geração de relatório DOCX (inalterada)
def generate_report(anomalies: List[Dict[str, any]], therapist: str, registry: str, output_path: str) -> None:
    """Gera um DOCX com o relatório de anomalias."""
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