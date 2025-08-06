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
    return (
        text.replace("\n", " ")
        .replace("\r", " ")
        .replace(",", ".")
        .replace("’", "'")
        .replace("'", "")
        .strip()
    )

def extract_numbers(text: Optional[str]) -> List[float]:
    """Extrai números (inteiros ou floats) de uma string."""
    if not text:
        return []
    matches = re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)
    return [float(m.replace(",", ".")) for m in matches]

def is_parameter_row(range_str: str, value_str: str) -> bool:
    """Verifica se é uma linha de parâmetro: range tem >=2 números (min-max), value tem exatamente 1."""
    return len(extract_numbers(range_str)) >= 2 and len(extract_numbers(value_str)) == 1

def split_parameter_name(raw_name: str) -> List[str]:
    """Divide nomes colados em uma célula usando heurísticas (:, ), espaços duplos). Remove duplicados."""
    if ":" in raw_name:
        parts = [p.strip(" -") for p in raw_name.split(":") if p.strip()]
    elif ") " in raw_name:
        parts = [p.strip(" -") + (")" if not p.endswith(")") else "") for p in raw_name.split(") ") if p.strip()]
    elif "  " in raw_name:  # Espaço duplo como separador
        parts = [p.strip() for p in raw_name.split("  ") if p.strip()]
    else:
        parts = [raw_name.strip()]
    
    # Remove duplicados preservando ordem
    seen = set()
    return [p for p in parts if p and not (p in seen or seen.add(p))]

# Função principal de extração
def extract_parameters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, float]]:
    """
    Extrai parâmetros de tabelas em PDF.
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
                    name, range_str, value_str = map(clean_text, row[1:4])
                    rows.append((name, range_str, value_str))

    # Processa as rows
    buffer = []  # Acumula nomes antes de um parâmetro
    i = 0
    while i < len(rows):
        name, range_str, value_str = rows[i]

        if not is_parameter_row(range_str, value_str):
            if name:
                buffer.append(name)
            i += 1
            continue

        # Extrai valores
        nums_range = extract_numbers(range_str)[:2]
        min_val, max_val = nums_range[0], nums_range[1]
        value = extract_numbers(value_str)[0]

        # Coleta nomes: buffer + nome atual + nomes seguintes até próximo parâmetro
        full_name_parts = buffer + ([name] if name else [])
        j = i + 1
        while j < len(rows) and not is_parameter_row(rows[j][1], rows[j][2]):
            next_name = rows[j][0]
            if next_name:
                full_name_parts.append(next_name)
            j += 1

        full_name = " ".join(full_name_parts).strip()
        buffer = []  # Reseta buffer

        # Divide e adiciona ao dict
        for split_name in split_parameter_name(full_name):
            parameters[split_name] = {"min": min_val, "max": max_val, "valor": value}

        i = j  # Avança

    return parameters

# Validação
def validate_parameters(parameters: Dict[str, Dict[str, float]]) -> List[Dict[str, any]]:
    """Retorna lista de anomalias (parâmetros fora do range)."""
    anomalies = []
    for name, data in parameters.items():
        val = data.get("valor")
        min_val = data.get("min")
        max_val = data.get("max")
        if val is None or min_val is None or max_val is None:
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

# Geração de relatório DOCX
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