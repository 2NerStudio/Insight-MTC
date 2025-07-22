# validacao_parametros.py

from parametros import PARAMETROS_NORMAIS

def validar_registro(registro):
    """
    Dado um registro com chaves:
      registro['item'], registro['valor'], registro['intervalo'], registro['conselho'], ...
    Retorna o registro se estiver fora do normal, ou None caso esteja normal.
    """
    nome = registro["item"]
    valor_str = registro["valor"].replace(",", ".").strip()
    try:
        valor = float(valor_str)
    except:
        return None  # não conseguiu converter, ignora

    # busca no dicionário
    if nome not in PARAMETROS_NORMAIS:
        return None

    minimo, maximo = PARAMETROS_NORMAIS[nome]
    if valor < minimo or valor > maximo:
        # adiciona os limites ao registro para uso posterior
        registro["minimo"] = minimo
        registro["maximo"] = maximo
        registro["valor_real"] = valor
        return registro

    return None
