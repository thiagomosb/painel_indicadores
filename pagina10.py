import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import subprocess
import os
from streamlit_echarts import st_echarts
import numpy as np
from io import BytesIO
import sys
from banco_escala_turnos import exportar_dados_para_csv

# --- FUNÇÕES DE ATUALIZAÇÃO E CARGA ---

def atualizar_dados():
    """
    Executa a função de exportação de dados do banco e atualiza os CSVs.
    """
    st.cache_data.clear()
    try:
        exportar_dados_para_csv()
        return True, "Dados do banco atualizados com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar dados: {str(e)}"

@st.cache_data
def carregar_dados():
    """
    Carrega os dados dos arquivos CSV, realiza a limpeza e preparação inicial.
    """
    try:
        df_escala = pd.read_csv("data/escala_nova.csv")
        df_turnos = pd.read_csv("data/turnos_newmars.csv")
        
        try:
            df_contrato = pd.read_csv("data/Contratos.csv")
        except FileNotFoundError:
            st.warning("Arquivo 'Contratos.csv' não encontrado na pasta 'data/'. Os dados de contrato não serão exibidos.")
            df_contrato = pd.DataFrame()

        # --- PREPARAÇÃO E LIMPEZA DOS DADOS ---
        df_escala['data_inicio'] = pd.to_datetime(df_escala['data_inicio'], errors='coerce')
        df_turnos['dt_inicio'] = pd.to_datetime(df_turnos['dt_inicio'], errors='coerce')
        df_turnos.rename(columns={'dt_inicio': 'data_inicio'}, inplace=True)
        
        df_escala['prefixo'] = df_escala['prefixo'].astype(str).str.strip().str.upper()
        df_turnos['prefixo'] = df_turnos['prefixo'].astype(str).str.strip().str.upper()

        if not df_contrato.empty:
            # Renomeia as colunas do CSV para o padrão do script
            df_contrato.rename(columns={'BASE BI': 'unidade', 'PREFIXO': 'prefixo', 'TIPO DE EQUIPE': 'descricao_tipo_prefixo'}, inplace=True)
            df_contrato['prefixo'] = df_contrato['prefixo'].astype(str).str.strip().str.upper()
            
            # 1. MAPA DE UNIDADE (como já existia)
            mapa_prefixo_unidade = df_contrato[['prefixo', 'unidade']].drop_duplicates('prefixo').dropna()
            
            if 'unidade' in df_escala.columns:
                df_escala = df_escala.drop(columns=['unidade'])
            if 'unidade' in df_turnos.columns:
                df_turnos = df_turnos.drop(columns=['unidade'])

            df_escala = pd.merge(df_escala, mapa_prefixo_unidade, on='prefixo', how='left')
            df_turnos = pd.merge(df_turnos, mapa_prefixo_unidade, on='prefixo', how='left')

            df_escala['unidade'].fillna('Não Alocado no Contrato', inplace=True)
            df_turnos['unidade'].fillna('Não Alocado no Contrato', inplace=True)
            
            # 2. NOVA LÓGICA: USAR Contratos.csv COMO REFERÊNCIA PARA TIPO DE EQUIPE
            if 'descricao_tipo_prefixo' in df_contrato.columns:
                # Cria o mapa de referência a partir de Contratos.csv
                mapa_tipo_prefixo = df_contrato[['prefixo', 'descricao_tipo_prefixo']].drop_duplicates('prefixo').dropna()
                
                # Remove a coluna antiga de tipo de equipe dos dataframes de turnos e escala para evitar conflitos
                if 'descricao_tipo_prefixo' in df_turnos.columns:
                    df_turnos = df_turnos.drop(columns=['descricao_tipo_prefixo'])
                if 'descricao_tipo_prefixo' in df_escala.columns:
                    df_escala = df_escala.drop(columns=['descricao_tipo_prefixo'])

                # Aplica o mapa de referência do contrato em AMBOS os dataframes
                df_escala = pd.merge(df_escala, mapa_tipo_prefixo, on='prefixo', how='left')
                df_turnos = pd.merge(df_turnos, mapa_tipo_prefixo, on='prefixo', how='left')
                
                # Preenche valores nulos para equipes que não foram encontradas no mapa do contrato
                df_escala['descricao_tipo_prefixo'].fillna('Tipo Não Mapeado no Contrato', inplace=True)
                df_turnos['descricao_tipo_prefixo'].fillna('Tipo Não Mapeado no Contrato', inplace=True)
            else:
                st.warning("A coluna 'TIPO DE EQUIPE' não foi encontrada em 'Contratos.csv'. Usando a lógica antiga.")
                mapa_tipo_prefixo = df_turnos[['prefixo', 'descricao_tipo_prefixo']].drop_duplicates('prefixo').dropna()
                df_escala = pd.merge(df_escala, mapa_tipo_prefixo, on='prefixo', how='left')
                df_escala['descricao_tipo_prefixo'].fillna('Tipo Não Encontrado', inplace=True)
        else:
            # Lógica antiga caso Contratos.csv não seja carregado
            mapa_tipo_prefixo = df_turnos[['prefixo', 'descricao_tipo_prefixo']].drop_duplicates('prefixo').dropna()
            df_escala = pd.merge(df_escala, mapa_tipo_prefixo, on='prefixo', how='left')
            df_escala['descricao_tipo_prefixo'].fillna('Tipo Não Encontrado', inplace=True)


        df_escala['id_equipe'] = df_escala['id_equipe'].astype(str)
        df_escala.dropna(subset=['data_inicio', 'prefixo', 'id_equipe', 'unidade'], inplace=True)
        df_turnos.dropna(subset=['data_inicio', 'prefixo', 'unidade'], inplace=True)
        df_escala = df_escala[df_escala['prefixo'] != '']
        df_turnos = df_turnos[df_turnos['prefixo'] != '']

        return df_escala, df_turnos, df_contrato

    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao carregar os dados: {e}")
        return None, None, None


def classificar_regional(df):
    df_copia = df.copy()
    condicoes = [
        df_copia['prefixo'].isin(["MORO001M", "MORO002M", "MORO003M", "MORO004M", "MORO005M", "MORO006M", "MORO007M", "MORO008M", "MORO009M", "MORO010M"]),
        df_copia['unidade'] == "RIO VERDE - GO",
        df_copia['unidade'] == "PALMAS - TO",
        df_copia['unidade'].isin(["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]),
        df_copia['unidade'].isin(["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"])
    ]
    resultados = ["SATELITE MORRINHO", "SATELITE RIO VERDE", "ENERGISA TO", "ENERGISA MT", "ANCORA MORRINHOS"]
    df_copia['REGIONAIS'] = np.select(condicoes, resultados, default='Não Classificado')
    return df_copia

def classificar_coordenacao(df):
    df_copia = df.copy()
    condicoes = [
        (df_copia['REGIONAIS'] == "ANCORA MORRINHOS") & (df_copia['descricao_tipo_prefixo'].isin(["PLANTÃO 16 HORAS 4X4", "PLANTÃO LEVE 8 HORAS TRIO", "PLANTÃO 8 HORAS TRIO 4X4", "PLANTÃO 8 HORAS MINI SKY", "PLANTÃO 16 HORAS MINI SKY", "LIGAÇÃO NOVA LEVE", "CORTE E RELIGAÇÃO LEVE", "CORTE E RELIGAÇÃO MOTO"])),
        (df_copia['REGIONAIS'] == "ANCORA MORRINHOS") & (df_copia['descricao_tipo_prefixo'].isin(["INSPECAO LEVE", "INSPECAO 4X4"])),
        (df_copia['REGIONAIS'] == "ANCORA MORRINHOS") & (df_copia['descricao_tipo_prefixo'].isin(["LINHA VIVA 3 HOMENS CESTO SIMPLES", "LINHA VIVA 4 HOMENS CESTO DUPLO", "MANUTENÇÃO LINHA MORTA 5 ELEMENTOS", "MANUTENÇÃO LINHA MORTA 3 ELEMENTOS", "PODA 4 HOMENS", "PODA MID SKY", "PODA - RECOLHIMENTO"])),
        (df_copia['REGIONAIS'] == "ANCORA MORRINHOS") & (df_copia['descricao_tipo_prefixo'] == "CONSTRUÇÃO 7 ELEMENTOS"),
        (df_copia['REGIONAIS'] == "SATELITE MORRINHO") & (df_copia['descricao_tipo_prefixo'].isin(["CONSTRUÇÃO 7 ELEMENTOS", "LINHA VIVA 4 HOMENS CESTO DUPLO"])),
        (df_copia['REGIONAIS'] == "SATELITE RIO VERDE") & (df_copia['descricao_tipo_prefixo'].isin(["CONSTRUÇÃO 7 ELEMENTOS", "LINHA VIVA 4 HOMENS CESTO DUPLO","LINHA VIVA 3 HOMENS CESTO SIMPLES","MANUTENÇÃO LINHA MORTA 2 ELEMENTOS"])),
        (df_copia['REGIONAIS'] == "ENERGISA MT") & (df_copia['descricao_tipo_prefixo'].isin(["PLANTÃO LEVE 8 HORAS TRIO", "PLANTÃO 8 HORAS MINI SKY", "LIGAÇÃO NOVA LEVE", "CORTE E RELIGAÇÃO LEVE"])),
        (df_copia['REGIONAIS'] == "ENERGISA MT") & (df_copia['descricao_tipo_prefixo'].isin(["LINHA VIVA 3 HOMENS CESTO DUPLO", "MANUTENÇÃO LINHA MORTA 3 ELEMENTOS", "CONSTRUÇÃO 7 ELEMENTOS"])),
        (df_copia['REGIONAIS'] == "ENERGISA TO") & (df_copia['descricao_tipo_prefixo'].isin(["LINHA VIVA 3 HOMENS CESTO DUPLO", "LINHA VIVA 3 HOMENS CESTO SIMPLES", "MANUTENÇÃO LINHA MORTA 5 ELEMENTOS", "CONSTRUÇÃO 7 ELEMENTOS", "MANUTENÇÃO LINHA MORTA 3 ELEMENTOS", "MANUTENÇÃO LINHA MORTA 2 ELEMENTOS"]))
    ]
    resultados = ["STC", "PERDAS", "MANUTENÇÃO", "CONSTRUÇÃO", "CONSTRUÇÃO", "CONSTRUÇÃO", "STC", "C&M", "C&M"]
    df_copia['COORDENACAO'] = np.select(condicoes, resultados, default='Não Classificado')
    return df_copia
def app():
    
    df_escala, df_turnos, df_contrato = carregar_dados()
    if df_escala is None or df_turnos is None:
        st.error("Falha ao carregar dados base. O aplicativo não pode continuar.")
        st.stop()
    
    df_escala_classificado = classificar_regional(df_escala)
    df_escala_classificado = classificar_coordenacao(df_escala_classificado)
    df_turnos_classificado = classificar_regional(df_turnos)
    df_turnos_classificado = classificar_coordenacao(df_turnos_classificado)
    
    if not df_contrato.empty:
        df_contrato_classificado = classificar_regional(df_contrato)
        df_contrato_classificado = classificar_coordenacao(df_contrato_classificado)
    else:
        df_contrato_classificado = pd.DataFrame()


    with st.sidebar:
        st.logo('https://www.dolpengenharia.com.br/wp-content/uploads/2021/01/logotipo-definitivo-250614.png')
        
        if st.button("🔄 Atualizar Dados", type="primary"):
            with st.spinner("Executando script do banco de dados..."):
                sucesso, mensagem = atualizar_dados()
                if sucesso:
                    with open("ultima_atualizacao.txt", "w", encoding="utf-8") as f:
                        f.write(datetime.now().strftime("%d/%m/%Y %H:%M"))
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

        try:
            if os.path.exists("ultima_atualizacao.txt"):
                with open("ultima_atualizacao.txt", "r", encoding='utf-8') as f:
                    ultima_atualizacao = f.read()
                st.info(f"📅 Última atualização: {ultima_atualizacao}")
            else:
                st.warning("📅 Dados não atualizados nesta sessão.")
        except Exception as e:
            st.warning(f"Erro ao verificar data: {e}")

        st.header("Filtros")
        
        st.write("**Período**")
        
        data_inicio_fixa = date(2025, 9, 1)

        if not df_turnos_classificado.empty:
            max_data = df_turnos_classificado['data_inicio'].max().date()
            if max_data < data_inicio_fixa:
                max_data = data_inicio_fixa
        else: 
            max_data = date.today()

        data_selecionada = st.date_input(
            "Período", 
            value=(data_inicio_fixa, max_data),
            min_value=data_inicio_fixa,      
            max_value=max_data,          
            label_visibility="collapsed"
        )
        st.markdown("---")
        
        if len(data_selecionada) == 2: 
            start_date, end_date = data_selecionada
        else: 
            start_date, end_date = data_selecionada[0], data_selecionada[0]
        
        regionais_unidades = {
            "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"]
        }
        opcoes_regionais = list(regionais_unidades.keys())
        regionais_selecionadas = st.multiselect("Regional", options=opcoes_regionais, default=opcoes_regionais)
        if not regionais_selecionadas:
            unidades_para_mostrar = sorted(list(set([unidade for lista in regionais_unidades.values() for unidade in lista])))
        else:
            unidades_para_mostrar = sorted(list(set([unidade for regional in regionais_selecionadas for unidade in regionais_unidades[regional]])))
        
        unidade_selecionada = st.multiselect("Unidade", options=unidades_para_mostrar, default=unidades_para_mostrar)
        st.markdown("---")

        if not df_contrato_classificado.empty:
            coord_disponiveis = sorted(df_contrato_classificado['COORDENACAO'].dropna().unique().tolist())
            tipos_disponiveis = sorted(df_contrato_classificado['descricao_tipo_prefixo'].dropna().unique().tolist())
        else:
            coord_disponiveis = sorted(pd.unique(list(df_escala_classificado['COORDENACAO'].unique()) + list(df_turnos_classificado['COORDENACAO'].unique())))
            tipos_disponiveis = sorted(pd.unique(list(df_escala_classificado['descricao_tipo_prefixo'].unique()) + list(df_turnos_classificado['descricao_tipo_prefixo'].unique())))

        coord_selecionada = st.multiselect("Coordenação", options=coord_disponiveis, default=coord_disponiveis)
        tipo_selecionado = st.multiselect("Tipo de Equipe", options=tipos_disponiveis, default=tipos_disponiveis)
        
        escala_selecionada = []
        if not df_contrato_classificado.empty and 'ESCALA' in df_contrato_classificado.columns:
            df_contrato_classificado['ESCALA'] = df_contrato_classificado['ESCALA'].astype(str)
            escala_disponiveis = sorted(df_contrato_classificado['ESCALA'].dropna().unique())
            escala_selecionada = st.multiselect("Dias na Escala (Contrato)", options=escala_disponiveis, default=escala_disponiveis)
        
    # --- LÓGICA DE FILTRAGEM CENTRALIZADA E CORRIGIDA ---

    # 1. Filtra o DF de Contrato com todos os filtros da barra lateral
    df_contrato_filtrado = pd.DataFrame()
    if not df_contrato_classificado.empty:
        df_contrato_filtrado_base = df_contrato_classificado[
            (df_contrato_classificado['unidade'].isin(unidade_selecionada)) &
            (df_contrato_classificado['COORDENACAO'].isin(coord_selecionada)) &
            (df_contrato_classificado['descricao_tipo_prefixo'].isin(tipo_selecionado))
        ]
        # Aplica o filtro de Dias na Escala
        if escala_selecionada:
            df_contrato_filtrado = df_contrato_filtrado_base[df_contrato_filtrado_base['ESCALA'].isin(escala_selecionada)]
        else:
            df_contrato_filtrado = df_contrato_filtrado_base

    # 2. Obtém a lista de prefixos válidos DEPOIS de todos os filtros serem aplicados no contrato.
    # Esta lista será a "fonte da verdade" para os outros dataframes.
    prefixos_validos = []
    deve_filtrar_por_prefixo = not df_contrato_classificado.empty # Flag para saber se o filtro de contrato está ativo
    if deve_filtrar_por_prefixo:
        prefixos_validos = df_contrato_filtrado['prefixo'].unique()

    # 3. Filtra os DataFrames de escala e turnos usando os filtros comuns
    df_escala_filtrado = df_escala_classificado[
        (df_escala_classificado['unidade'].isin(unidade_selecionada)) &
        (df_escala_classificado['data_inicio'].dt.date >= start_date) &
        (df_escala_classificado['data_inicio'].dt.date <= end_date) &
        (df_escala_classificado['descricao_tipo_prefixo'].isin(tipo_selecionado)) &
        (df_escala_classificado['COORDENACAO'].isin(coord_selecionada))
    ]
    df_turnos_filtrado = df_turnos_classificado[
        (df_turnos_classificado['unidade'].isin(unidade_selecionada)) &
        (df_turnos_classificado['data_inicio'].dt.date >= start_date) &
        (df_turnos_classificado['data_inicio'].dt.date <= end_date) &
        (df_turnos_classificado['descricao_tipo_prefixo'].isin(tipo_selecionado)) &
        (df_turnos_classificado['COORDENACAO'].isin(coord_selecionada))
    ]

    # 4. Aplica o filtro final de prefixos (derivado do contrato) aos dataframes de escala e turnos
    if deve_filtrar_por_prefixo:
        df_escala_filtrado = df_escala_filtrado[df_escala_filtrado['prefixo'].isin(prefixos_validos)]
        df_turnos_filtrado = df_turnos_filtrado[df_turnos_filtrado['prefixo'].isin(prefixos_validos)]
    
    st.write(", ".join(unidade_selecionada))      

    # Gera o range de datas do filtro e conta os domingos para os cálculos
    date_range = pd.date_range(start_date, end_date)
    numero_dias_filtro = len(date_range)
    num_sundays = len([d for d in date_range if d.dayofweek == 6])
    num_non_sundays = numero_dias_filtro - num_sundays
    
    tab1, tab2, tab3 = st.tabs(["ESCALA x TURNOS x CONTRATOS","TURNOS x ESCALA DETALHE", "COI DE ABERTURA DE TURNOS"])

    with tab2:
        
        st.markdown(
                """
                <h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>
                Contratado x Escalado x Turnos Abertos - Regional
                </h2>
                """, unsafe_allow_html=True)

        # --- LÓGICA DE SOMA TOTAL APLICADA A TODAS AS MÉTRICAS ---
        soma_contrato_regional = pd.Series(dtype='float64')
        if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
            df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')
            contratos_30_regional = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30].groupby('REGIONAIS')['prefixo'].nunique()
            contratos_24_regional = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24].groupby('REGIONAIS')['prefixo'].nunique()
            df_agg = pd.DataFrame({'count_30': contratos_30_regional, 'count_24': contratos_24_regional}).fillna(0)
            soma_contrato_regional = (df_agg['count_30'] * numero_dias_filtro) + (df_agg['count_24'] * num_non_sundays)

        soma_escala_regional = df_escala_filtrado.groupby(['REGIONAIS', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('REGIONAIS').sum()
        soma_turnos_regional = df_turnos_filtrado.groupby(['REGIONAIS', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('REGIONAIS').sum()

        df_comparativo_regional = pd.DataFrame({
            'Turnos Contratados': soma_contrato_regional,
            'Escala sgd': soma_escala_regional, 
            'Turnos Abertos NewMars': soma_turnos_regional
        }).reset_index().fillna(0).rename(columns={'index': 'REGIONAIS'})

        df_comparativo_regional = df_comparativo_regional.sort_values(by=['Turnos Contratados', 'Escala sgd'], ascending=False)

        fig_regional_tab1 = px.bar(df_comparativo_regional, x='REGIONAIS', y=['Turnos Contratados', 'Escala sgd', 'Turnos Abertos NewMars'], 
                                    barmode='group', text_auto=True, 
                                    labels={'REGIONAIS': '', 'value': '', 'variable': 'Fonte'},
                                    color_discrete_map={'Turnos Contratados': '#36b9cc', 'Escala sgd': '#4e73df', 'Turnos Abertos NewMars': '#1cc88a'})

        fig_regional_tab1.update_traces(textfont=dict(color='black', size=14), hovertemplate='%{data.name}: <b>%{y}</b><extra></extra>') 
        fig_regional_tab1.update_layout(legend_title_text='', xaxis=dict(tickfont=dict(color='black', size=12)), yaxis=dict(showticklabels=False),
                                            hoverlabel=dict(bgcolor="white", font_size=16, font_color="black"))
        st.plotly_chart(fig_regional_tab1, use_container_width=True, key="regional_chart_prefixo_sum")
        st.markdown("---")

        st.markdown(
                """
                <h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>
                Contratado x Escalado x Turnos Abertos - Coordenação
                </h2>
                """, unsafe_allow_html=True)

        soma_contrato_coord = pd.Series(dtype='float64')
        if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
            df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')
            contratos_30_coord = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30].groupby('COORDENACAO')['prefixo'].nunique()
            contratos_24_coord = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24].groupby('COORDENACAO')['prefixo'].nunique()
            df_agg_coord = pd.DataFrame({'count_30': contratos_30_coord, 'count_24': contratos_24_coord}).fillna(0)
            soma_contrato_coord = (df_agg_coord['count_30'] * numero_dias_filtro) + (df_agg_coord['count_24'] * num_non_sundays)

        soma_escala_coord = df_escala_filtrado.groupby(['COORDENACAO', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('COORDENACAO').sum()
        soma_turnos_coord = df_turnos_filtrado.groupby(['COORDENACAO', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('COORDENACAO').sum()
        
        df_comparativo_coord = pd.DataFrame({
            'Turnos Contratados': soma_contrato_coord,
            'Escala sgd': soma_escala_coord, 
            'Turnos Abertos NewMars': soma_turnos_coord
            }).reset_index().fillna(0)
            
        df_comparativo_coord = df_comparativo_coord[df_comparativo_coord['COORDENACAO'] != 'Não Classificado']
        df_comparativo_coord = df_comparativo_coord.sort_values(by=['Turnos Contratados', 'Escala sgd'], ascending=False)

        fig_coord = px.bar(df_comparativo_coord, x='COORDENACAO', y=['Turnos Contratados', 'Escala sgd', 'Turnos Abertos NewMars'], 
                            barmode='group', text_auto=True, 
                            labels={'COORDENACAO': '', 'value': '', 'variable': 'Fonte'},
                            color_discrete_map={'Turnos Contratados': '#36b9cc', 'Escala sgd': '#4e73df', 'Turnos Abertos NewMars': '#1cc88a'})

        fig_coord.update_traces(textfont=dict(color='black', size=14), hovertemplate='%{data.name}: <b>%{y}</b><extra></extra>')
        fig_coord.update_layout(legend_title_text='', xaxis=dict(tickfont=dict(color='black', size=12)), yaxis=dict(showticklabels=False),
                                hoverlabel=dict(bgcolor="white", font_size=16, font_color="black"))
        st.plotly_chart(fig_coord, use_container_width=True, key="coord_chart_prefixo_sum")
        st.markdown("---")

        st.markdown(
                """
                <h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>
                Contratado x Escalado x Turnos Abertos - Tipo de Equipes
                </h2>
                """, unsafe_allow_html=True)
                
        soma_contrato_tipo = pd.Series(dtype='float64')
        if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
            df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')
            contratos_30_tipo = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30].groupby('descricao_tipo_prefixo')['prefixo'].nunique()
            contratos_24_tipo = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24].groupby('descricao_tipo_prefixo')['prefixo'].nunique()
            df_agg_tipo = pd.DataFrame({'count_30': contratos_30_tipo, 'count_24': contratos_24_tipo}).fillna(0)
            soma_contrato_tipo = (df_agg_tipo['count_30'] * numero_dias_filtro) + (df_agg_tipo['count_24'] * num_non_sundays)

        soma_escala_tipo = df_escala_filtrado.groupby(['descricao_tipo_prefixo', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('descricao_tipo_prefixo').sum()
        soma_turnos_tipo = df_turnos_filtrado.groupby(['descricao_tipo_prefixo', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().groupby('descricao_tipo_prefixo').sum()
        
        df_comparativo_tipo = pd.DataFrame({
            'Turnos Contratados': soma_contrato_tipo,
            'Escala sgd': soma_escala_tipo, 
            'Turnos Abertos NewMars': soma_turnos_tipo
            }).reset_index().fillna(0)

        df_comparativo_tipo = df_comparativo_tipo.sort_values(by=['Turnos Contratados', 'Escala sgd'], ascending=False)

        fig_tipo_prefixo = px.bar(df_comparativo_tipo, x='descricao_tipo_prefixo', y=['Turnos Contratados', 'Escala sgd', 'Turnos Abertos NewMars'], 
                                    barmode='group', text_auto=True, 
                                    labels={'descricao_tipo_prefixo': '', 'value': '', 'variable': 'Fonte'}, 
                                    template='plotly_white',
                                    color_discrete_map={'Turnos Contratados': '#36b9cc', 'Escala sgd': '#4e73df', 'Turnos Abertos NewMars': '#1cc88a'})

        fig_tipo_prefixo.update_traces(textfont=dict(color='black', size=14), hovertemplate='%{data.name}: <b>%{y}</b><extra></extra>')
        fig_tipo_prefixo.update_layout(legend_title_text='', xaxis=dict(tickfont=dict(color='black', size=12)), yaxis=dict(showticklabels=False),
                                        hoverlabel=dict(bgcolor="white", font_size=16, font_color="black"))
        st.plotly_chart(fig_tipo_prefixo, use_container_width=True, key="tipo_prefixo_chart_prefixo_sum")
        st.markdown("---")

    with tab1:
        
        if not df_escala_filtrado.empty or not df_turnos_filtrado.empty:
            
            st.markdown(
                """
                <h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>
                Escala x Turnos Abertos x Turnos contratados - Geral
                </h2>
                """, unsafe_allow_html=True)
            
            escala_por_dia_t2 = df_escala_filtrado.groupby(df_escala_filtrado['data_inicio'].dt.date)['prefixo'].nunique().reset_index()
            escala_por_dia_t2.rename(columns={'prefixo': 'Escala sgd'}, inplace=True)
            
            turnos_por_dia_t2 = df_turnos_filtrado.groupby(df_turnos_filtrado['data_inicio'].dt.date)['prefixo'].nunique().reset_index()
            turnos_por_dia_t2.rename(columns={'prefixo': 'Turnos Abertos NewMars'}, inplace=True)

            # --- LÓGICA DO CONTRATO POR DIA ATUALIZADA ---
            contrato_por_dia_t2 = pd.DataFrame()
            if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
                df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')

                total_contratos_30 = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30]['prefixo'].nunique()
                total_contratos_24 = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24]['prefixo'].nunique()

                daily_contract_counts = []
                for d in date_range:
                    if d.dayofweek == 6:  # Domingo
                        count = total_contratos_30
                    else:
                        count = total_contratos_30 + total_contratos_24
                    daily_contract_counts.append({'data_inicio': d.date(), 'Turnos Contratados': count})
                
                if daily_contract_counts:
                    contrato_por_dia_t2 = pd.DataFrame(daily_contract_counts)
            
            df_comparativo_diario_t2 = pd.merge(escala_por_dia_t2, turnos_por_dia_t2, on='data_inicio', how='outer')
            if not contrato_por_dia_t2.empty:
                df_comparativo_diario_t2 = pd.merge(df_comparativo_diario_t2, contrato_por_dia_t2, on='data_inicio', how='outer')
            
            df_comparativo_diario_t2 = df_comparativo_diario_t2.fillna(0)
            df_comparativo_diario_t2.rename(columns={'data_inicio': 'Data'}, inplace=True)

            options_diario = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ['Turnos Contratados','Escala sgd', 'Turnos Abertos NewMars']},
                "xAxis": {"type": "category", "data": df_comparativo_diario_t2['Data'].astype(str).tolist(), "axisLabel": {"color": "black"}},
                "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"show": False}},
                "series": [
                    {"name": 'Turnos Contratados', "type": 'bar', "data": df_comparativo_diario_t2['Turnos Contratados'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#36b9cc"}},
                    {"name": 'Escala sgd', "type": 'bar', "data": df_comparativo_diario_t2['Escala sgd'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#4e73df"}},
                    {"name": 'Turnos Abertos NewMars', "type": 'bar', "data": df_comparativo_diario_t2['Turnos Abertos NewMars'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#1cc88a"}},
                ]
            }
            st_echarts(options=options_diario, height="500px")
            st.markdown("---")

            st.markdown("<h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>Escala x Turnos Abertos x Turnos contratados - Regional</h2>", unsafe_allow_html=True)
            novas_regionais_map = {unidade: regional for regional, unidades in regionais_unidades.items() for unidade in unidades}
            df_escala_filtrado['regional_nova'] = df_escala_filtrado['unidade'].map(novas_regionais_map)
            df_turnos_filtrado['regional_nova'] = df_turnos_filtrado['unidade'].map(novas_regionais_map)
            if not df_contrato_filtrado.empty:
                df_contrato_filtrado['regional_nova'] = df_contrato_filtrado['unidade'].map(novas_regionais_map)

            escala_diaria_regional = df_escala_filtrado.groupby(['regional_nova', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
            turnos_diaria_regional = df_turnos_filtrado.groupby(['regional_nova', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
            soma_escala_regional = escala_diaria_regional.groupby('regional_nova')['equipes_dia'].sum()
            soma_turnos_regional = turnos_diaria_regional.groupby('regional_nova')['equipes_dia'].sum()

            # --- LÓGICA DO CONTRATO POR REGIONAL ATUALIZADA ---
            soma_contrato_regional = pd.Series(dtype='float64')
            if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
                df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')
                
                contratos_30_regional = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30].groupby('regional_nova')['prefixo'].nunique()
                contratos_24_regional = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24].groupby('regional_nova')['prefixo'].nunique()
                
                df_contratos_agg = pd.DataFrame({'count_30': contratos_30_regional, 'count_24': contratos_24_regional}).fillna(0)
                soma_contrato_regional = (df_contratos_agg['count_30'] * numero_dias_filtro) + (df_contratos_agg['count_24'] * num_non_sundays)

            df_comparativo_nova_regional = pd.DataFrame({'Escala sgd': soma_escala_regional, 'Turnos Abertos NewMars': soma_turnos_regional, 'Turnos Contratados': soma_contrato_regional}).reset_index().fillna(0).rename(columns={'regional_nova': 'Regional'})
            
            options_regional = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ['Turnos Contratados','Escala sgd', 'Turnos Abertos NewMars']},
                "xAxis": {"type": "category", "data": df_comparativo_nova_regional['Regional'].tolist(), "axisLabel": {"color": "black"}},
                "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"show": False}},
                "series": [
                    {"name": 'Turnos Contratados', "type": 'bar', "data": df_comparativo_nova_regional['Turnos Contratados'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#36b9cc"}},
                    {"name": 'Escala sgd', "type": 'bar', "data": df_comparativo_nova_regional['Escala sgd'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#4e73df"}},
                    {"name": 'Turnos Abertos NewMars', "type": 'bar', "data": df_comparativo_nova_regional['Turnos Abertos NewMars'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#1cc88a"}},
                ]
            }
            st_echarts(options=options_regional, height="500px")
            st.markdown("---")

            st.markdown("<h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>Escala x Turnos Abertos x Turnos contratados - Unidade</h2>", unsafe_allow_html=True)
            
            escala_diaria_unidade = df_escala_filtrado.groupby(['unidade', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
            turnos_diaria_unidade = df_turnos_filtrado.groupby(['unidade', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
            soma_escala_unidade = escala_diaria_unidade.groupby('unidade')['equipes_dia'].sum()
            soma_turnos_unidade = turnos_diaria_unidade.groupby('unidade')['equipes_dia'].sum()
            
            # --- LÓGICA DO CONTRATO POR UNIDADE ATUALIZADA ---
            soma_contrato_unidade = pd.Series(dtype='float64')
            if not df_contrato_filtrado.empty and 'ESCALA' in df_contrato_filtrado.columns:
                df_contrato_filtrado['ESCALA'] = pd.to_numeric(df_contrato_filtrado['ESCALA'], errors='coerce')
                
                contratos_30_unidade = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 30].groupby('unidade')['prefixo'].nunique()
                contratos_24_unidade = df_contrato_filtrado[df_contrato_filtrado['ESCALA'] == 24].groupby('unidade')['prefixo'].nunique()
                
                df_contratos_agg_unidade = pd.DataFrame({'count_30': contratos_30_unidade, 'count_24': contratos_24_unidade}).fillna(0)
                soma_contrato_unidade = (df_contratos_agg_unidade['count_30'] * numero_dias_filtro) + (df_contratos_agg_unidade['count_24'] * num_non_sundays)

            df_comparativo_unidade = pd.DataFrame({'Escala sgd': soma_escala_unidade, 'Turnos Abertos NewMars': soma_turnos_unidade, 'Turnos Contratados': soma_contrato_unidade}).reset_index().fillna(0).rename(columns={'index': 'unidade'})
            
            options_unidade = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ['Turnos Contratados','Escala sgd', 'Turnos Abertos NewMars']},
                "xAxis": {"type": "category", "data": df_comparativo_unidade['unidade'].tolist(), "axisLabel": {"color": "black", "rotate": 30}},
                "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"show": False}},
                "series": [
                    {"name": 'Turnos Contratados', "type": 'bar', "data": df_comparativo_unidade['Turnos Contratados'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#36b9cc"}},
                    {"name": 'Escala sgd', "type": 'bar', "data": df_comparativo_unidade['Escala sgd'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#4e73df"}},
                    {"name": 'Turnos Abertos NewMars', "type": 'bar', "data": df_comparativo_unidade['Turnos Abertos NewMars'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#1cc88a"}},
                ]
            }
            st_echarts(options=options_unidade, height="500px")
            st.markdown("---")
            
            if 'cidade' in df_escala_filtrado.columns and 'cidade' in df_turnos_filtrado.columns:
                st.markdown("<h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>Escala x Turnos Abertos - Cidades</h2>", unsafe_allow_html=True)
                
                escala_diaria_cidade = df_escala_filtrado.groupby(['cidade', df_escala_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
                turnos_diaria_cidade = df_turnos_filtrado.groupby(['cidade', df_turnos_filtrado['data_inicio'].dt.date])['prefixo'].nunique().reset_index(name='equipes_dia')
                soma_escala_cidade = escala_diaria_cidade.groupby('cidade')['equipes_dia'].sum()
                soma_turnos_cidade = turnos_diaria_cidade.groupby('cidade')['equipes_dia'].sum()

                df_comparativo_cidade = pd.DataFrame({'Escala sgd': soma_escala_cidade, 'Turnos Abertos NewMars': soma_turnos_cidade}).reset_index().fillna(0)
                
                options_cidade = {
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "legend": {"data": ['Escala sgd', 'Turnos Abertos NewMars']},
                    "xAxis": {"type": "category", "data": df_comparativo_cidade['cidade'].tolist(), "axisLabel": {"color": "black", "rotate": 30}},
                    "yAxis": {"type": "value", "axisLabel": {"show": False}, "splitLine": {"show": False}},
                    "series": [
                        {"name": 'Escala sgd', "type": 'bar', "data": df_comparativo_cidade['Escala sgd'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#4e73df"}},
                        {"name": 'Turnos Abertos NewMars', "type": 'bar', "data": df_comparativo_cidade['Turnos Abertos NewMars'].tolist(), "label": {"show": True, "position": "top", "color": "black"}, "itemStyle": {"color": "#1cc88a"}},
                    ]
                }
                st_echarts(options=options_cidade, height="500px")
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados na Análise Geográfica.")
            
    with tab3:
        st.markdown(
        """
        <h2 style='text-align: center; font-size: 28px; font-weight: bold; color: #2E86C1;'>
        CONTROLE DE ABERTURA DE TURNO POR EQUIPE 
        </h2>
        """, unsafe_allow_html=True)

        equipes_contrato = sorted(df_contrato_filtrado['prefixo'].unique())
        equipes_escala = sorted(df_escala_filtrado['prefixo'].unique())
        equipes_turnos = sorted(df_turnos_filtrado['prefixo'].unique())

        set_contrato = set(equipes_contrato)
        set_escala = set(equipes_escala)
        set_turnos = set(equipes_turnos)

        equipes_sem_turno = sorted(list(set_contrato - set_turnos))

        st.markdown("""
        <style>
        .metrics-container {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin: 20px 0;
            font-family: 'Segoe UI', Tahoma, sans-serif;
        }
        .metric-card {
            flex: 1;
            background: linear-gradient(145deg, #ffffff, #f0f0f0);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease-in-out;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-value {
            font-size: 26px;
            font-weight: bold;
            margin-top: 10px;
        }
        .metric-label {
            font-size: 14px;
            color: #666;
        }
        .green { border-left: 6px solid #28a745; }
        .blue { border-left: 6px solid #007bff; }
        .orange { border-left: 6px solid #fd7e14; }
        .red { border-left: 6px solid #dc3545; }

        /* Estilos para os filtros (checkboxes) */
        div[data-testid="stCheckbox"] label span {
            font-weight: bold;
            font-size: 14px;
        }
        </style>
        """, unsafe_allow_html=True)

        html_metrics = f"""
        <div class="metrics-container">
            <div class="metric-card green">
                <div class="metric-label">✅ Total Contratadas</div>
                <div class="metric-value">{len(equipes_contrato)}</div>
            </div>
            <div class="metric-card blue">
                <div class="metric-label">📅 Total na Escala (SGD)</div>
                <div class="metric-value">{len(equipes_escala)}</div>
            </div>
            <div class="metric-card orange">
                <div class="metric-label">🛠️ Total com Turnos (NewMars)</div>
                <div class="metric-value">{len(equipes_turnos)}</div>
            </div>
            <div class="metric-card red">
                <div class="metric-label">⚠️ Contrato s/ Turno</div>
                <div class="metric-value">{len(equipes_sem_turno)}</div>
            </div>
        </div>
        """
        st.markdown(html_metrics, unsafe_allow_html=True)

        css_style = """
        <style>
            .prefix-container {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                justify-content: center;
                margin-top: 20px;
            }
            .prefix-box {
                width: 90px;
                height: 90px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .green { background-color: #28a745; }
            .yellow { background-color: #ffc107; color: black; }
            .red { background-color: #dc3545; }
            .orange { background-color: #fd7e14; }
            .gray { background-color: #6c757d; color: white; }
        </style>
        """

        def get_prefix_status(prefix):
            in_contrato = prefix in set_contrato
            in_escala = prefix in set_escala
            in_turno = prefix in set_turnos

            if in_turno and in_escala and in_contrato:
                return "green", "✅ Turno + Escala + Contrato"
            elif in_escala and in_contrato and not in_turno:
                return "yellow", "🟨 Escala + Contrato (s/ Turno)"
            elif in_escala and not in_contrato:
                return "red", "🟥 Na Escala (fora do Contrato)"
            elif in_turno and not in_contrato:
                return "orange", "🟧 Com Turno (fora do Contrato)"
            elif in_contrato and not in_escala and not in_turno:
                return "gray", "⚪ Contrato (s/ Escala e s/ Turno)"
            else:
                return None, None

        all_prefixes = sorted(set_contrato.union(set_escala).union(set_turnos))

        dict_coord = pd.concat([df_escala_classificado[['prefixo', 'COORDENACAO']], df_turnos_classificado[['prefixo', 'COORDENACAO']]]).drop_duplicates('prefixo').set_index('prefixo')['COORDENACAO'].to_dict()

        # --- MUDANÇA 1: CRIAR DICIONÁRIO PARA A ESCALA ---
        dict_escala = {}
        if not df_contrato_classificado.empty:
            dict_tipo = df_contrato_classificado.drop_duplicates('prefixo').set_index('prefixo')['descricao_tipo_prefixo'].to_dict()
            # Verifica se a coluna ESCALA existe antes de criar o mapa
            if 'ESCALA' in df_contrato_classificado.columns:
                dict_escala = df_contrato_classificado.drop_duplicates('prefixo').set_index('prefixo')['ESCALA'].to_dict()
        else:
            dict_tipo = {}

        prefix_status_list = []
        status_options = {} 
        for p in all_prefixes:
            cor, descricao = get_prefix_status(p)
            if cor is not None:
                prefix_status_list.append({'prefixo': p, 'cor': cor, 'descricao': descricao})
                if descricao not in status_options:
                    status_options[descricao] = cor

        st.markdown("---")

        cols = st.columns(len(status_options))
        selected_descriptions = []

        sorted_options = sorted(status_options.items())

        for i, (description, color) in enumerate(sorted_options):
            with cols[i]:
                if st.checkbox(description, value=True, key=f"cb_{color}"):
                    selected_descriptions.append(description)

        prefixos_filtrados = [
            item for item in prefix_status_list if item['descricao'] in selected_descriptions
        ]

        html_prefixes = ""
        for item in prefixos_filtrados:
            p = item['prefixo']
            cor = item['cor']
            coord = dict_coord.get(p, "N/A")
            tipo = dict_tipo.get(p, "N/A")
            # --- MUDANÇA 2: BUSCAR A ESCALA E ADICIONAR AO TOOLTIP ---
            escala = dict_escala.get(p, "N/A")
            
            tooltip = f"Coordenação: {coord} | Tipo: {tipo} | Escala dias: {escala}"
            
            html_prefixes += f"<div class='prefix-box {cor}' title='{tooltip}'>{p}</div>"

        st.markdown(css_style + f"<div class='prefix-container'>{html_prefixes}</div>", unsafe_allow_html=True)
        st.markdown("---")

        df_download = pd.DataFrame(all_prefixes, columns=['prefixo'])
        # A função get_prefix_status retorna tupla, precisamos pegar só a cor para o status
        df_download['status'] = df_download['prefixo'].apply(lambda p: get_prefix_status(p)[0])
        df_download['coordenacao'] = df_download['prefixo'].map(dict_coord).fillna('N/A')
        df_download['tipo_equipe'] = df_download['prefixo'].map(dict_tipo).fillna('N/A')
        
        df_download['in_contrato'] = df_download['prefixo'].isin(set_contrato)
        df_download['in_escala'] = df_download['prefixo'].isin(set_escala)
        df_download['in_turno'] = df_download['prefixo'].isin(set_turnos)


        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Controle de Turnos')
            return output.getvalue()

        excel_data = to_excel(df_download)

        st.download_button(
            label="📥 Baixar Controle Detalhado",
            data=excel_data,
            file_name="controle_turnos_detalhado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
                
if __name__ == "__main__":
    app()