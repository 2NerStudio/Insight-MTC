# validacao_parametros.py

from parametros import PARAMETROS
from extrair_dados import extrair_valores_apenas
from utils import exportar_para_docx

def validar_valores(valores: dict):
    anomalias = []
    faltantes = []

    for item, val_str in valores.items():
        # pula quem não tem valor
        if not val_str:
            continue

        # converte string
        try:
            valor = float(val_str.replace(",", "."))
        except ValueError:
            continue

        # verifica existência no dicionário
        if item not in PARAMETROS:
            faltantes.append(item)
            continue

        minimo, maximo = PARAMETROS[item]
        if valor < minimo:
            status = "Abaixo"
        elif valor > maximo:
            status = "Acima"
        else:
            continue

        anomalias.append({
            "item": item,
            "valor_real": valor,
            "status": status,
            "normal_min": minimo,
            "normal_max": maximo
        })

    return anomalias, sorted(set(faltantes))

def gerar_relatorio_anomalias(pdf_path: str, terapeuta: str, registro: str, output_path="relatorio_anomalias.docx"):
    valores = extrair_valores_apenas(pdf_path)
    anomalias, faltantes = validar_valores(valores)

    # Monta o texto
    lines = [f"Relatório de Anomalias",
             f"Terapeuta: {terapeuta}   Registro: {registro}", ""]
    if not anomalias:
        lines.append("🎉 Todos os parâmetros dentro da normalidade.")
    else:
        for a in anomalias:
            lines.append(
                f"• {a['item']}: {a['valor_real']}  "
                f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})"
            )
    if faltantes:
        lines += ["", "⚠️ Itens extraídos sem parâmetros definidos (adicione-os em parametros_normais.py):"]
        for item in faltantes:
            lines.append(f"- {item}")

    texto = "\n".join(lines) + "\n"
    buffer = exportar_para_docx(texto)
    with open(output_path, "wb") as f:
        f.write(buffer.read())
    print(f"✅ Relatório gerado: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Uso: python validacao_parametros.py <arquivo.pdf> \"Nome\" \"Registro\"")
        sys.exit(1)
    gerar_relatorio_anomalias(sys.argv[1], sys.argv[2], sys.argv[3])
