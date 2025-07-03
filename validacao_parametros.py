def checar_parametro(item, valor_min, valor_max, valor_real):
    """
    Verifica se o valor está dentro do intervalo normal.
    Retorna um dicionário com status e dados.
    """
    try:
        valor_real = float(valor_real)
        valor_min = float(valor_min)
        valor_max = float(valor_max)
    except ValueError:
        return {
            "item": item,
            "status": "Erro",
            "detalhe": "Valores inválidos"
        }

    if valor_real < valor_min:
        return {
            "item": item,
            "status": "Abaixo do normal",
            "valor": valor_real,
            "normal": f"{valor_min} - {valor_max}"
        }
    elif valor_real > valor_max:
        return {
            "item": item,
            "status": "Acima do normal",
            "valor": valor_real,
            "normal": f"{valor_min} - {valor_max}"
        }
    else:
        return {
            "item": item,
            "status": "Normal",
            "valor": valor_real,
            "normal": f"{valor_min} - {valor_max}"
        }
    
if __name__ == "__main__":
    resultado = checar_parametro("Viscosidade do sangue", 48.264, 65.371, 69.954)
    print(resultado)

    resultado2 = checar_parametro("Ácido úrico", 1.435, 1.987, 3.11)
    print(resultado2)

    resultado3 = checar_parametro("Vitamina E", 4.826, 6.013, 4.119)
    print(resultado3)
