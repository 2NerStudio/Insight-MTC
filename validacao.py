import re
from typing import Dict, List, Optional
import pdfplumber
from docx import Document
import os

# Funções utilitárias
def clean_text(text: Optional[str]) -> str:
    """Limpa texto removendo quebras de linha, vírgulas e caracteres indesejados."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\r", " ").replace(",", ".").replace("’", "'").replace("'", "")).strip()

def extract_numbers(text: Optional[str]) -> List[float]:
    """Extrai números (inteiros ou floats) de uma string."""
    if not text:
        return []
    matches = re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)
    return [float(m.replace(",", ".").replace(".", ".", 1)) for m in matches]  # Corrige decimais

def is_header_row(text: str) -> bool:
    """Detecta se é um cabeçalho inválido (ex: 'Intervalo Normal' ou puro ranges)."""
    text_lower = text.lower()
    if "intervalo normal" in text_lower or not re.search(r'[a-zA-Z]', text):  # Sem letras = puro números
        return True
    return False

def is_parameter_row(range_str: str, value_str: str) -> bool:
    """Verifica se é uma linha de parâmetro: range tem >=2 números (min-max), value tem exatamente 1."""
    return len(extract_numbers(range_str)) >= 2 and len(extract_numbers(value_str)) == 1

def split_parameter_name(raw_name: str) -> List[str]:
    """Divide nomes colados usando heurísticas melhoradas (:, ), espaços, parênteses). Remove duplicados e inválidos."""
    raw_name = clean_text(raw_name)
    if not raw_name or is_header_row(raw_name):
        return []
    # Split por padrões comuns no PDF
    parts = re.split(r'(?<=[KATEX_INLINE_CLOSE```]) |: | - ', raw_name)  # Split após ) ou ], ou : ou -
    parts = [p.strip() for p in parts if p.strip() and not is_header_row(p)]
    # Remove duplicados preservando ordem
    seen = set()
    return [p for p in parts if p and not (p in seen or seen.add(p))]

# Função principal de extração
def extract_parameters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, float]]:
    """
    Extrai parâmetros de tabelas em PDF, filtrando cabeçalhos e limpando melhor.
    Retorna: {"Nome do Parâmetro": {"min": float, "max": float, "valor": float}}
    """
    parameters = {}
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_y_tolerance": 10,
    }

    rows = []  # Lista de (nome, range_str, value_str)
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(table_settings):
                for row in table:
                    if len(row) < 4:
                        continue
                    name, range_str, value_str = map(clean_text, row[:3])  # Ajustado para colunas 0-2, caso layout varie
                    if is_header_row(name) or is_header_row(range_str):
                        continue
                    rows.append((name, range_str, value_str))

    # Processa as rows com filtragem
    buffer = []  # Acumula nomes válidos antes de um parâmetro
    i = 0
    seen_names = set()  # Evita duplicatas globais
    while i < len(rows):
        name, range_str, value_str = rows[i]

        if is_header_row(name + range_str + value_str) or not is_parameter_row(range_str, value_str):
            if name and not is_header_row(name):
                buffer.append(name)
            i += 1
            continue

        # Extrai valores
        nums_range = extract_numbers(range_str)[:2]
        if len(nums_range) < 2:
            i += 1
            continue
        min_val, max_val = nums_range
        vals = extract_numbers(value_str)
        if len(vals) != 1:
            i += 1
            continue
        value = vals[0]

        # Coleta nomes: buffer + nome atual + nomes seguintes válidos
        full_name_parts = buffer + ([name] if name and not is_header_row(name) else [])
        j = i + 1
        while j < len(rows) and not is_parameter_row(rows[j][1], rows[j][2]):
            next_name = rows[j][0]
            if next_name and not is_header_row(next_name):
                full_name_parts.append(next_name)
            j += 1

        full_name = " ".join(full_name_parts).strip()
        buffer = []  # Reseta

        # Divide e adiciona ao dict, evitando duplicatas
        for split_name in split_parameter_name(full_name):
            if split_name in seen_names:
                continue
            seen_names.add(split_name)
            parameters[split_name] = {"min": min_val, "max": max_val, "valor": value}

        i = j  # Avança

    return parameters

# Validação (mesma, mas com checagem extra de None)
def validate_parameters(parameters: Dict[str, Dict[str, float]]) -> List[Dict[str, any]]:
    """Retorna lista de anomalias (parâmetros fora do range)."""
    anomalies = []
    for name, data in parameters.items():
        val = data.get("valor")
        min_val = data.get("min")
        max_val = data.get("max")
        if val is None or min_val is None or max_val is None or min_val > max_val:  # Ignora ranges inválidos
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