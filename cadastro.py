import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import mysql.connector

# --- ARQUIVOS DE DADOS ---
HISTORICO_CSV = "historico_alteracoes.csv"
ESCALA_CSV = "escala_data.csv"

# --- DADOS DE CONEXÃO ---
DB_HOST = 'sgddolp.com.br'
DB_DATABASE = 'dolpenge_views'
DB_USER = 'dolpenge_dolpviews'
DB_PASSWORD = 'Why6RT0H}+#&uo]'

# --- CONFIGURAÇÕES DO APP ---
regionais_unidades = {
    "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"],
    "REGIONAL RIO VERDE": ["RIO VERDE - GO"],
    "REGIONAL TO": ["PALMAS - TO"],
    "REGIONAL MT": ["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]
}

# --- FUNÇÕES AUXILIARES ---

def get_regional_from_unidade(unidade):
    for regional, unidades in regionais_unidades.items():
        if unidade in unidades:
            return regional
    return "NÃO ENCONTRADA"

def carregar_dados_historico():
    try:
        df = pd.read_csv(HISTORICO_CSV)
        df['data_registro'] = pd.to_datetime(df['data_registro'])
        df['data_alteracao'] = pd.to_datetime(df['data_alteracao'])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["data_registro", "data_alteracao", "regional", "unidade", "turno_contrato", "valor_equipe"])

# --- NOVA FUNÇÃO DE SALVAR, MAIS ROBUSTA ---
def salvar_dados_historico(df):
    """Salva o DataFrame de histórico no arquivo CSV com tratamento de erros."""
    try:
        df.to_csv(HISTORICO_CSV, index=False)
        print(f"SUCESSO: Arquivo '{HISTORICO_CSV}' salvo com {len(df)} linhas.")
        return True # Retorna True em caso de sucesso
    except Exception as e:
        st.error(f"ERRO CRÍTICO AO SALVAR O ARQUIVO: Não foi possível escrever em '{HISTORICO_CSV}'.")
        st.error(f"Detalhe do erro: {e}")
        st.warning("Se o app estiver online, isso pode ser normal (sistema de arquivos temporário). Use o botão de download para garantir seus dados.")
        st.warning("Se o app estiver no seu computador, verifique as permissões de escrita na pasta.")
        print(f"FALHA: Erro ao salvar '{HISTORICO_CSV}'. Erro: {e}")
        return False # Retorna False em caso de falha

def atualizar_novas_escalas_do_banco():
    # (Esta função permanece a mesma da versão anterior, sem alterações)
    novos_registros_df = pd.DataFrame()
    try:
        connection = mysql.connector.connect(
            host=DB_HOST, database=DB_DATABASE, user=DB_USER, password=DB_PASSWORD
        )
        if not connection.is_connected():
            st.error("Falha na conexão com o banco de dados.")
            return novos_registros_df

        cursor = connection.cursor(dictionary=True)
        
        df_escala_existente = pd.DataFrame()
        query_escala = ""

        if os.path.exists(ESCALA_CSV):
            df_escala_existente = pd.read_csv(ESCALA_CSV)
            if not df_escala_existente.empty and 'idtb_escala' in df_escala_existente.columns:
                ultimo_id_escala = df_escala_existente['idtb_escala'].max()
                query_escala = f"SELECT * FROM view_power_bi_equipe WHERE idtb_escala > {ultimo_id_escala} ORDER BY idtb_escala"
            else:
                 query_escala = "SELECT * FROM view_power_bi_equipe WHERE data_inicio >= '2025-01-01' ORDER BY idtb_escala"
        else:
            query_escala = "SELECT * FROM view_power_bi_equipe WHERE data_inicio >= '2025-01-01' ORDER BY idtb_escala"

        cursor.execute(query_escala)
        novas_escalas = pd.DataFrame(cursor.fetchall())

        if not novas_escalas.empty:
            cursor.execute("SELECT idtb_equipes, descricao_tipo_prefixo FROM view_power_bi_turnos WHERE dt_inicio >= '2025-01-01'")
            df_turnos_prefixo = pd.DataFrame(cursor.fetchall())
            
            novas_escalas['id_equipe'] = novas_escalas['id_equipe'].astype(str)
            df_turnos_prefixo['idtb_equipes'] = df_turnos_prefixo['idtb_equipes'].astype(str)

            novas_escalas_enriquecido = pd.merge(
                novas_escalas,
                df_turnos_prefixo.drop_duplicates(subset='idtb_equipes'),
                left_on='id_equipe',
                right_on='idtb_equipes',
                how='left'
            ).drop(columns=['idtb_equipes'])
            
            df_escala_final = pd.concat([df_escala_existente, novas_escalas_enriquecido], ignore_index=True)
            df_escala_final.drop_duplicates(subset=['idtb_escala'], keep='last', inplace=True)
            df_escala_final.to_csv(ESCALA_CSV, index=False)
            
            novos_registros_df = novas_escalas_enriquecido
            
    except Exception as e:
        st.error(f"Erro de Banco de Dados: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            
    return novos_registros_df


# --- INTERFACE DO STREAMLIT ---
st.set_page_config(page_title="Cadastro de Turnos", layout="wide")
st.title("📋 Planejador de Turnos por Contrato")
st.markdown("---")

df_historico = carregar_dados_historico()

# --- 1. CADASTRO DE VALORES PADRÃO ---
st.subheader("1. Cadastre os Valores Padrão (Modelos)")
st.info("Cadastre aqui os valores que servirão de base para preencher os custos dos turnos vindos do banco de dados.")

col_semana, col_domingo = st.columns(2)
with col_semana:
    with st.form("form_semana"):
        # ... (código do formulário de semana igual ao anterior)
        regional_semana = st.selectbox("Selecione a Regional", list(regionais_unidades.keys()), key="reg_sem")
        unidade_semana = st.selectbox("Selecione a Unidade", regionais_unidades.get(regional_semana, []), key="uni_sem")
        turno_semana = st.text_input("Turno por contrato (Dias de Semana)", key="turno_semana", help="Deve ser igual à 'descricao_tipo_prefixo' do banco de dados.")
        valor_semana = st.number_input("Valor da equipe R$ (Dias de Semana)", min_value=0.0, step=0.01, format="%.2f", key="valor_semana")
        
        if st.form_submit_button("Salvar Valor para DIAS DE SEMANA"):
            if turno_semana and unidade_semana:
                nova_linha = pd.DataFrame([{"data_registro": datetime.now(), "data_alteracao": pd.to_datetime(date.today()), "regional": regional_semana, "unidade": unidade_semana, "turno_contrato": turno_semana, "valor_equipe": valor_semana}])
                df_novo = pd.concat([df_historico, nova_linha], ignore_index=True)
                # MODIFICADO: Verifica se o salvamento deu certo antes de recarregar
                if salvar_dados_historico(df_novo):
                    st.success("✅ Valor para dias de semana salvo!")
                    st.info(f"💾 Arquivo '{HISTORICO_CSV}' atualizado com sucesso no servidor.")
                    st.rerun()

with col_domingo:
    with st.form("form_domingo"):
        # ... (código do formulário de domingo igual ao anterior)
        regional_domingo = st.selectbox("Selecione a Regional", list(regionais_unidades.keys()), key="reg_dom")
        unidade_domingo = st.selectbox("Selecione a Unidade", regionais_unidades.get(regional_domingo, []), key="uni_dom")
        turno_domingo = st.text_input("Turno por contrato (Domingos)", key="turno_domingo", help="Deve ser igual à 'descricao_tipo_prefixo' do banco de dados.")
        valor_domingo = st.number_input("Valor da equipe R$ (Domingos)", min_value=0.0, step=0.01, format="%.2f", key="valor_domingo")
        
        if st.form_submit_button("Salvar Valor para DOMINGOS"):
            if turno_domingo and unidade_domingo:
                hoje = date.today()
                dias_ate_domingo = (6 - hoje.weekday() + 7) % 7
                data_domingo = hoje + timedelta(days=dias_ate_domingo)
                nova_linha = pd.DataFrame([{"data_registro": datetime.now(), "data_alteracao": pd.to_datetime(data_domingo), "regional": regional_domingo, "unidade": unidade_domingo, "turno_contrato": turno_domingo, "valor_equipe": valor_domingo}])
                df_novo = pd.concat([df_historico, nova_linha], ignore_index=True)
                # MODIFICADO: Verifica se o salvamento deu certo antes de recarregar
                if salvar_dados_historico(df_novo):
                    st.success("✅ Valor para domingos salvo!")
                    st.info(f"💾 Arquivo '{HISTORICO_CSV}' atualizado com sucesso no servidor.")
                    st.rerun()

# --- 2. PROCESSAMENTO DOS DADOS DO BANCO ---
st.markdown("---")
st.subheader("2. Processar Turnos do Banco de Dados")
st.info("Este botão busca por novas escalas de trabalho no banco e preenche os custos com base nos modelos cadastrados.")

if st.button("Buscar Novos Turnos e Aplicar Valores", type="primary"):
    if df_historico.empty:
        st.warning("⚠️ Não há valores padrão cadastrados. Cadastre um modelo antes de processar.")
    else:
        with st.spinner("Conectando ao banco e buscando novas escalas..."):
            df_novas_escalas = atualizar_novas_escalas_do_banco()

        if df_novas_escalas.empty:
            st.success("✅ Nenhuma nova escala encontrada no banco de dados. Tudo atualizado!")
        else:
            # ... (Lógica de processamento igual à anterior)
            st.info(f"Encontrados {len(df_novas_escalas)} novos turnos. Processando...")
            novos_registros_para_historico = []
            df_novas_escalas['data_inicio'] = pd.to_datetime(df_novas_escalas['data_inicio'])

            for _, turno_db in df_novas_escalas.iterrows():
                data_do_turno = turno_db['data_inicio']
                unidade_db = turno_db['unidade']
                turno_contrato_db = turno_db.get('descricao_tipo_prefixo') 
                
                if not unidade_db or not turno_contrato_db: continue
                regional_db = get_regional_from_unidade(unidade_db)
                
                df_modelos_validos = df_historico[(df_historico['regional'] == regional_db) & (df_historico['unidade'] == unidade_db) & (df_historico['turno_contrato'] == turno_contrato_db) & (df_historico['data_alteracao'].dt.date <= data_do_turno.date())]
                if df_modelos_validos.empty: continue

                base_registro = None
                if data_do_turno.dayofweek == 6:
                    modelos_domingo = df_modelos_validos[df_modelos_validos['data_alteracao'].dt.dayofweek == 6]
                    if not modelos_domingo.empty: base_registro = modelos_domingo.sort_values('data_alteracao', ascending=False).iloc[0]
                else:
                    modelos_semana = df_modelos_validos[df_modelos_validos['data_alteracao'].dt.dayofweek < 6]
                    if not modelos_semana.empty: base_registro = modelos_semana.sort_values('data_alteracao', ascending=False).iloc[0]

                if base_registro is not None:
                    novos_registros_para_historico.append({"data_registro": datetime.now(), "data_alteracao": data_do_turno, "regional": regional_db, "unidade": unidade_db, "turno_contrato": turno_contrato_db, "valor_equipe": base_registro['valor_equipe']})
            
            if novos_registros_para_historico:
                df_preenchido = pd.DataFrame(novos_registros_para_historico)
                df_final = pd.concat([df_historico, df_preenchido], ignore_index=True)
                df_final.drop_duplicates(subset=['data_alteracao', 'regional', 'unidade', 'turno_contrato'], keep='last', inplace=True)
                
                # MODIFICADO: Verifica se o salvamento deu certo antes de recarregar
                if salvar_dados_historico(df_final):
                    st.success(f"✅ Sucesso! {len(novos_registros_para_historico)} registros foram criados/atualizados.")
                    st.info(f"💾 Arquivo '{HISTORICO_CSV}' atualizado com sucesso no servidor.")
                    st.rerun()

# --- 3. VISUALIZAÇÃO DOS DADOS ---
st.markdown("---")
st.subheader("📄 Registros de Custos Salvos (Base Final)")

if not df_historico.empty:
    # (Código de visualização e download igual ao anterior)
    df_display = df_historico.copy().sort_values(by="data_alteracao", ascending=False)
    df_display['data_registro'] = df_display['data_registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df_display['data_alteracao'] = df_display['data_alteracao'].dt.strftime('%d/%m/%Y')
    df_display['valor_equipe'] = df_display['valor_equipe'].map('R$ {:,.2f}'.format)

    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig').encode('utf-8-sig')

    csv_data = convert_df_to_csv(df_historico.sort_values(by="data_alteracao", ascending=False))

    st.download_button(
       label="📥 Baixar dados como CSV",
       data=csv_data,
       file_name='registros_de_custos.csv',
       mime='text/csv',
    )
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum registro encontrado.")