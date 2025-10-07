import mysql.connector
import pandas as pd
import os

def extract_and_save_to_csv():
    try:
        connection = mysql.connector.connect(
            host='',
            database='',
            user='',
            password=''
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            # ---------------- ESCALA (sem alterações) ----------------
            escala_file = 'escala_data.csv'
            df_escala_existente = pd.DataFrame() 

            if os.path.exists(escala_file):
                df_escala_existente = pd.read_csv(escala_file)
                ultimo_id_escala = df_escala_existente['idtb_escala'].max()
                print(f"Último idtb_escala no CSV: {ultimo_id_escala}")

                query_escala = f"""
                SELECT 
                    idtb_escala, data_inicio, id_equipe, equipe, cidade, 
                    nome_funcionario, nome_supervisor, id_funcionario, unidade, tp_dia
                FROM view_power_bi_equipe
                WHERE idtb_escala > {ultimo_id_escala}
                ORDER BY idtb_escala
                """
            else:
                query_escala = """
                SELECT 
                    idtb_escala, data_inicio, id_equipe, equipe, cidade, 
                    nome_funcionario, nome_supervisor, id_funcionario, unidade, tp_dia
                FROM view_power_bi_equipe
                WHERE data_inicio >= '2025-01-01'
                ORDER BY idtb_escala
                """

            cursor.execute(query_escala)
            novos_escala = pd.DataFrame(cursor.fetchall())
            
            df_escala_final = df_escala_existente

            if not novos_escala.empty:
                print(f"Encontrados {len(novos_escala)} novos registros de escala.")
                query_turnos_prefixo = """
                SELECT idtb_equipes, descricao_tipo_prefixo
                FROM view_power_bi_turnos WHERE dt_inicio >= '2025-01-01'
                """
                cursor.execute(query_turnos_prefixo)
                df_turnos_prefixo = pd.DataFrame(cursor.fetchall())

                novos_escala['id_equipe'] = novos_escala['id_equipe'].astype(str)
                df_turnos_prefixo['idtb_equipes'] = df_turnos_prefixo['idtb_equipes'].astype(str)

                novos_escala = pd.merge(
                    novos_escala,
                    df_turnos_prefixo.drop_duplicates(subset='idtb_equipes'),
                    left_on='id_equipe',
                    right_on='idtb_equipes',
                    how='left'
                ).drop(columns=['idtb_equipes'])
                
                df_escala_final = pd.concat([df_escala_existente, novos_escala], ignore_index=True)
            else:
                print("Nenhum novo registro de escala encontrado.")

            if not df_escala_final.empty:
                df_escala_final.drop_duplicates(subset=['idtb_escala'], inplace=True, keep='last')
                df_escala_final['prefixo'] = df_escala_final['equipe'].astype(str).str[6:]
                df_escala_final.to_csv(escala_file, index=False)
                print(f"Arquivo '{escala_file}' salvo com sucesso e com a coluna 'prefixo'.")
            else:
                print("Nenhum dado para salvar no arquivo de escala.")


            # ---------------- TURNOS (Com a coluna "descricao_tipo_prefixo" adicionada) ----------------
            turnos_file = 'turnos_data.csv'
            
            if os.path.exists(turnos_file):
                df_turnos_existente = pd.read_csv(turnos_file)
                ultimo_id_turno = df_turnos_existente['idtb_turnos'].max()
                print(f"Último idtb_turnos no CSV: {ultimo_id_turno}")

                query_turnos_completo = f"""
                SELECT 
                    p.idtb_turnos, p.idtb_pessoas, p2.nome, t.dt_inicio as data_turno,
                    t.unidade, t.idtb_equipes, t.cidade, t.dt_inicio, t.dt_fim,
                    t.num_operacional, t.prefixo, e.evento, t.descricao_tipo_prefixo -- <-- COLUNA ADICIONADA AQUI
                FROM view_power_bi_turnos_pessoas p
                JOIN view_power_bi_pessoas p2 ON p.idtb_pessoas = p2.idtb_oper_pessoa
                JOIN view_power_bi_turnos t ON p.idtb_turnos = t.idtb_turnos
                LEFT JOIN view_power_bi_turnos_eventos e ON t.idtb_turnos = e.idtb_turnos
                WHERE p.idtb_turnos > {ultimo_id_turno}
                ORDER BY p.idtb_turnos
                """
            else:
                df_turnos_existente = pd.DataFrame()
                query_turnos_completo = """
                SELECT 
                    p.idtb_turnos, p.idtb_pessoas, p2.nome, t.dt_inicio as data_turno,
                    t.unidade, t.idtb_equipes, t.cidade, t.dt_inicio, t.dt_fim,
                    t.num_operacional, t.prefixo, e.evento, t.descricao_tipo_prefixo -- <-- E AQUI TAMBÉM
                FROM view_power_bi_turnos_pessoas p
                JOIN view_power_bi_pessoas p2 ON p.idtb_pessoas = p2.idtb_oper_pessoa
                JOIN view_power_bi_turnos t ON p.idtb_turnos = t.idtb_turnos
                LEFT JOIN view_power_bi_turnos_eventos e ON t.idtb_turnos = e.idtb_turnos
                WHERE t.dt_inicio >= '2025-01-01'
                ORDER BY p.idtb_turnos
                """

            cursor.execute(query_turnos_completo)
            novos_turnos = pd.DataFrame(cursor.fetchall())

            if not novos_turnos.empty:
                df_turnos_final = pd.concat([df_turnos_existente, novos_turnos], ignore_index=True)
                df_turnos_final.drop_duplicates(subset=['idtb_turnos', 'idtb_pessoas', 'evento'], inplace=True)
                df_turnos_final.to_csv(turnos_file, index=False)
                print(f"{len(novos_turnos)} novos registros adicionados em {turnos_file}")
            else:
                # Se não houver novos turnos, ainda salva o arquivo caso tenha sido a primeira execução
                if not os.path.exists(turnos_file) and not df_turnos_existente.empty:
                     df_turnos_existente.to_csv(turnos_file, index=False)
                print("Nenhum novo registro de turnos encontrado.")


    except mysql.connector.Error as e:
        print(f"Erro ao conectar ao MariaDB ou extrair dados: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexão ao MariaDB fechada.")

if __name__ == "__main__":

    extract_and_save_to_csv()
