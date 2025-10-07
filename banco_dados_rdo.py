import mysql.connector
import pandas as pd
import os

def extract_turnos_eventos_fim_rdo():
    try:
        # Conexão com o banco
        connection = mysql.connector.connect(
            host='sgddolp.com.br',
            database='dolpenge_views',
            user='dolpenge_dolpviews',
            password='Why6RT0H}+#&uo]'
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            # Nome do CSV de saída
            csv_file = 'turnos_eventos_fim_rdo.csv'

            # Query para trazer toda a base
            query = """
            SELECT 
                t.idtb_turnos,
                t.dt_inicio AS data_turno,
                t.idtb_equipes,
                e.evento,
                t.num_operacional,
                t.prefixo,
                t.unidade,
                t.tipo,
                t.cidade,
                t.descricao_tipo_prefixo
            FROM view_power_bi_turnos t
            LEFT JOIN view_power_bi_turnos_eventos e
                ON t.idtb_turnos = e.idtb_turnos
            ORDER BY t.dt_inicio
            """

            cursor.execute(query)
            dados = pd.DataFrame(cursor.fetchall())

            if not dados.empty:
                # Remove duplicados por turno + evento
                dados.drop_duplicates(subset=['idtb_turnos', 'evento'], inplace=True)

                # Salva CSV
                dados.to_csv(csv_file, index=False, encoding="utf-8-sig")
                print(f"✅ Extração concluída. {len(dados)} registros salvos em {csv_file}.")
            else:
                print("⚠️ Nenhum dado retornado pela query.")

    except mysql.connector.Error as e:
        print(f"❌ Erro ao conectar ou extrair dados: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Conexão ao MariaDB fechada.")

if __name__ == "__main__":
    extract_turnos_eventos_fim_rdo()
