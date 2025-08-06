import re
from typing import Dict, List, Optional
import pdfplumber
from docx import Document
import os

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
    """Verifica se é um nome válido (não é cabeçalho ou vazio)."""
    name_lower = name.lower()
    invalid_keywords = ["intervalo normal", "valor de medição real", "resultado do teste", "item de teste"]
    return bool(name) and not any(kw in name_lower for kw in invalid_keywords) and re.search(r'[a-zA-Z]', name)

# Função principal de extração (nova abordagem: texto bruto + regex)
def extract_parameters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, float]]:
    """
    Extrai parâmetros usando texto bruto e regex para maior robustez.
    Padrão: "Nome min - max valor" ou variações.
    Retorna: {"Nome": {"min": float, "max": float, "valor": float}}
    """
    parameters = {}
    seen = set()  # Evita duplicatas

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += clean_text(page.extract_text()) + " "

        # Regex para capturar linhas como "Nome min - max valor"
        pattern = r"([A-Za-z\sKATEX_INLINE_OPENKATEX_INLINE_CLOSE/]+?)\s*(\d+[.,]?\d*)\s*-\s*(\d+[.,]?\d*)\s*(\d+[.,]?\d*)"
        matches = re.findall(pattern, full_text)

        for match in matches:
            raw_name, min_str, max_str, val_str = match
            name = clean_text(raw_name).strip()
            if not is_valid_name(name) or name in seen:
                continue

            try:
                min_val = float(min_str.replace(",", "."))
                max_val = float(max_str.replace(",", "."))
                val = float(val_str.replace(",", "."))
                if min_val >= max_val:  # Range inválido
                    continue
            except ValueError:
                continue

            seen.add(name)
            parameters[name] = {"min": min_val, "max": max_val, "valor": val}

    return parameters

# Validação
def validate_parameters(parameters: Dict[str, Dict[str, float]]) -> List[Dict[str, any]]:
    """Retorna lista de anomalias."""
    anomalies = []
    for name, data in parameters.items():
        val = data.get("valor")
        min_val = data.get("min")
        max_val = data.get("max")
        if val is None or min_val is None or max_val is None or min_val > max_val:
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