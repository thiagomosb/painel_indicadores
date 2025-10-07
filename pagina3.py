import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
def app():
    # Arquivo onde os dados serão salvos
    ARQUIVO_CSV = "historico_alteracoes copy.csv"

    # Dicionário de regionais e unidades
    regionais_unidades = {
        "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"],
        "REGIONAL RIO VERDE": ["RIO VERDE - GO"],
        "REGIONAL TO": ["PALMAS - TO"],
        "REGIONAL MT": ["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]
    }

    # Configuração da página
    st.set_page_config(page_title="Cadastro de Turnos", layout="wide")
    st.title("📋 Planejador de Turnos por Contrato")
    st.markdown("---")

    # --- Carrega os dados existentes ---
    try:
        df_historico = pd.read_csv(ARQUIVO_CSV)
    except FileNotFoundError:
        df_historico = pd.DataFrame(columns=["data_registro", "data_alteracao", "regional", "unidade", "turno_contrato", "valor_equipe"])

    # --- Seleção de Contrato (comum aos dois formulários) ---
    st.subheader("1. Selecione o Contrato")
    col_reg, col_uni = st.columns(2)
    with col_reg:
        regional = st.selectbox("Selecione a Regional", list(regionais_unidades.keys()))
    with col_uni:
        unidades_opcoes = regionais_unidades.get(regional, [])
        unidade = st.selectbox("Selecione a Unidade", unidades_opcoes)

    st.markdown("---")
    st.subheader("2. Cadastre os Valores Padrão")

    ### NOVOS FORMULÁRIOS: Um para Dias de Semana, outro para Domingos ###
    col_semana, col_domingo = st.columns(2)

    # Formulário para Dias de Semana
    with col_semana:
        with st.form("form_semana"):
            st.markdown("<h5 style='text-align: center;'>Dias de Semana (Seg a Sáb)</h5>", unsafe_allow_html=True)
            turno_semana = st.text_input("Turno por contrato (Dias de Semana)")
            valor_semana = st.number_input("Valor da equipe R$ (Dias de Semana)", min_value=0.0, step=0.01, format="%.2f")
            
            submitted_semana = st.form_submit_button("Salvar Valor para DIAS DE SEMANA")
            if submitted_semana:
                # Salva com a data de hoje para ser o registro mais recente
                data_hoje = date.today().strftime("%Y-%m-%d")
                nova_linha = pd.DataFrame([{
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "data_alteracao": data_hoje,
                    "regional": regional, "unidade": unidade,
                    "turno_contrato": turno_semana, "valor_equipe": valor_semana
                }])
                
                df_novo = pd.concat([df_historico, nova_linha], ignore_index=True)
                df_novo.to_csv(ARQUIVO_CSV, index=False)
                st.success("✅ Valor para dias de semana salvo!")
                st.rerun()

    # Formulário para Domingos
    with col_domingo:
        with st.form("form_domingo"):
            st.markdown("<h5 style='text-align: center;'>Apenas Domingos</h5>", unsafe_allow_html=True)
            turno_domingo = st.text_input("Turno por contrato (Domingos)")
            valor_domingo = st.number_input("Valor da equipe R$ (Domingos)", min_value=0.0, step=0.01, format="%.2f")
            
            submitted_domingo = st.form_submit_button("Salvar Valor para DOMINGOS")
            if submitted_domingo:
                # Salva com a data do próximo domingo para ser o registro mais recente de domingo
                hoje = date.today()
                dias_ate_domingo = (6 - hoje.weekday() + 7) % 7
                data_domingo = hoje + timedelta(days=dias_ate_domingo)
                
                nova_linha = pd.DataFrame([{
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "data_alteracao": data_domingo.strftime("%Y-%m-%d"),
                    "regional": regional, "unidade": unidade,
                    "turno_contrato": turno_domingo, "valor_equipe": valor_domingo
                }])

                df_novo = pd.concat([df_historico, nova_linha], ignore_index=True)
                df_novo.to_csv(ARQUIVO_CSV, index=False)
                st.success("✅ Valor para domingos salvo!")
                st.rerun()

    # --- Ação de Preenchimento do Mês ---
    st.markdown("---")
    st.subheader("3. Gerar Calendário do Mês")
    st.info("Após salvar os valores padrão para dias de semana e domingos, clique aqui para preencher o calendário do mês atual.")

    if st.button("Preencher Mês Atual com Últimos Dados", type="primary"):
        if df_historico.empty:
            st.warning("⚠️ Não há registros para usar como base.")
        else:
            with st.spinner("Processando e preenchendo o mês..."):
                df_para_processar = df_historico.copy()
                df_para_processar['data_alteracao'] = pd.to_datetime(df_para_processar['data_alteracao'])

                hoje = date.today()
                primeiro_dia_mes = hoje.replace(day=1)
                ultimo_dia_mes_num = calendar.monthrange(hoje.year, hoje.month)[1]
                ultimo_dia_mes = hoje.replace(day=ultimo_dia_mes_num)
                datas_do_mes = pd.date_range(start=primeiro_dia_mes, end=ultimo_dia_mes)
                
                combinacoes_unicas = df_para_processar[['regional', 'unidade', 'turno_contrato']].drop_duplicates()
                novos_registros = []

                for _, row in combinacoes_unicas.iterrows():
                    r, u, t = row['regional'], row['unidade'], row['turno_contrato']
                    df_grupo = df_para_processar[(df_para_processar['regional'] == r) & (df_para_processar['unidade'] == u) & (df_para_processar['turno_contrato'] == t)]

                    ultimo_dia_semana = df_grupo[df_grupo['data_alteracao'].dt.dayofweek < 6].sort_values('data_alteracao', ascending=False).iloc[:1]
                    ultimo_domingo = df_grupo[df_grupo['data_alteracao'].dt.dayofweek == 6].sort_values('data_alteracao', ascending=False).iloc[:1]

                    for dia in datas_do_mes:
                        base_registro = None
                        if dia.dayofweek == 6 and not ultimo_domingo.empty: # Se é domingo
                            base_registro = ultimo_domingo.iloc[0].to_dict()
                        elif dia.dayofweek < 6 and not ultimo_dia_semana.empty: # Se é dia de semana
                            base_registro = ultimo_dia_semana.iloc[0].to_dict()

                        if base_registro:
                            base_registro['data_alteracao'] = dia.strftime("%Y-%m-%d")
                            novos_registros.append(base_registro)
                
                if novos_registros:
                    df_preenchido = pd.DataFrame(novos_registros)
                    df_final = pd.concat([df_historico, df_preenchido], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['data_alteracao', 'regional', 'unidade', 'turno_contrato'], keep='first')
                    df_final.sort_values(by=['regional', 'unidade', 'turno_contrato', 'data_alteracao'], inplace=True)
                    
                    df_final.to_csv(ARQUIVO_CSV, index=False)
                    st.success("✅ Mês atual preenchido com sucesso!")
                    st.rerun()
                else:
                    st.warning("Não foram encontrados dados de base para preencher o mês.")

    # --- Exibe os dados salvos no arquivo ---
    st.markdown("---")
    st.subheader("📄 Registros Salvos (Base de Dados)")
    if not df_historico.empty:
        df_display = df_historico.copy()
        df_display['data_alteracao'] = pd.to_datetime(df_display['data_alteracao']).dt.strftime('%d/%m/%Y')
        df_display['valor_equipe'] = df_display['valor_equipe'].map('R$ {:,.2f}'.format)
        st.dataframe(df_display.sort_values(by="data_alteracao", ascending=False), use_container_width=True)
    else:
        st.info("Nenhum registro encontrado. Cadastre um novo valor para começar.")
       
# Chamada principal
if __name__ == "__main__":
    app()        