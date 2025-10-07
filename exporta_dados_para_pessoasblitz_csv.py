import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

def exportar_dados():
    os.makedirs("data", exist_ok=True)

    config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "use_pure": True
    }

    print("DB_HOST:", config["host"])

    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        # Exportar BLITZ
        query_blitz = """
            SELECT 
                b.prefixo,
                b.idtb_pessoas_inspetor, 
                b.idtb_pessoas,
                b.zona_inspecao,
                b.Key,
                b.idtb_turnos_blitz_contatos,
                b.nome_inspetor, 
                b.num_operacional,
                b.idtb_turnos, 
                b.data_turno,
                t.nom_fant, 
                t.unidade, 
                p.funcao, 
                p.nome, 
                t.tipo, 
                p2.funcao_geral
            FROM view_power_bi_blitz_contatos b
            JOIN view_power_bi_turnos t ON b.idtb_turnos = t.idtb_turnos
            JOIN view_power_bi_turnos_pessoas p ON b.idtb_turnos = p.idtb_turnos
            JOIN view_power_bi_pessoas p2 ON b.nome_inspetor = p2.nome
            """
        cursor.execute(query_blitz)
        df_blitz = pd.DataFrame(cursor.fetchall(), columns=[
            "prefixo",
            "idtb_pessoas_inspetor",  # <- nova coluna adicionada
            "idtb_pessoas",
            "zona_inspecao", 
            "Key", 
            "idtb_turnos_blitz_contatos",
            "nome_inspetor", 
            "num_operacional", 
            "idtb_turnos", 
            "data_turno",
            "nom_fant", 
            "unidade", 
            "funcao", 
            "nome", 
            "tipo", 
            "funcao_geral"
        ])
        df_blitz.to_csv("data/blitz.csv", index=False)
        print("✔️ blitz.csv salvo")

        # Exportar TURNOS com novas colunas
        # Exportar TURNOS com idtb_turnos incluso
        query_turnos = """
        SELECT 
            prefixo, idtb_turnos, num_operacional, dt_inicio, nom_fant, unidade, id_reserva, descricao_tipo_prefixo
        FROM view_power_bi_turnos
        """
        cursor.execute(query_turnos)
        df_turnos = pd.DataFrame(cursor.fetchall(), columns=[
            "prefixo","idtb_turnos", "num_operacional", "dt_inicio", "nom_fant", "unidade", "id_reserva", "descricao_tipo_prefixo"
        ])
        df_turnos.to_csv("data/turnos.csv", index=False)
        print("✔️ turnos.csv salvo")


        # Exportar RESPOSTAS
        query_respostas = """
        SELECT 
            r.idtb_pessoas, r.Key, r.resposta_int, r.pergunta, r.nc_criada, r.idtb_turnos_pessoas,
            r.subgrupo, r.pontuacao,
            b.nome_inspetor, b.num_operacional, b.idtb_turnos
        FROM view_power_bi_blitz_respostas r
        JOIN view_power_bi_blitz_contatos b ON r.Key = b.Key
        JOIN view_power_bi_turnos t ON b.idtb_turnos = t.idtb_turnos
        """
        cursor.execute(query_respostas)
        df_respostas = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_pesoas","Key", "resposta_int", "pergunta", "nc_criada", "idtb_turnos_pessoas",
            "subgrupo", "pontuacao", "nome_inspetor", "num_operacional", "idtb_turnos"
        ])
        df_respostas.to_csv("data/respostas.csv", index=False)
        print("✔️ respostas.csv salvo")

        # Exportar EVENTOS
        query_eventos = """
        SELECT 
            e.idtb_turnos, e.evento, e.latitude, e.longitude
        FROM view_power_bi_turnos_eventos e
        JOIN view_power_bi_turnos t ON e.idtb_turnos = t.idtb_turnos
        JOIN view_power_bi_blitz_contatos b ON e.idtb_turnos = b.idtb_turnos
        """
        cursor.execute(query_eventos)
        df_eventos = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_turnos", "evento", "latitude", "longitude"
        ])
        df_eventos.to_csv("data/eventos.csv", index=False)
        print("✔️ eventos.csv salvo")
        
        # Exportar contatos (blitz)
        query_blitzPessoas = """
        SELECT 
            b.nome_inspetor, b.num_operacional, b.idtb_turnos, b.data_turno,
            t.nom_fant, t.unidade, t.tipo, 
            p2.funcao_geral, p.nome, p2.idtb_oper_pessoa, p.idtb_pessoas, p2.dt_admissao
        FROM view_power_bi_blitz_contatos b
        JOIN view_power_bi_turnos t ON b.idtb_turnos = t.idtb_turnos
        JOIN view_power_bi_turnos_pessoas p ON b.idtb_turnos = p.idtb_turnos
        JOIN view_power_bi_pessoas p2 ON p.idtb_pessoas = p2.idtb_oper_pessoa
        """
        cursor.execute(query_blitzPessoas)
        df_blitz = pd.DataFrame(cursor.fetchall(), columns=[
            "nome_inspetor", "num_operacional", "idtb_turnos", "data_turno", "nom_fant",
            "unidade", "tipo", "funcao_geral", "nome", "idtb_oper_pessoa", "idtb_pessoas", "dt_admissao"
        ])
        df_blitz.to_csv("data/blitzPessoas.csv", index=False, encoding="utf-8")
        print("✔️ blitzPessoas.csv salvo")

        # Exportar turnos
        query_turnosPessoas = """
        SELECT idtb_turnos, num_operacional, dt_inicio, nom_fant, unidade
        FROM view_power_bi_turnos
        """
        cursor.execute(query_turnosPessoas)
        df_turnos = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_turnos", "num_operacional", "dt_inicio", "nom_fant", "unidade"
        ])
        df_turnos.to_csv("data/turnosPessoas.csv", index=False, encoding="utf-8")
        print("✔️ turnosPessoas.csv salvo")

        # Exportar turnos_pessoas
        query_turnos_pessoas_Pessoas = """
        SELECT idtb_turnos, idtb_pessoas
        FROM view_power_bi_turnos_pessoas
        """
        cursor.execute(query_turnos_pessoas_Pessoas)
        df_turnos_pessoas = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_turnos", "idtb_pessoas"
        ])
        df_turnos_pessoas.to_csv("data/turnos_pessoas_pessoas.csv", index=False, encoding="utf-8")
        print("✔️ turnos_pessoas_pessoas.csv salvo")

        # Exportar pessoas
        query_pessoas = """
        SELECT base, situacao, idtb_oper_pessoa, nome, funcao_geral, dt_admissao
        FROM view_power_bi_pessoas
        """
        cursor.execute(query_pessoas)
        df_pessoas = pd.DataFrame(cursor.fetchall(), columns=[
            "base","situacao", "idtb_oper_pessoa", "nome", "funcao_geral", "dt_admissao"
        ])
        df_pessoas.to_csv("data/pessoas.csv", index=False, encoding="utf-8")
        print("✔️ pessoas.csv salvo")
        
        
        # Exportar RESPOSTAS
        query_respostas = """
        SELECT 
            r.idtb_pessoas, r.Key, r.resposta_int, r.pergunta, r.nc_criada, r.idtb_turnos_pessoas,
            r.subgrupo, r.pontuacao,
            b.nome_inspetor, b.num_operacional, b.idtb_turnos
        FROM view_power_bi_blitz_respostas r
        JOIN view_power_bi_blitz_contatos b ON r.Key = b.Key
        JOIN view_power_bi_turnos t ON b.idtb_turnos = t.idtb_turnos
        """
        cursor.execute(query_respostas)
        df_respostas = pd.DataFrame(cursor.fetchall(), columns=[
            "idtb_pesoas","Key", "resposta_int", "pergunta", "nc_criada", "idtb_turnos_pessoas",
            "subgrupo", "pontuacao", "nome_inspetor", "num_operacional", "idtb_turnos"
        ])
        df_respostas.to_csv("data/respostas.csv", index=False)
        print("✔️ respostas.csv salvo")

    
    except mysql.connector.Error as err:
        print(f"❌ Erro ao conectar: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔒 Conexão encerrada.")

if __name__ == "__main__":
    exportar_dados()
