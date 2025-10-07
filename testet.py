import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- CONFIGURAÇÕES E FUNÇÕES ---

st.set_page_config(page_title="Monitoramento de Turnos", layout="wide")

# Função para carregar os dados necessários
@st.cache_data
def carregar_dados():
    try:
        df_historico = pd.read_csv("historico_alteracoes.csv")
        # Assume que o arquivo de turnos reais se chama 'turnos.csv'
        df_turnos = pd.read_csv("turnos.csv", parse_dates=["dt_inicio"]) 
        return df_historico, df_turnos
    except FileNotFoundError as e:
        st.error(f"Erro: Arquivo não encontrado. Verifique se 'historico_alteracoes.csv' e 'turnos.csv' estão na pasta. Detalhe: {e}")
        return None, None

# Função que preenche o histórico com as regras de dia de semana e domingo
def preencher_historico_diario(df_registros):
    if df_registros.empty:
        return pd.DataFrame(columns=['data_alteracao', 'regional', 'unidade', 'turno_contrato', 'valor_equipe'])

    df = df_registros.copy()
    df['data_alteracao'] = pd.to_datetime(df['data_alteracao'])
    df['tipo_dia'] = df['data_alteracao'].dt.dayofweek.apply(lambda x: 'Domingo' if x == 6 else 'DiaDeSemana')

    data_inicio = df['data_alteracao'].min()
    data_fim = pd.to_datetime(date.today()) + timedelta(days=31) # Garante que cubra o futuro
    todas_as_datas = pd.DataFrame(pd.date_range(start=data_inicio, end=data_fim), columns=['data_alteracao'])
    todas_as_datas['tipo_dia'] = todas_as_datas['data_alteracao'].dt.dayofweek.apply(lambda x: 'Domingo' if x == 6 else 'DiaDeSemana')

    combinacoes_unicas = df[['regional', 'unidade', 'turno_contrato']].drop_duplicates()
    resultados_finais = []

    for _, row in combinacoes_unicas.iterrows():
        r, u, t = row['regional'], row['unidade'], row['turno_contrato']
        df_combinacao = df[(df['regional'] == r) & (df['unidade'] == u) & (df['turno_contrato'] == t)]
        if df_combinacao.empty: continue

        df_grid = todas_as_datas.copy()
        df_grid['regional'] = r
        df_grid['unidade'] = u
        
        # O turno contratado não deve variar por data, mas por regra. Pegamos o último valor válido.
        df_grid['turno_contrato'] = t 

        df_merged = pd.merge(df_grid, df_combinacao, on=['data_alteracao', 'tipo_dia', 'regional', 'unidade', 'turno_contrato'], how='left')
        df_merged = df_merged.sort_values('data_alteracao')

        dias_semana_mask = df_merged['tipo_dia'] == 'DiaDeSemana'
        df_merged.loc[dias_semana_mask] = df_merged.loc[dias_semana_mask].ffill()
        
        domingos_mask = df_merged['tipo_dia'] == 'Domingo'
        df_merged.loc[domingos_mask] = df_merged.loc[domingos_mask].ffill()
        
        resultados_finais.append(df_merged)

    if not resultados_finais: return pd.DataFrame()
        
    df_final = pd.concat(resultados_finais)
    df_final = df_final.dropna(subset=['valor_equipe'])
    df_final = df_final[['data_alteracao', 'regional', 'unidade', 'turno_contrato']]
    
    return df_final.drop_duplicates()

# --- INTERFACE DO USUÁRIO ---

st.title("📊 Monitoramento: Contratado vs. Realizado")

df_historico, df_turnos = carregar_dados()

if df_historico is not None and df_turnos is not None:
    # Filtros na barra lateral
    st.sidebar.header("Filtros")
    
    unidades_disponiveis = sorted(df_historico['unidade'].unique())
    unidade_selecionada = st.sidebar.selectbox("Selecione a Unidade", unidades_disponiveis)

    hoje = date.today()
    ano_selecionado = st.sidebar.selectbox("Ano", range(hoje.year - 2, hoje.year + 2), index=2)
    mes_selecionado = st.sidebar.selectbox("Mês", range(1, 13), index=hoje.month - 1)

    # --- PROCESSAMENTO DOS DADOS ---

    # 1. Obter os Turnos Contratados para cada dia
    df_contratado_full = preencher_historico_diario(df_historico)
    df_contratado = df_contratado_full[df_contratado_full['unidade'] == unidade_selecionada].copy()
    # Converte para numérico, tratando erros
    df_contratado['turno_contrato'] = pd.to_numeric(df_contratado['turno_contrato'], errors='coerce').fillna(0)
    df_contratado.rename(columns={'data_alteracao': 'Data', 'turno_contrato': 'Turnos Contratados'}, inplace=True)
    df_contratado['Data'] = pd.to_datetime(df_contratado['Data']).dt.date

    # 2. Obter a Escala (Turnos Realizados) de turnos.csv
    df_realizado = df_turnos[df_turnos['unidade'] == unidade_selecionada].copy()
    df_realizado['Data'] = pd.to_datetime(df_realizado['dt_inicio']).dt.date
    # Conta turnos únicos por dia
    escala_diaria = df_realizado.groupby('Data')['idtb_turnos'].nunique().reset_index()
    escala_diaria.rename(columns={'idtb_turnos': 'Escala (Realizado)'}, inplace=True)
    escala_diaria['Data'] = pd.to_datetime(escala_diaria['Data']).dt.date

    # 3. Construir a tabela final do mês
    primeiro_dia_mes = date(ano_selecionado, mes_selecionado, 1)
    ultimo_dia_mes_num = calendar.monthrange(ano_selecionado, mes_selecionado)[1]
    ultimo_dia_mes = date(ano_selecionado, mes_selecionado, ultimo_dia_mes_num)

    # Cria um DataFrame com todos os dias do mês selecionado
    df_mes = pd.DataFrame(pd.date_range(start=primeiro_dia_mes, end=ultimo_dia_mes), columns=['Data'])
    df_mes['Data'] = pd.to_datetime(df_mes['Data']).dt.date

    # Juntar os dados
    df_final = pd.merge(df_mes, df_contratado[['Data', 'Turnos Contratados']], on='Data', how='left')
    df_final = pd.merge(df_final, escala_diaria[['Data', 'Escala (Realizado)']], on='Data', how='left')

    # Preencher NaNs e garantir que a coluna 'Turnos Contratados' seja preenchida com o último valor válido
    df_final['Turnos Contratados'] = df_final['Turnos Contratados'].ffill().fillna(0)
    df_final['Escala (Realizado)'] = df_final['Escala (Realizado)'].fillna(0)
    df_final = df_final.astype({'Turnos Contratados': int, 'Escala (Realizado)': int})

    # 4. Calcular os Turnos Abertos
    df_final['Turnos Abertos (Diferença)'] = df_final['Turnos Contratados'] - df_final['Escala (Realizado)']
    
    # Formatação para exibição
    df_display = df_final.copy()
    df_display.rename(columns={'Data': 'Dia a Dia'}, inplace=True)
    df_display['Dia a Dia'] = pd.to_datetime(df_display['Dia a Dia']).dt.strftime('%d/%m/%Y')

    st.subheader(f"Análise para a Unidade: {unidade_selecionada}")
    st.write(f"Período: {mes_selecionado:02d}/{ano_selecionado}")

    # --- EXIBIÇÃO DA TABELA ---
    st.dataframe(df_display, use_container_width=True)