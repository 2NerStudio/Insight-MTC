import json
import sqlite3
from extrair_dados import extrair_dados_do_pdf

# =======================
# 📄 1. Caminho do PDF
# =======================
CAMINHO_PDF = "relatório original.pdf"

# =======================
# 🧪 2. Extrair os dados
# =======================
dados = extrair_dados_do_pdf(CAMINHO_PDF)

print("✅ Dados extraídos do PDF:\n")
for d in dados:
    print(f"- {d['item']} | {d['valor']} (Normal: {d['intervalo']})")
    print(f"  Conselho: {d['conselho']}\n")

# =======================
# 💾 3. Salvar em JSON
# =======================
with open("dados_extraidos.json", "w", encoding="utf-8") as f:
    json.dump(dados, f, indent=2, ensure_ascii=False)
print("📁 Arquivo salvo: dados_extraidos.json")

# =======================
# 🗃️ 4. Salvar em SQLite
# =======================
conn = sqlite3.connect("dados_relatorio.db")
cursor = conn.cursor()

# Criar a tabela
cursor.execute("""
CREATE TABLE IF NOT EXISTS dados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT,
    intervalo TEXT,
    valor TEXT,
    conselho TEXT
)
""")

# Limpar entradas antigas (opcional)
cursor.execute("DELETE FROM dados")

# Inserir os dados
for d in dados:
    cursor.execute("""
    INSERT INTO dados (item, intervalo, valor, conselho)
    VALUES (?, ?, ?, ?)
    """, (d["item"], d["intervalo"], d["valor"], d["conselho"]))

conn.commit()
conn.close()
print("🗃️ Banco de dados atualizado: dados_relatorio.db")
