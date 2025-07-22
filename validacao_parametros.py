# validacao_parametros.py

import sys
from extrair_dados import extrair_valores_apenas
from parametros import PARAMETROS
from utils import exportar_para_docx

def validar_valores(valores: dict):
    """
    Retorna uma lista de dicionários somente com os itens cujo
    valor esteja abaixo ou acima do intervalo normal.
    Cada dicionário contém:
      - item
      - valor_real (float)
      - status ("Abaixo" ou "Acima")
      - normal_min, normal_max
    """
    anomalias = []
    for item, val_str in valores.items():
        if val_str is None or val_str == "":
            continue
        try:
            # converte "69,954" -> 69.954
            valor = float(val_str.replace(",", "."))
        except ValueError:
            continue
        if item not in PARAMETROS:
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
    return anomalias

def gerar_relatorio_anomalias(pdf_path: str, terapeuta: str, registro: str, output_path="relatorio_anomalias.docx"):
    # 1) Extrai valores do PDF
    valores = extrair_valores_apenas(pdf_path)

    # 2) Valida e filtra fora do normal
    anomalias = validar_valores(valores)

    # 3) Monta texto do relatório
    if not anomalias:
        texto = "🎉 Todos os parâmetros estão dentro do intervalo normal."
    else:
        texto = f"Relatório de Anomalias  \nTerapeuta: {terapeuta}  |  Registro: {registro}\n\n"
        for a in anomalias:
            texto += (f"• {a['item']}: {a['valor_real']}  "
                      f"({a['status']} do normal; Normal: {a['normal_min']}–{a['normal_max']})\n")
        texto += "\n"

    # 4) Exporta para DOCX
    buffer = exportar_para_docx(texto)
    with open(output_path, "wb") as f:
        f.write(buffer.read())

    print(f"✅ Relatório gerado: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso:")
        print("  python validacao_parametros.py <arquivo.pdf> \"Nome Terapeuta\" \"Registro\"")
        sys.exit(1)

    pdf_file = sys.argv[1]
    terapeuta = sys.argv[2]
    registro = sys.argv[3]
    gerar_relatorio_anomalias(pdf_file, terapeuta, registro)
