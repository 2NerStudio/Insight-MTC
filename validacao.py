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
    """Verifica se é um nome válido (mínimo 10 chars alfabéticos, não cabeçalho)."""
    name_lower = name.lower()
    invalid_keywords = ["intervalo normal", "valor de medição", "resultado do teste", "item de teste", "conselho de peritos", "real"]
    if len(re.sub(r'[^a-zA-Z]', '', name)) < 10 or any(kw in name_lower for kw in invalid_keywords):
        return False
    # Evita nomes cortados (ex: termina com preposição curta)
    if name_lower.endswith((" de", " do", " da", " ncia", " o")):
        return False
    return True

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