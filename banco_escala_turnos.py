import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def exportar_dados_para_csv():
    """
    Conecta ao banco de dados MySQL, executa as consultas para escalas e turnos,
    e exporta os resultados para arquivos CSV.
    """
    # Cria a pasta 'data' se ela não existir
    os.makedirs("data", exist_ok=True)

    # Configurações de conexão com o banco de dados a partir do .env
    config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "use_pure": True
    }

    try:
        # Estabelece a conexão com o banco de dados
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        print("🚀 Conexão com o banco de dados estabelecida com sucesso!")

        # 1. Exportar dados da view_power_bi_equipe para escala_nova.csv
        print("\nIniciando a exportação para escala_nova.csv...")
        query_escala = """
        SELECT 
            idtb_escala, data_inicio, id_equipe, equipe, cidade, 
            nome_supervisor, id_funcionario, unidade, tp_dia
        FROM view_power_bi_equipe
        WHERE data_inicio >= '2025-01-01'
        """
        cursor.execute(query_escala)
        
        colunas_escala = [
            'idtb_escala', 'data_inicio', 'id_equipe', 'equipe', 'cidade',
            'nome_supervisor', 'id_funcionario', 'unidade', 'tp_dia'
        ]
        
        df_escala = pd.DataFrame(cursor.fetchall(), columns=colunas_escala)
        
        # Cria a coluna 'prefixo' a partir da coluna 'equipe'
        df_escala['prefixo'] = df_escala['equipe'].astype(str).str[6:]
        
        df_escala.to_csv("data/escala_nova.csv", index=False, encoding='utf-8')
        print(f"✔️ {len(df_escala)} registros salvos em data/escala_nova.csv (com a coluna 'prefixo')")

        # 2. Exportar dados da view_power_bi_turnos para turnos_newmars.csv
        print("\nIniciando a exportação para turnos_newmars.csv...")
        query_turnos = """
        SELECT 
            dt_inicio, unidade, cidade, num_operacional, 
            prefixo, descricao_tipo_prefixo
        FROM view_power_bi_turnos
        """
        cursor.execute(query_turnos)

        colunas_turnos = [
            'dt_inicio', 'unidade', 'cidade', 'num_operacional', 
            'prefixo', 'descricao_tipo_prefixo'
        ]

        df_turnos = pd.DataFrame(cursor.fetchall(), columns=colunas_turnos)
        df_turnos.to_csv("data/turnos_newmars.csv", index=False, encoding='utf-8')
        print(f"✔️ {len(df_turnos)} registros salvos em data/turnos_newmars.csv")

    except mysql.connector.Error as err:
        print(f"❌ Erro ao conectar ou executar a consulta: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n🔒 Conexão com o banco de dados encerrada.")

if __name__ == "__main__":
    exportar_dados_para_csv()
