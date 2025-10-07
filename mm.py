import pandas as pd

# ===============================
# CONFIGURAÇÃO
# ===============================
# Caminho do CSV original
csv_path = r"C:\Users\thiagomacedo.dlp\Desktop\PowerBi\Planilha1.csv"

# Caminho do arquivo M de saída
output_m_path = r"C:\Users\thiagomacedo.dlp\Desktop\PowerBi\codigo_m_completoo2.txt"

# ===============================
# LEITURA DO CSV
# ===============================
df = pd.read_csv(csv_path)

# ===============================
# FUNÇÃO PARA FORMATAR CADA LINHA COMO RECORD DO M
# ===============================
def format_record(row):
    parts = []
    for col in df.columns:
        val = row[col]
        # Se o nome da coluna tem espaço ou caractere especial, envolve em #"..."
        if any(c in col for c in [' ', '%', '-', '/', '(', ')']):
            col_name = f'#"{col}"'
        else:
            col_name = col

        if pd.isna(val):
            parts.append(f'{col_name}=null')
        elif isinstance(val, (int, float)):
            parts.append(f'{col_name}={val}')
        else:
            val_str = str(val).replace('"', '""')
            parts.append(f'{col_name}="{val_str}"')
    return "[" + ", ".join(parts) + "]"


# ===============================
# GERAR LISTA DE RECORDS
# ===============================
records = df.apply(format_record, axis=1).tolist()

# ===============================
# MONTAR CÓDIGO M FINAL
# ===============================
# Quebra de linha a cada 100 registros para facilitar leitura
chunks = [records[i:i+100] for i in range(0, len(records), 100)]
m_lines = []
for chunk in chunks:
    m_lines.append("        " + ",\n        ".join(chunk))

m_code = "let\n    Fonte = Table.FromRecords({\n" + ",\n".join(m_lines) + "\n    })\nin\n    Fonte"

# ===============================
# SALVAR EM ARQUIVO
# ===============================
with open(output_m_path, "w", encoding="utf-8") as f:
    f.write(m_code)

print(f"Código M gerado com sucesso! Arquivo salvo em:\n{output_m_path}")
