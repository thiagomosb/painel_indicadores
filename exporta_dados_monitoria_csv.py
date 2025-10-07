import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

def exportar_dados_monitoramento():
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
        cursor = connection.cursor()

        # Exportar TURNOS
        query_turnos_monitoria = """
        SELECT 
            unidade, idtb_turnos, num_operacional, prefixo, 
            dt_inicio, dt_fim, tipo, motora, nom_fant
        FROM view_power_bi_turnos
        """
        cursor.execute(query_turnos_monitoria)
        df_turnos = pd.DataFrame(cursor.fetchall(), columns=[
            "unidade", "idtb_turnos", "num_operacional", "prefixo",
            "dt_inicio", "dt_fim", "tipo", "motora", "nom_fant"
        ])
        df_turnos.to_csv("data/turnos_monitoria.csv", index=False)
        print("✔️ turnos_monitoria.csv salvo")

        # Exportar AVULSA
        query_avulsa = """
        SELECT 
            idturnos, unidade, equipe_real, dt_inicio_serv, situacao, 
            gravou_atividade, monitor, supervisor
        FROM view_power_bi_avulsa_mon
        """
        cursor.execute(query_avulsa)
        df_avulsa = pd.DataFrame(cursor.fetchall(), columns=[
            "idturnos", "unidade", "equipe_real", "dt_inicio_serv", "situacao",
            "gravou_atividade", "monitor", "supervisor"
        ])
        df_avulsa.to_csv("data/avulsa.csv", index=False)
        print("✔️ avulsa.csv salvo")

        # Exportar PESSOAS
        query_pessoas_monitoria = """
        SELECT situacao, idtb_oper_pessoa, nome, funcao_geral, dt_admissao
        FROM view_power_bi_pessoas
        """
        cursor.execute(query_pessoas_monitoria)
        df_pessoas = pd.DataFrame(cursor.fetchall(), columns=[
            "situacao", "idtb_oper_pessoa", "nome", "funcao_geral", "dt_admissao"
        ])
        df_pessoas.to_csv("data/pessoas_monitoria.csv", index=False)
        print("✔️ pessoas_monitoria.csv salvo")

        # Exportar TURNOS PESSOAS
        query_turnos_pessoas_monitoria = """
        SELECT 
            idtb_turnos, idtb_pessoas, idtb_escalas, nome, funcao
        FROM view_power_bi_turnos_pessoas
        """
        cursor.execute(query_turnos_pessoas_monitoria)
        df_turnos_pessoas = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_turnos", "idtb_pessoas", "idtb_escalas", "nome", "funcao"
        ])
        df_turnos_pessoas.to_csv("data/turnos_pessoas_monitoria.csv", index=False)
        print("✔️ turnos_pessoas_monitoria.csv salvo")

    except mysql.connector.Error as err:
        print(f"❌ Erro ao conectar: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔒 Conexão encerrada.")

if __name__ == "__main__":
    exportar_dados_monitoramento()
