import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

def exportar_funcoes_unidades():
    os.makedirs("data", exist_ok=True)

    config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "use_pure": True
    }

    try:
        connection = mysql.connector.connect(**config)

        if connection.is_connected():
            cursor = connection.cursor()

            # ---------------- FUNCOES ----------------
            query_funcoes = "SELECT DISTINCT funcao_geral FROM view_power_bi_pessoas"
            cursor.execute(query_funcoes)
            df_funcoes = pd.DataFrame(cursor.fetchall(), columns=["funcao_geral"])
            df_funcoes.to_csv("data/funcoes.csv", index=False, encoding="utf-8")
            print(f"✔️ funcoes.csv gerado com {len(df_funcoes)} registros")

            # ---------------- UNIDADES ----------------
            query_unidades = "SELECT DISTINCT idtb_bases, unidade FROM view_power_bi_turnos"
            cursor.execute(query_unidades)
            df_unidades = pd.DataFrame(cursor.fetchall(), columns=["idtb_bases", "unidade"])
            df_unidades.to_csv("data/unidades.csv", index=False, encoding="utf-8")
            print(f"✔️ unidades.csv gerado com {len(df_unidades)} registros")

    except mysql.connector.Error as e:
        print(f"❌ Erro ao conectar ao banco: {e}")

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔒 Conexão encerrada.")

# Executar
if __name__ == "__main__":
    exportar_funcoes_unidades()
