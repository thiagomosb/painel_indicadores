import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import os
import subprocess
import time
from io import BytesIO
import uuid
import matplotlib.pyplot as plt
import pandas as pd
import calendar
import streamlit as st
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import pydeck as pdk
import hashlib
from io import BytesIO
import io

def app():
    # Configuração da página
    
    
    # Cabeçalho
    st.markdown("""
        <div style="text-align: center;">
            <h3>📊 DASHBOARD DE INSPEÇÕES DINÂMICAS</h3>
        </div>
    """, unsafe_allow_html=True)
    
   

    # Filtros na barra lateral (Sidebar)
    st.logo('https://www.dolpengenharia.com.br/wp-content/uploads/2021/01/logotipo-definitivo-250614.png')


        # --- Botão de atualização e data fixa na barra lateral ---
    
        # Configuração da página para layout amplo
    
    st.markdown("""
            <style>
            .main > div {
                max-width: 100%;
                padding-left: 5%;
                padding-right: 5%;
            }
            .stButton > button {
                width: 100%;
            }
            .stTextInput > div > div > input {
                width: 100%;
            }
            .stSelectbox > div > div > div {
                width: 100%;
            }
            .stSlider > div > div > div {
                width: 100%;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    ## Leitura dos arquivos CSV
    @st.cache_data
    def load_data():
        df = pd.read_csv("data/blitz.csv", parse_dates=["data_turno"])
        df_turnos = pd.read_csv("data/turnos.csv", parse_dates=["dt_inicio"])
        df_respostas = pd.read_csv("data/respostas.csv")
        df_eventos = pd.read_csv("data/eventos.csv")
        df_pessoas = pd.read_csv("data/pessoas.csv")
        return df, df_turnos, df_respostas, df_eventos, df_pessoas

    # --- Mostra data/hora da última atualização ---
    def get_data_mod_time(file_path):
        if os.path.exists(file_path):
            mod_time = os.path.getmtime(file_path)
            return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(mod_time))
        return "Arquivo não encontrado"
    # Botão para atualizar os dados
    


    # Adiciona na barra lateral
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center;">
            🕒 Última atualização: <strong>{get_data_mod_time('data/blitz.csv')}</strong>
        </div>
    """, unsafe_allow_html=True)


        if st.button("🔄 Atualizar Dados Agora"):
            
            with st.spinner("Atualizando CSVs a partir do banco..."):
                subprocess.run(["python", "exportar_dados_para_csv.py"], check=True)
                st.cache_data.clear()
                st.success("CSVs atualizados com sucesso!")
                st.rerun()
                

    formulario = st.sidebar.form('teste')  # Filtros na barra lateral
    with formulario:    
        
        # Cabeçalho
        st.markdown("""
            <div style="text-align: center;">
                <h3>Click no botão carregar para carregar os filtros selecionados</h3>
            </div>
        """, unsafe_allow_html=True)
        st.form_submit_button("⏳carregar")
        # Carrega os dados (após possível reinício)
        df, df_turnos, df_respostas, df_eventos, df_pessoas = load_data()
        
        # Adiciona coluna descricao_tipo_prefixo ao df principal
        
        # 🛠 Corrige a data_turno com base em dt_inicio (data real do turno)
        df = pd.merge(
            df,
            df_turnos[['idtb_turnos', 'dt_inicio', ]],
            on='idtb_turnos',
            how='left'
        )

        # Usa a data real
        df['data_turno'] = df['dt_inicio']

        # semana
        df['semana_ano'] = df['data_turno'].dt.isocalendar().week

        # Garante que df (blitz.csv) tenha as colunas 'id_reserva' e 'descricao_tipo_prefixo'
        df = pd.merge(
            df,
            df_turnos[['idtb_turnos', 'id_reserva', 'descricao_tipo_prefixo']],
            on='idtb_turnos',
            how='left'
        )

        # Classificação do tipo de equipe baseada no número operacional
        def identificar_tipo(num_op):
            num_op = str(num_op)
            if num_op.startswith('9'):
                return 'EQUIPE LEVE'
            elif num_op.startswith('8'):
                return 'EQUIPE PESADA'
            elif num_op.startswith('7'):
                return 'EQUIPE DE LINHA'
            elif num_op.startswith('4'):
                return 'EQUIPE DE MOTOCICLETA'
            else:
                return 'Outros'

        # Aplica a função ao DataFrame principal
        df['tipo_equipe_classificado'] = df['num_operacional'].astype(str).apply(identificar_tipo)

        # Pré-processamentos e filtros iniciais
        ano_mais_recente = df['data_turno'].dt.year.max()
        mes_mais_recente = df[df['data_turno'].dt.year == ano_mais_recente]['data_turno'].dt.month.max()

    
        st.header("Filtros")
        
        anos_disponiveis = sorted(df['data_turno'].dt.year.unique(), reverse=True)
        anos_filtrados = [ano for ano in anos_disponiveis if ano >= 2025]

        if anos_filtrados:
            ano_selecionado = st.selectbox("Ano", anos_filtrados, index=0)
        else:
            st.warning("Nenhum dado disponível a partir de 2025.")
            st.stop()

        try:
            meses_disponiveis = df[df['data_turno'].dt.year == ano_selecionado]['data_turno'].dt.month.unique()
            meses_selecionados = st.multiselect(
                "Selecione os Meses",
                sorted(meses_disponiveis),
                default=[mes_mais_recente]
            )
        except:
            st.error("Sem dados no Sistema")

        # <<< INÍCIO DA ALTERAÇÃO >>>
        
        # Dicionário de Regionais e Unidades
        regionais_unidades = {
            "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"],
            "REGIONAL RIO VERDE": ["RIO VERDE - GO"],
            "REGIONAL TO": ["PALMAS - TO"],
            "REGIONAL MT": ["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]
        }

        # Seleção múltipla de Regionais (todas selecionadas por padrão)
        regionais_disponiveis = list(regionais_unidades.keys())
        regionais_selecionadas = st.multiselect(
            "Selecione a(s) Regional(is)",
            options=regionais_disponiveis,
            default=regionais_disponiveis
        )

        # Gerar lista de unidades com base nas regionais selecionadas
        unidades_disponiveis = []
        for regional in regionais_selecionadas:
            unidades_disponiveis.extend(regionais_unidades[regional])
        
        # Remover duplicatas e ordenar
        unidades_disponiveis = sorted(list(set(unidades_disponiveis)))

        # Seleção múltipla de Unidades
        unidades_selecionadas = st.multiselect(
            "Selecione a(s) Unidade(s)",
            options=unidades_disponiveis,
            default=unidades_disponiveis # Seleciona todas as unidades disponíveis por padrão
        )

        # <<< FIM DA ALTERAÇÃO >>>
        
        #--------------------semana
        # Filtro por semana do ano
        st.markdown("### Semana do Ano")

        # Pega semanas disponíveis com base no ano e mês já selecionados
        semanas_disponiveis = sorted(df[
            (df['data_turno'].dt.year == ano_selecionado) &
            (df['data_turno'].dt.month.isin(meses_selecionados))
        ]['semana_ano'].dropna().unique())

        # Filtro multiselect de semanas
        semanas_selecionadas = st.multiselect(
            "Selecione as Semanas",
            options=semanas_disponiveis,
            default=semanas_disponiveis
        )

        st.markdown("### Tipo de Inspetor")

        # Define as categorias manualmente
        categorias_funcao = {
            "SESMT": [
                "TÉCNICO DE SEGURANÇA DO TRABALHO",
                "TECNICO DE SEGURANÇA DO TRABALHO",
                "COORDENADOR DE SEGURANÇA"
            ],
            "SUPERVISÃO": [
                "SUPERVISOR",
                "SUPERVISOR ",
                "LIDER DE CAMPO","COORDENADOR DE OBRAS","COORDENADOR OPERACIONAL"
            ]
        }

    
        st.markdown("### Tipo de Inspetor e Tipo de Frota")
        
        col1, col2 = st.columns(2)
        
        with col1:
            seleciona_sesmt = st.checkbox("SESMT", value=True)
            seleciona_supervisao = st.checkbox("SUPERVISÃO", value=True)
            
        with col2:
            exibir_reserva = st.checkbox("Frota Reserva", value=True)
            exibir_titular = st.checkbox("Frota Titular", value=True)
            exibir_sem_identificacao = st.checkbox("Sem Identificação", value=True)
        # Lógica dos tipos de inspetores
        funcao_geral_selecionada = []
        if seleciona_sesmt:
            funcao_geral_selecionada.extend(categorias_funcao["SESMT"])
        if seleciona_supervisao:
            funcao_geral_selecionada.extend(categorias_funcao["SUPERVISÃO"])

        # Lógica do filtro de frota (com NaN incluído se marcado)
        mascara_frota = pd.Series(False, index=df.index)

        if exibir_reserva:
            mascara_frota |= df['id_reserva'] == 1
        if exibir_titular:
            mascara_frota |= df['id_reserva'] == 2
        if exibir_sem_identificacao:
            mascara_frota |= df['id_reserva'].isna()

        # Aplica o filtro de frota ao DataFrame principal
        df = df[mascara_frota]

        # Lista de instrutores filtrada após o filtro de frota
        instrutores_unicos = sorted(df[df['unidade'].isin(unidades_selecionadas)]['nome_inspetor'].dropna().unique())
        instrutor_escolhido = st.selectbox(
            "Selecione o Instrutor",
            options=["Todos"] + instrutores_unicos,
            index=0
        )

        if instrutor_escolhido == "Todos":
            instrutores_selecionados = instrutores_unicos
        else:
            instrutores_selecionados = [instrutor_escolhido]

        # Aplica a função ao DataFrame principal
        df['tipo_equipe_classificado'] = df['num_operacional'].astype(str).apply(identificar_tipo)

        # Filtro por tipo de equipe (baseado em classificação)
        tipos_equipe_disponiveis = sorted(df['tipo_equipe_classificado'].unique())
        tipos_equipe_selecionados = st.multiselect(
            "Tipo de Equipe (por número operacional)",
            options=tipos_equipe_disponiveis,
            default=tipos_equipe_disponiveis
        )

        # Filtro por tipo de prefixo (descricao_tipo_prefixo)
        prefixos_disponiveis = df_turnos['descricao_tipo_prefixo'].dropna().unique()
        prefixos_selecionados = st.multiselect(
            "Tipo de Prefixo",
            options=sorted(prefixos_disponiveis),
            default=sorted(prefixos_disponiveis)
        )

        # ➕ Filtro de Turno
        st.markdown("### Turno da Inspeção")
        turnos_opcoes = ['MANHÃ', 'TARDE', 'NOITE']
        turnos_selecionados = st.multiselect(
            "Selecione o(s) Turno(s)",
            options=turnos_opcoes,
            default=turnos_opcoes
        )

        # Adiciona coluna de hora e classifica turno
        df['hora'] = pd.to_datetime(df['data_turno'], errors='coerce').dt.hour

        def classificar_turno(hora):
            if 1 <= hora <= 11:
                return 'MANHÃ'
            elif 12 <= hora <= 17:
                return 'TARDE'
            elif 18 <= hora <= 23 or hora == 0:
                return 'NOITE'

        df['turno_inspecao'] = df['hora'].apply(classificar_turno)

        # 🔎 Filtro por Zona de Inspeção
        st.markdown("### Zona da Inspeção")

        # Padroniza os valores de zona_inspecao
        df['zona_inspecao'] = df['zona_inspecao'].astype(str).str.strip().str.upper()
        df['zona_inspecao'] = df['zona_inspecao'].replace({
            'ZONA RURAL': 'RURAL',
            'ZONA URBANA': 'URBANA',
            'LOCAl': 'LOCAL'
        })

        zonas_disponiveis = sorted(df['zona_inspecao'].dropna().unique())
        zonas_selecionadas = st.multiselect(
            "Selecione a(s) Zona(s)",
            options=zonas_disponiveis,
            default=zonas_disponiveis
        )

        # Aplica todos os filtros
        try:
            df_filtrado = df[
                (df['data_turno'].dt.year == ano_selecionado) &
                (df['data_turno'].dt.month.isin(meses_selecionados)) &
                (df['semana_ano'].isin(semanas_selecionadas)) &
                (df['unidade'].isin(unidades_selecionadas)) &
                (df['nome_inspetor'].isin(instrutores_selecionados)) &
                (df['funcao_geral'].isin(funcao_geral_selecionada)) &
                (df['tipo_equipe_classificado'].isin(tipos_equipe_selecionados)) &
                (df['descricao_tipo_prefixo'].isin(prefixos_selecionados)) & 
                (df['turno_inspecao'].isin(turnos_selecionados)) & 
                (df['zona_inspecao'].isin(zonas_selecionadas))
            ]
        except Exception as e:
            st.error(f"Erro ao aplicar filtros: {e}")
            df_filtrado = pd.DataFrame()


        # Também filtramos os turnos e respostas conforme os mesmos critérios básicos
        df_turnos = df_turnos[
            (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
            (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados)) &
            (df_turnos['unidade'].isin(unidades_selecionadas))
        ]
        # Tratar a coluna 'idtb_pessoas' com segurança
        try:
            df_filtrado['idtb_pessoas'] = df_filtrado['idtb_pessoas'].replace('', pd.NA)
        except KeyError:
            st.warning("Coluna 'idtb_pessoas' não encontrada no DataFrame filtrado. Criando coluna vazia.")
            df_filtrado['idtb_pessoas'] = pd.NA

        # Filtrar só linhas onde idtb_pessoas está em branco (NaN)
        df_sem_pessoas = df_filtrado[df_filtrado['idtb_pessoas'].isna()]
        #semana

        # Divisão SESMT e LIDERANÇA
        # Obtem os IDs dos turnos que estão filtrados
        turnos_validos = df_filtrado['idtb_turnos'].unique()

        # Aplica todos os filtros corretamente
        df_respostas_filtradas = df_respostas[
            (df_respostas['resposta_int'] == 2) &
            (df_respostas['idtb_turnos'].isin(turnos_validos)) &
            (df_respostas['nome_inspetor'].isin(instrutores_selecionados)) &
            (df_respostas['num_operacional'].isin(df_filtrado['num_operacional'].unique()))
        ]

        # 🔄 Aplica também o filtro de frota ao df_turnos
        mascara_turnos_frota = pd.Series(False, index=df_turnos.index)

        if exibir_reserva:
            mascara_turnos_frota |= df_turnos['id_reserva'] == 1
        if exibir_titular:
            mascara_turnos_frota |= df_turnos['id_reserva'] == 2
        if exibir_sem_identificacao:
            mascara_turnos_frota |= df_turnos['id_reserva'].isna()

        df_turnos = df_turnos[mascara_turnos_frota]

    # ########################################################################################## #
    # ###################### INÍCIO DO BLOCO DE CÁLCULO ATUALIZADO ############################# #
    # ########################################################################################## #
    
    # --- LÓGICA ALTERADA PARA FILTRAR PELA BASE DO INSPETOR ---
    # 1. Obter a lista de IDs dos inspetores que estão "Em Atividade" E cuja "base" (lotação) está na lista de unidades selecionadas no filtro.
    # Esta é a mudança principal: a lista de inspetores a serem exibidos agora depende da sua base, não de onde eles realizaram a inspeção.
    inspetores_da_base_selecionada = df_pessoas[
        (df_pessoas['situacao'] == 'Em Atividade') &
        (df_pessoas['base'].isin(unidades_selecionadas))
    ]
    ids_finais_ativos = inspetores_da_base_selecionada['idtb_oper_pessoa'].unique()

    # 2. Construir o DataFrame de base com os inspetores ativos das bases selecionadas.
    df_active_inspectors = pd.DataFrame({'idtb_oper_pessoa': ids_finais_ativos})
    inspector_info = df_pessoas[['idtb_oper_pessoa', 'nome', 'funcao_geral']].drop_duplicates(subset=['idtb_oper_pessoa'])
    df_active_inspectors = pd.merge(df_active_inspectors, inspector_info, on='idtb_oper_pessoa', how='left')
    df_active_inspectors.rename(columns={'nome': 'nome_inspetor'}, inplace=True) # Renomeia para consistência


    # Define as listas de funções para cada categoria
    funcoes_sesmt = ["TÉCNICO DE SEGURANÇA DO TRABALHO", "TECNICO DE SEGURANÇA DO TRABALHO", "COORDENADOR DE SEGURANÇA", "TECNICO DE SEGURANÇA DO TRABALHO II"]
    funcoes_supervisao = ["SUPERVISOR", "SUPERVISOR "]
    funcoes_coordenacao = ["COORDENADOR DE OBRAS", "COORDENADOR OPERACIONAL","COORDENADOR STC","COORDENADOR DE OBRAS"]
    funcoes_lider_campo = ["LIDER DE CAMPO"]
    funcoes_lideranca = funcoes_supervisao + funcoes_coordenacao + funcoes_lider_campo

    # Função para truncar nomes longos de inspetores
    def truncar_nome(nome):
        # Garante que o nome não seja nulo (NaN) antes de verificar o comprimento
        if pd.isna(nome):
            return ""
        return nome if len(nome) <= 25 else nome[:22] + '...'

    # Realiza a contagem de blitz UMA VEZ usando o DataFrame `df_sem_pessoas`.
    # Este DataFrame já foi filtrado por data e outros critérios, mas não pela base do inspetor.
    # Isso é o correto, pois queremos contar TODAS as inspeções do período para os inspetores que selecionamos pela base.
    blitz_counts = (
        df_sem_pessoas.groupby('idtb_pessoas_inspetor')['idtb_turnos_blitz_contatos']
        .nunique().reset_index()
        .rename(columns={'idtb_turnos_blitz_contatos': 'quantidade_blitz', 'idtb_pessoas_inspetor': 'idtb_oper_pessoa'}) # Renomeia ID para o merge
    )

    # --- CÁLCULOS POR FUNÇÃO ---
    # Os merges a seguir vão juntar a lista de inspetores (filtrada pela base) com suas contagens totais de inspeções.
    # Se um inspetor da base selecionada não fez inspeções no período, ele aparecerá com 0, que é o comportamento desejado.

    # --- CÁLCULO PARA O SESMT ---
    ativos_sesmt = df_active_inspectors[df_active_inspectors['funcao_geral'].isin(funcoes_sesmt)]
    blitz_por_instrutor_sesmt_sem_pessoas = pd.merge(
        ativos_sesmt[['idtb_oper_pessoa', 'nome_inspetor']], blitz_counts, on='idtb_oper_pessoa', how='left'
    )
    blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'] = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].fillna(0).astype(int)
    blitz_por_instrutor_sesmt_sem_pessoas = blitz_por_instrutor_sesmt_sem_pessoas.sort_values(by=['quantidade_blitz', 'nome_inspetor'], ascending=[False, True])
    blitz_por_instrutor_sesmt_sem_pessoas['nome_inspetor'] = blitz_por_instrutor_sesmt_sem_pessoas['nome_inspetor'].apply(truncar_nome)

    # --- CÁLCULO PARA SUPERVISÃO ---
    ativos_supervisao = df_active_inspectors[df_active_inspectors['funcao_geral'].isin(funcoes_supervisao)]
    blitz_por_instrutor_supervisao = pd.merge(
        ativos_supervisao[['idtb_oper_pessoa', 'nome_inspetor']], blitz_counts, on='idtb_oper_pessoa', how='left'
    )
    blitz_por_instrutor_supervisao['quantidade_blitz'] = blitz_por_instrutor_supervisao['quantidade_blitz'].fillna(0).astype(int)
    blitz_por_instrutor_supervisao = blitz_por_instrutor_supervisao.sort_values(by=['quantidade_blitz', 'nome_inspetor'], ascending=[False, True])
    blitz_por_instrutor_supervisao['nome_inspetor'] = blitz_por_instrutor_supervisao['nome_inspetor'].apply(truncar_nome)

    # --- CÁLCULO PARA COORDENAÇÃO ---
    ativos_coordenacao = df_active_inspectors[df_active_inspectors['funcao_geral'].isin(funcoes_coordenacao)]
    blitz_por_instrutor_coordenacao = pd.merge(
        ativos_coordenacao[['idtb_oper_pessoa', 'nome_inspetor']], blitz_counts, on='idtb_oper_pessoa', how='left'
    )
    blitz_por_instrutor_coordenacao['quantidade_blitz'] = blitz_por_instrutor_coordenacao['quantidade_blitz'].fillna(0).astype(int)
    blitz_por_instrutor_coordenacao = blitz_por_instrutor_coordenacao.sort_values(by=['quantidade_blitz', 'nome_inspetor'], ascending=[False, True])
    blitz_por_instrutor_coordenacao['nome_inspetor'] = blitz_por_instrutor_coordenacao['nome_inspetor'].apply(truncar_nome)

    # --- CÁLCULO PARA LÍDER DE CAMPO ---
    ativos_lider_campo = df_active_inspectors[df_active_inspectors['funcao_geral'].isin(funcoes_lider_campo)]
    blitz_por_instrutor_lider_campo = pd.merge(
        ativos_lider_campo[['idtb_oper_pessoa', 'nome_inspetor']], blitz_counts, on='idtb_oper_pessoa', how='left'
    )
    blitz_por_instrutor_lider_campo['quantidade_blitz'] = blitz_por_instrutor_lider_campo['quantidade_blitz'].fillna(0).astype(int)
    blitz_por_instrutor_lider_campo = blitz_por_instrutor_lider_campo.sort_values(by=['quantidade_blitz', 'nome_inspetor'], ascending=[False, True])
    blitz_por_instrutor_lider_campo['nome_inspetor'] = blitz_por_instrutor_lider_campo['nome_inspetor'].apply(truncar_nome)
    
    # --- CÁLCULO PARA A LIDERANÇA (AGRUPADO) ---
    ativos_lideranca = df_active_inspectors[df_active_inspectors['funcao_geral'].isin(funcoes_lideranca)]
    blitz_por_instrutor_lideranca_sem_pessoas = pd.merge(
        ativos_lideranca[['idtb_oper_pessoa', 'nome_inspetor']], blitz_counts, on='idtb_oper_pessoa', how='left'
    )
    blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'] = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].fillna(0).astype(int)
    blitz_por_instrutor_lideranca_sem_pessoas = blitz_por_instrutor_lideranca_sem_pessoas.sort_values(by=['quantidade_blitz', 'nome_inspetor'], ascending=[False, True])
    blitz_por_instrutor_lideranca_sem_pessoas['nome_inspetor'] = blitz_por_instrutor_lideranca_sem_pessoas['nome_inspetor'].apply(truncar_nome)

    # ########################################################################################## #
    # ####################### FIM DO BLOCO DE CÁLCULO ATUALIZADO ############################### #
    # ########################################################################################## #


 

    #-----------------------------------Inspeção SESMT E SUPERVISÃO ----------------------------------#
    
   

    # 🔹 CSS para habilitar rolagem horizontal nas abas
    st.markdown("""
        <style>
        /* Área da lista de abas */
        div[data-baseweb="tab-list"] {
            overflow-x: auto !important;
            white-space: nowrap !important;
            scrollbar-width: thin;
        }
        /* Barra de rolagem no Chrome/Safari */
        div[data-baseweb="tab-list"]::-webkit-scrollbar {
            height: 6px;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        </style>
    """, unsafe_allow_html=True)

    # 🔹 Suas abas com scroll horizontal
    INSPECAO_ESP,INSPECAO, CONTATO, REPROVACAO, REPROVACAO_TIPO_EQUIPE, REPROVACAO_INSPETOR, REPROVACAO_INSPETOR2, RETROVACAO_INSPETOR3, ICIT_INSPETOR, MAPA, EQUIPES_INSTRUTOR, Horas_das_inspecao = st.tabs([
        "📋 INSPEÇÕES POR CATEGORIA DE FUNÇÃO",
        "📋 INSPEÇÕES",
        "📊 TAXA DE CONTATO",
        "🧮 PONTUAÇÕES POR CATEGORIA",
        "🚘 PONTUAÇÕES POR TIPO DE EQUIPE",
        "👷 PONTUAÇÕES POR INSPETOR",
        "👷 PONTUAÇÕES POR INSPETOR II",
        "👷 PONTUAÇÕES POR INSPETOR III",
        "🔍 ICIT INSPETOR",
        "🗺️ MAPA DAS INSPEÇÕES",
        "👥 EQUIPES INSPECIONADAS POR INSPETOR",
        "🗓️ PERÍODO DAS INSPEÇÕES"
    ])
    
    with INSPECAO_ESP:

        import uuid  

        qtd_meses = len(meses_selecionados)

        # ⚡️ NOVO: Lógica condicional para as metas com base na regional selecionada ⚡️
        # A nova regra se aplica se "REGIONAL MT" estiver entre as regionais escolhidas.
        if "REGIONAL MT" in regionais_selecionadas:
            meta_sesmt = 24 * qtd_meses
            meta_coordenacao = 4 * qtd_meses
            meta_supervisao = 15 * qtd_meses
            meta_lider_campo = 15 * qtd_meses
        else:
            meta_sesmt = 15 * qtd_meses
            meta_coordenacao = 4 * qtd_meses
            meta_supervisao = 8 * qtd_meses
            meta_lider_campo = 8 * qtd_meses
        
        # PRIMEIRA LINHA DE GRÁFICOS
        col1, col2 = st.columns([1, 1])

        # GRÁFICO 1: SESMT
        with col1:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES SESMT</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_sesmt_sem_pessoas.empty:
                max_valor = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].max()
                fig_sesmt = px.bar(
                    blitz_por_instrutor_sesmt_sem_pessoas, x='nome_inspetor', y='quantidade_blitz',
                    text='quantidade_blitz', title=""
                )
                fig_sesmt.update_traces(marker_color='#1f77b4', marker_line_color='black', marker_line_width=1.5,
                                        textposition='outside', textfont=dict(color='black', size=16, family='Arial'))
                fig_sesmt.add_hline(y=meta_sesmt, line_dash="dash", line_color="red",
                                    annotation_text=f"Meta: {meta_sesmt}", annotation_position="top left")
                fig_sesmt.update_layout(
                        xaxis_title="", yaxis_title="", template="plotly_white",
                        font=dict(color='black', size=14, family='Arial'),
                        xaxis=dict(tickfont=dict(color='black', size=14)),
                        yaxis=dict(
                            showticklabels=False,  # <-- ADICIONE ESTA LINHA
                            range=[0, max(1, max_valor * 1.2)]
                        ),
                        margin=dict(t=100)
)
                st.plotly_chart(fig_sesmt, use_container_width=True, key=f"grafico_sesmt_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO SESMT.")
        
        # GRÁFICO 2: COORDENAÇÃO
        with col2:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES COORDENAÇÃO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_coordenacao.empty:
                max_valor_coordenacao = blitz_por_instrutor_coordenacao['quantidade_blitz'].max()
                fig_coordenacao = px.bar(
                    blitz_por_instrutor_coordenacao, x='nome_inspetor', y='quantidade_blitz',
                    text='quantidade_blitz', title=""
                )
                fig_coordenacao.update_traces(marker_color='#2ca02c', marker_line_color='black', marker_line_width=1.5,
                                            textposition='outside', textfont=dict(color='black', size=16, family='Arial'))
                ### ALTERAÇÃO: Usando a meta_coordenacao ###
                fig_coordenacao.add_hline(y=meta_coordenacao, line_dash="dash", line_color="red",
                                            annotation_text=f"Meta: {meta_coordenacao}", annotation_position="top left")
                fig_coordenacao.update_layout(
                            xaxis_title="", yaxis_title="", template="plotly_white",
                            font=dict(color='black', size=14, family='Arial'),
                            xaxis=dict(tickfont=dict(color='black', size=14)),
                            yaxis=dict(
                                showticklabels=False,  # <-- ADICIONE ESTA LINHA
                                range=[0, max(1, max_valor_coordenacao * 1.6)]
                            ),
                            margin=dict(t=100)
)
                st.plotly_chart(fig_coordenacao, use_container_width=True, key=f"grafico_coordenacao_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO COORDENAÇÃO.")
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # SEGUNDA LINHA DE GRÁFICOS
        col3, col4 = st.columns([1, 1])
        
        # GRÁFICO 3: SUPERVISÃO
        with col3:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES SUPERVISÃO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_supervisao.empty:
                max_valor_supervisao = blitz_por_instrutor_supervisao['quantidade_blitz'].max()
                fig_supervisao = px.bar(
                    blitz_por_instrutor_supervisao, x='nome_inspetor', y='quantidade_blitz',
                    text='quantidade_blitz', title=""
                )
                fig_supervisao.update_traces(marker_color='#ff7f0e', marker_line_color='black', marker_line_width=1.5,
                                            textposition='outside', textfont=dict(color='black', size=16, family='Arial'))
                ### ALTERAÇÃO: Usando a meta_supervisao ###
                fig_supervisao.add_hline(y=meta_supervisao, line_dash="dash", line_color="red",
                                            annotation_text=f"Meta: {meta_supervisao}", annotation_position="top left")
                fig_supervisao.update_layout(
                        xaxis_title="", yaxis_title="", template="plotly_white",
                        font=dict(color='black', size=14, family='Arial'),
                        xaxis=dict(tickfont=dict(color='black', size=14)),
                        yaxis=dict(
                            showticklabels=False,  # <-- ADICIONE ESTA LINHA
                            range=[0, max(1, max_valor_supervisao * 1.6)]
                        ),
                        margin=dict(t=100)
                    )
                st.plotly_chart(fig_supervisao, use_container_width=True, key=f"grafico_supervisao_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO SUPERVISÃO.")

        # GRÁFICO 4: LÍDER DE CAMPO
        with col4:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES LÍDER DE CAMPO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_lider_campo.empty:
                max_valor_lider = blitz_por_instrutor_lider_campo['quantidade_blitz'].max()
                fig_lider = px.bar(
                    blitz_por_instrutor_lider_campo, x='nome_inspetor', y='quantidade_blitz',
                    text='quantidade_blitz', title=""
                )
                fig_lider.update_traces(marker_color='#9467bd', marker_line_color='black', marker_line_width=1.5,
                                    textposition='outside', textfont=dict(color='black', size=16, family='Arial'))
                ### ALTERAÇÃO: Usando a meta_lider_campo ###
                fig_lider.add_hline(y=meta_lider_campo, line_dash="dash", line_color="red",
                                    annotation_text=f"Meta: {meta_lider_campo}", annotation_position="top left")
                fig_lider.update_layout(
                        xaxis_title="", yaxis_title="", template="plotly_white",
                        font=dict(color='black', size=14, family='Arial'),
                        xaxis=dict(tickfont=dict(color='black', size=14)),
                        yaxis=dict(
                            showticklabels=False,  # <-- ADICIONE ESTA LINHA
                            range=[0, max(1, max_valor_lider * 1.6)]
                        ),
                        margin=dict(t=100)
                    )
                st.plotly_chart(fig_lider, use_container_width=True, key=f"grafico_lider_campo_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO LÍDER DE CAMPO.")
                
        st.markdown("<hr>", unsafe_allow_html=True)
                
        col5, col6 = st.columns([1, 1])
        
        with col5:    
            

            # --- Início do cálculo de metas acumuladas por função ---
            qtd_meses_calc = len(meses_selecionados) if meses_selecionados else 1

            # Metas base mensais por pessoa
            if "REGIONAL MT" in regionais_selecionadas:
                meta_base_sesmt = 24
                meta_base_coordenacao = 4
                meta_base_supervisao = 15
                meta_base_lider_campo = 15
            else:
                meta_base_sesmt = 15
                meta_base_coordenacao = 4
                meta_base_supervisao = 8
                meta_base_lider_campo = 8
            
            # Quantidade de inspetores ativos em cada categoria
            qtd_ativos_sesmt = len(ativos_sesmt)
            qtd_ativos_coordenacao = len(ativos_coordenacao)
            qtd_ativos_supervisao = len(ativos_supervisao)
            qtd_ativos_lider_campo = len(ativos_lider_campo)

            # Metas Acumuladas
            meta_acumulada_sesmt = qtd_ativos_sesmt * meta_base_sesmt * qtd_meses_calc
            meta_acumulada_coordenacao = qtd_ativos_coordenacao * meta_base_coordenacao * qtd_meses_calc
            meta_acumulada_supervisao = qtd_ativos_supervisao * meta_base_supervisao * qtd_meses_calc
            meta_acumulada_lider_campo = qtd_ativos_lider_campo * meta_base_lider_campo * qtd_meses_calc

            # Totais realizados por função
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_coordenacao = blitz_por_instrutor_coordenacao['quantidade_blitz'].sum()
            total_supervisao = blitz_por_instrutor_supervisao['quantidade_blitz'].sum()
            total_lider_campo = blitz_por_instrutor_lider_campo['quantidade_blitz'].sum()
            
            # Cálculo de atingimento
            atingimento_sesmt = (total_sesmt / meta_acumulada_sesmt * 100) if meta_acumulada_sesmt > 0 else 0
            atingimento_coordenacao = (total_coordenacao / meta_acumulada_coordenacao * 100) if meta_acumulada_coordenacao > 0 else 0
            atingimento_supervisao = (total_supervisao / meta_acumulada_supervisao * 100) if meta_acumulada_supervisao > 0 else 0
            atingimento_lider_campo = (total_lider_campo / meta_acumulada_lider_campo * 100) if meta_acumulada_lider_campo > 0 else 0

            
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>TOTAL DE INSPEÇÕES POR FUNÇÃO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Somar o total de inspeções para cada categoria
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_supervisao = blitz_por_instrutor_supervisao['quantidade_blitz'].sum()
            total_coordenacao = blitz_por_instrutor_coordenacao['quantidade_blitz'].sum()
            total_lider_campo = blitz_por_instrutor_lider_campo['quantidade_blitz'].sum()

            # Criar um DataFrame para o gráfico
            dados_totais = pd.DataFrame({
                'Função': ['SESMT', 'Supervisão', 'Coordenação', 'Líder de Campo'],
                'Total de Inspeções': [total_sesmt, total_supervisao, total_coordenacao, total_lider_campo]
            })

            # Cores para cada barra
            cores_funcoes = {
                'SESMT': '#1f77b4',
                'Supervisão': '#ff7f0e',
                'Coordenação': '#2ca02c',
                'Líder de Campo': '#9467bd'
            }

            fig_totais = px.bar(
                dados_totais,
                x='Função',
                y='Total de Inspeções',
                text='Total de Inspeções',
                color='Função',
                color_discrete_map=cores_funcoes
            )
            
            max_total = dados_totais['Total de Inspeções'].max()

            fig_totais.update_traces(
                textposition='outside',
                textfont=dict(color='black', size=16)
            )

            fig_totais.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                template="plotly_white",
                font=dict(color='black', size=14),
                xaxis=dict(tickfont=dict(color='black', size=16)),
                yaxis=dict(
                    showticklabels=False,  # <-- ADICIONE ESTA LINHA
                    range=[0, max(1, max_total * 1.25)]
                ),
                margin=dict(t=50, b=50)
            )
            
            st.plotly_chart(fig_totais, use_container_width=True, key=f"grafico_totais_funcao_{uuid.uuid4()}")
        st.markdown("<hr>", unsafe_allow_html=True)
            
        with col6:
            

            # --- Início do cálculo de metas acumuladas ---
            qtd_meses_calc = len(meses_selecionados) if meses_selecionados else 1

            # Metas base por pessoa
            if "REGIONAL MT" in regionais_selecionadas:
                meta_base_sesmt = 24
                meta_base_coordenacao = 4
                meta_base_supervisao = 15
                meta_base_lider_campo = 15
            else:
                meta_base_sesmt = 15
                meta_base_coordenacao = 4
                meta_base_supervisao = 8
                meta_base_lider_campo = 8
            
            # Quantidade de inspetores ativos em cada categoria
            qtd_ativos_sesmt = len(ativos_sesmt)
            qtd_ativos_coordenacao = len(ativos_coordenacao)
            qtd_ativos_supervisao = len(ativos_supervisao)
            qtd_ativos_lider_campo = len(ativos_lider_campo)

            # Meta Acumulada SESMT
            meta_acumulada_sesmt = qtd_ativos_sesmt * meta_base_sesmt * qtd_meses_calc

            # Meta Acumulada Liderança (soma das metas individuais)
            meta_acumulada_lideranca = (qtd_ativos_coordenacao * meta_base_coordenacao * qtd_meses_calc) + \
                                        (qtd_ativos_supervisao * meta_base_supervisao * qtd_meses_calc) + \
                                        (qtd_ativos_lider_campo * meta_base_lider_campo * qtd_meses_calc)

            # Totais realizados
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_lideranca = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].sum()
            
            # Cálculo de atingimento
            atingimento_sesmt = (total_sesmt / meta_acumulada_sesmt * 100) if meta_acumulada_sesmt > 0 else 0
            atingimento_lideranca = (total_lideranca / meta_acumulada_lideranca * 100) if meta_acumulada_lideranca > 0 else 0
            
            # Exibir métricas de atingimento
            
            
            
            
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>TAXA INSPEÇÃO POR SESMT E LIDERANÇA</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )


            # Gráfico de barras com os totais (como antes)
            dados_consolidados = pd.DataFrame({
                'Tipo de Inspeção': ['INSPEÇÃO SESMT', 'INSPEÇÃO LIDERANÇA'],
                'Quantidade de Inspeções': [total_sesmt, total_lideranca]
            })

            if not dados_consolidados.empty:
                cores = {
                    'INSPEÇÃO SESMT': '#1f77b4',
                    'INSPEÇÃO LIDERANÇA': '#ff7f0e'
                }
                fig_barras = px.bar(
                    dados_consolidados,
                    x='Tipo de Inspeção',
                    y='Quantidade de Inspeções',
                    text='Quantidade de Inspeções',
                    color='Tipo de Inspeção',
                    color_discrete_map=cores
                )
                max_valor = dados_consolidados['Quantidade de Inspeções'].max() if not dados_consolidados.empty else 1
                fig_barras.update_traces(
                    textposition='outside',
                    textfont=dict(color='black', size=16)
                )
                fig_barras.update_layout(
                    xaxis_title="", yaxis_title="", showlegend=False, template="plotly_white",
                    font=dict(color='black', size=14),
                    xaxis=dict(tickfont=dict(color='black', size=16)),
                    yaxis=dict(tickfont=dict(color='black', size=14), range=[0, max(1, max_valor * 1.25)]),
                    margin=dict(t=50, b=50)
                )
                st.plotly_chart(fig_barras, use_container_width=True, key=f"grafico_inspecoes_barra_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para consolidar as inspeções.")
        with col5:
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 20px;">
                <h4 style="font-size:28px;"><strong>ATINGIMENTO DE METAS ACUMULADAS</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # --- Início do cálculo de metas acumuladas por função ---
            qtd_meses_calc = len(meses_selecionados) if meses_selecionados else 1

            # Metas base mensais por pessoa
            if "REGIONAL MT" in regionais_selecionadas:
                meta_base_sesmt = 24
                meta_base_coordenacao = 4
                meta_base_supervisao = 15
                meta_base_lider_campo = 15
            else:
                meta_base_sesmt = 15
                meta_base_coordenacao = 4
                meta_base_supervisao = 8
                meta_base_lider_campo = 8
            
            # Quantidade de inspetores ativos em cada categoria
            qtd_ativos_sesmt = len(ativos_sesmt)
            qtd_ativos_coordenacao = len(ativos_coordenacao)
            qtd_ativos_supervisao = len(ativos_supervisao)
            qtd_ativos_lider_campo = len(ativos_lider_campo)

            # Metas Acumuladas
            meta_acumulada_sesmt = qtd_ativos_sesmt * meta_base_sesmt * qtd_meses_calc
            meta_acumulada_coordenacao = qtd_ativos_coordenacao * meta_base_coordenacao * qtd_meses_calc
            meta_acumulada_supervisao = qtd_ativos_supervisao * meta_base_supervisao * qtd_meses_calc
            meta_acumulada_lider_campo = qtd_ativos_lider_campo * meta_base_lider_campo * qtd_meses_calc

            # Totais realizados por função
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_coordenacao = blitz_por_instrutor_coordenacao['quantidade_blitz'].sum()
            total_supervisao = blitz_por_instrutor_supervisao['quantidade_blitz'].sum()
            total_lider_campo = blitz_por_instrutor_lider_campo['quantidade_blitz'].sum()
            
            # Cálculo de atingimento
            atingimento_sesmt = (total_sesmt / meta_acumulada_sesmt * 100) if meta_acumulada_sesmt > 0 else 0
            atingimento_coordenacao = (total_coordenacao / meta_acumulada_coordenacao * 100) if meta_acumulada_coordenacao > 0 else 0
            atingimento_supervisao = (total_supervisao / meta_acumulada_supervisao * 100) if meta_acumulada_supervisao > 0 else 0
            atingimento_lider_campo = (total_lider_campo / meta_acumulada_lider_campo * 100) if meta_acumulada_lider_campo > 0 else 0

            # --- HTML e CSS para os cartões de KPI ---
            
            # Função para determinar a cor da barra de progresso
            def get_progress_color(percentage):
                if percentage >= 100:
                    return "#28a745"  # Verde (sucesso)
                elif percentage >= 70:
                    return "#ffc107"  # Amarelo (atenção)
                else:
                    return "#dc3545"  # Vermelho (perigo)

            # Função para criar um cartão de KPI
            def create_kpi_card(title, icon, percentage, realizado, meta, color):
                progress_color = get_progress_color(percentage)
                # Garante que a barra não passe de 100% visualmente
                progress_width = min(percentage, 100)

                return f"""
                <div style="background-color: {color}; border-radius: 10px; padding: 20px; color: white; margin-bottom: 15px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);">
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 1.2em;">
                        <span style="font-weight: bold;">{title}</span>
                        <span>{icon}</span>
                    </div>
                    <div style="font-size: 2.5em; font-weight: bold; margin-top: 10px; text-align: center;">
                        {percentage:.1f}%
                    </div>
                    <div style="text-align: center; font-size: 0.9em; opacity: 0.9;">
                        Realizado: {realizado} / Meta: {meta}
                    </div>
                    <div style="background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 10px; margin-top: 15px;">
                        <div style="width: {progress_width}%; background-color: {progress_color}; height: 10px; border-radius: 5px;"></div>
                    </div>
                </div>
                """

            # Criar e exibir os cartões
            card_sesmt = create_kpi_card("SESMT", "", atingimento_sesmt, total_sesmt, meta_acumulada_sesmt, "#1f77b4")
            card_coordenacao = create_kpi_card("COORDENAÇÃO", "", atingimento_coordenacao, total_coordenacao, meta_acumulada_coordenacao, "#2ca02c")
            card_supervisao = create_kpi_card("SUPERVISÃO", "", atingimento_supervisao, total_supervisao, meta_acumulada_supervisao, "#ff7f0e")
            card_lider_campo = create_kpi_card("LÍDER DE CAMPO", "", atingimento_lider_campo, total_lider_campo, meta_acumulada_lider_campo, "#9467bd")

            st.markdown(card_sesmt, unsafe_allow_html=True)
            st.markdown(card_coordenacao, unsafe_allow_html=True)
            st.markdown(card_supervisao, unsafe_allow_html=True)
            st.markdown(card_lider_campo, unsafe_allow_html=True)
            
        with col6:
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 20px;">
                <h4 style="font-size:28px;"><strong>ATINGIMENTO DE METAS - GRUPOS</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # --- Início do cálculo de metas acumuladas ---
            qtd_meses_calc = len(meses_selecionados) if meses_selecionados else 1

            # Metas base por pessoa
            if "REGIONAL MT" in regionais_selecionadas:
                meta_base_sesmt = 24
                meta_base_coordenacao = 4
                meta_base_supervisao = 15
                meta_base_lider_campo = 15
            else:
                meta_base_sesmt = 15
                meta_base_coordenacao = 4
                meta_base_supervisao = 8
                meta_base_lider_campo = 8
            
            # Quantidade de inspetores ativos em cada categoria
            qtd_ativos_sesmt = len(ativos_sesmt)
            qtd_ativos_coordenacao = len(ativos_coordenacao)
            qtd_ativos_supervisao = len(ativos_supervisao)
            qtd_ativos_lider_campo = len(ativos_lider_campo)

            # Meta Acumulada SESMT
            meta_acumulada_sesmt = qtd_ativos_sesmt * meta_base_sesmt * qtd_meses_calc

            # Meta Acumulada Liderança (soma das metas individuais)
            meta_acumulada_lideranca = (qtd_ativos_coordenacao * meta_base_coordenacao * qtd_meses_calc) + \
                                        (qtd_ativos_supervisao * meta_base_supervisao * qtd_meses_calc) + \
                                        (qtd_ativos_lider_campo * meta_base_lider_campo * qtd_meses_calc)

            # Totais realizados
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_lideranca = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].sum()
            
            # Cálculo de atingimento
            atingimento_sesmt = (total_sesmt / meta_acumulada_sesmt * 100) if meta_acumulada_sesmt > 0 else 0
            atingimento_lideranca = (total_lideranca / meta_acumulada_lideranca * 100) if meta_acumulada_lideranca > 0 else 0
            
            # --- HTML e CSS para os cartões de KPI (mesma função da col5) ---
            def get_progress_color(percentage):
                if percentage >= 100: return "#28a745"
                elif percentage >= 70: return "#ffc107"
                else: return "#e6d540"

            def create_kpi_card(title, icon, percentage, realizado, meta, color):
                progress_color = get_progress_color(percentage)
                progress_width = min(percentage, 100)
                return f"""
                <div style="background-color: {color}; border-radius: 10px; padding: 20px; color: white; margin-bottom: 15px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);">
                    <div style="display: flex; align-items: center; justify-content: space-between; font-size: 1.2em;">
                        <span style="font-weight: bold;">{title}</span>
                        <span>{icon}</span>
                    </div>
                    <div style="font-size: 2.5em; font-weight: bold; margin-top: 10px; text-align: center;">
                        {percentage:.1f}%
                    </div>
                    <div style="text-align: center; font-size: 0.9em; opacity: 0.9;">
                        Realizado: {realizado} / Meta: {meta}
                    </div>
                    <div style="background-color: rgba(255, 255, 255, 0.3); border-radius: 5px; height: 10px; margin-top: 15px;">
                        <div style="width: {progress_width}%; background-color: {progress_color}; height: 10px; border-radius: 5px;"></div>
                    </div>
                </div>
                """

            # Criar e exibir os cartões para os grupos
            card_sesmt_grupo = create_kpi_card("SESMT", "", atingimento_sesmt, total_sesmt, meta_acumulada_sesmt, "#1f77b4")
            card_lideranca_grupo = create_kpi_card("LIDERANÇA", "", atingimento_lideranca, total_lideranca, meta_acumulada_lideranca, "#ff460e")

            
            
            st.markdown(card_sesmt_grupo, unsafe_allow_html=True)
            
            st.markdown(card_lideranca_grupo, unsafe_allow_html=True)

            



    with INSPECAO:
    
        import uuid

        qtd_meses = len(meses_selecionados)

        # ⚡️ NOVO: Lógica condicional para as metas com base na regional selecionada ⚡️
        # A nova regra se aplica se "REGIONAL MT" estiver entre as regionais escolhidas.
        if "REGIONAL MT" in regionais_selecionadas:
            meta_sesmt = 24 * qtd_meses
            # A meta de liderança agrupada será a soma das metas individuais
            meta_lideranca = 15 * qtd_meses 
        else:
            meta_sesmt = 15 * qtd_meses
            # A meta de liderança agrupada será a soma das metas individuais
            meta_lideranca = 8 * qtd_meses

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES SESMT</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_sesmt_sem_pessoas.empty:
                max_valor = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].max()

                fig_sesmt = px.bar(
                    blitz_por_instrutor_sesmt_sem_pessoas,
                    x='nome_inspetor',
                    y='quantidade_blitz',
                    text='quantidade_blitz',
                    title=""
                )

                fig_sesmt.update_traces(
                    marker_color='#1f77b4',
                    marker_line_color='black',
                    marker_line_width=1.5,
                    textposition='outside',
                    textfont=dict(
                        color='black',
                        size=16,
                        family='Arial'
                    )
                )

                fig_sesmt.add_hline(
                    y=meta_sesmt,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Meta: {meta_sesmt}",
                    annotation_position="top left"
                )

                fig_sesmt.update_layout(
                    xaxis_title="",
                    yaxis_title="",
                    template="plotly_white",
                    font=dict(color='black', size=14, family='Arial'),
                    xaxis=dict(tickfont=dict(color='black', size=14)),
                    yaxis=dict(
                        tickfont=dict(color='black', size=14),
                        range=[0, max(1, max_valor * 1.2)]
                    ),
                    margin=dict(t=100)
                )

                st.plotly_chart(fig_sesmt, use_container_width=True, key=f"grafico_sesmt_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO SESMT.")

        with col2:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES LIDERANÇA</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            if not blitz_por_instrutor_lideranca_sem_pessoas.empty:
                max_valor_lideranca = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].max()

                fig_lideranca = px.bar(
                    blitz_por_instrutor_lideranca_sem_pessoas,
                    x='nome_inspetor',
                    y='quantidade_blitz',
                    text='quantidade_blitz',
                    title=""
                )

                fig_lideranca.update_traces(
                    marker_color='#ff7f0e',
                    marker_line_color='black',
                    marker_line_width=1.5,
                    textposition='outside',
                    textfont=dict(
                        color='black',
                        size=16,
                        family='Arial'
                    )
                )

                fig_lideranca.add_hline(
                    y=meta_lideranca,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Meta: {meta_lideranca}",
                    annotation_position="top left"
                )

                fig_lideranca.update_layout(
                    xaxis_title="",
                    yaxis_title="",
                    template="plotly_white",
                    font=dict(color='black', size=14, family='Arial'),
                    xaxis=dict(tickfont=dict(color='black', size=14)),
                    yaxis=dict(
                        tickfont=dict(color='black', size=14),
                        range=[0, max(1, max_valor_lideranca * 1.6)]
                    ),
                    margin=dict(t=100)
                )

                st.plotly_chart(fig_lideranca, use_container_width=True, key=f"grafico_lideranca_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para INSPEÇÃO LIDERANÇA.")

                # O restante do seu código para as outras abas (CONTATO, REPROVACAO, etc.) continua aqui...
                # Se este for o seu script principal, você pode chamar a função no final
                # if __name__ == "__main__":
                #     app()
             
        
                                
                
                
                

        #-------------------------------------------------------------------------------------------------------------------------------#
        #------------------------------------- Tipo de Inspeções -----------------------------------------------------------------------#

    
        col1, col2, col3, col4 = st.columns(4)

        # Gráfico de Inspeções por Tipo de Inspeção
        with col2:
            

            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>TAXA INSPEÇÃO POR SESMT E LIDERANÇA</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Aqui você já deve ter definido esses dois dataframes antes no código:
            # blitz_por_instrutor_sesmt_sem_pessoas
            # blitz_por_instrutor_lideranca_sem_pessoas

            # Agora soma as inspeções por grupo, usando a mesma base que nos gráficos de barras
            total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
            total_lideranca = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].sum()

            dados_consolidados = pd.DataFrame({
                'Tipo de Inspeção': ['INSPEÇÃO SESMT', 'INSPEÇÃO LIDERANÇA'],
                'Quantidade de Inspeções': [total_sesmt, total_lideranca]
            })

            if not dados_consolidados.empty:
                fig_rosca = px.pie(
                    dados_consolidados,
                    names='Tipo de Inspeção',
                    values='Quantidade de Inspeções',
                    hole=0.5,
                    hover_data=['Quantidade de Inspeções']
                )

                fig_rosca.update_traces(
                    textposition='inside',
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18)
                )

                fig_rosca.update_layout(
                    showlegend=True,
                    legend_title_text='Tipo de Inspeção',
                    template="plotly_white",
                    annotations=[
                        dict(
                            text=f"<b>Inspeções</b><br><span style='font-size:20px; color:black'><b>{total_sesmt + total_lideranca}</b></span>",
                            x=0.5,
                            y=0.5,
                            font=dict(color='black', size=20),
                            showarrow=False
                        )
                    ],
                    legend=dict(font=dict(size=16, color='black'))
                )

                st.plotly_chart(fig_rosca, use_container_width=True, key=f"grafico_inspecoes_roda_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para consolidar as inspeções.")

#

        # Gráfico de Inspeções por Tipo de Equipe
        with col1:
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>TAXA INSPEÇÃO POR TIPO DE EQUIPE</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            total_inspecoes = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum() + blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].sum()


            # Criar uma cópia para evitar modificar o df original
            df_temp = df_filtrado.copy()

            # Criar a "medida" do tipo de equipe diretamente
            def identificar_tipo(num_op):
                num_op = str(num_op)
                if num_op.startswith('9'):
                    return 'EQUIPE LEVE'
                elif num_op.startswith('8'):
                    return 'EQUIPE PESADA'
                elif num_op.startswith('7'):
                    return 'EQUIPE DE LINHA'
                elif num_op.startswith('4'):
                    return 'EQUIPE DE MOTOCICLETA'
                else:
                    return 'Outros'

            df_temp['tipo_calculado'] = df_temp['num_operacional'].astype(str).apply(identificar_tipo)

            inspecoes_por_tipo_equipe = df_temp.groupby("tipo_calculado").agg(
                quantidade_inspecoes=('idtb_turnos', 'nunique')
            ).reset_index()

            inspecoes_por_tipo_equipe['porcentagem'] = (inspecoes_por_tipo_equipe['quantidade_inspecoes'] / total_inspecoes) * 100

            if not inspecoes_por_tipo_equipe.empty:
                fig_rosca_tipo_equipe = px.pie(
                    inspecoes_por_tipo_equipe,
                    names='tipo_calculado',
                    values='quantidade_inspecoes',
                    hole=0.5,
                    hover_data=['porcentagem']
                )

                # Indicadores nas fatias
                fig_rosca_tipo_equipe.update_traces(
                    textposition='inside',
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18)  # maior e branco
                )

                # Texto central (preto e grande)
                fig_rosca_tipo_equipe.update_layout(
                    showlegend=True,
                    legend_title_text='Tipo de Equipe',
                    template="plotly_white",
                    annotations=[
                        dict(
                            text=f"<b>Inspeções</b><br><span style='font-size:20px; color:black'><b>{total_inspecoes}</b></span>",
                            x=0.5,
                            y=0.5,
                            font=dict(size=20, color='black'),
                            showarrow=False
                        )
                    ],
                    legend=dict(
                        font=dict(size=16, color='black')  # aumenta e deixa a legenda preta
                    )
                )

                st.plotly_chart(fig_rosca_tipo_equipe, use_container_width=True)
            else:
                st.warning("Nenhum dado disponível para quantidade de inspeções por tipo de equipe.")


        # Gráfico de Inspeções por Unidade
        with col3:
            st.markdown(
            """
            <div style="text-align: center;">
            <h4 style="font-size:28px;"><strong>TAXA INSPEÇÃO POR UNIDADE</strong></h4>
            </div>
            """,
            unsafe_allow_html=True
            )

            inspecoes_por_unidade = df_filtrado.groupby("unidade").agg(
                quantidade_inspecoes=('idtb_turnos', 'nunique')
            ).reset_index()

            inspecoes_por_unidade['porcentagem'] = (inspecoes_por_unidade['quantidade_inspecoes'] / total_inspecoes) * 100

            if not inspecoes_por_unidade.empty:
                fig_rosca_unidade = px.pie(
                    inspecoes_por_unidade,
                    names='unidade',
                    values='quantidade_inspecoes',
                    hole=0.5,
                    hover_data=['porcentagem']
                )

                fig_rosca_unidade.update_traces(
                    textposition='inside',
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18)
                )

                fig_rosca_unidade.update_layout(
                    showlegend=True,
                    legend_title_text='Unidade',
                    template="plotly_white",
                    annotations=[
                        dict(
                            text=f"<b>Inspeções</b><br><span style='font-size:20px; color:black'><b>{total_inspecoes}</b></span>",
                            x=0.5,
                            y=0.5,
                            font=dict(size=20, color='black'),
                            showarrow=False
                        )
                    ],
                    legend=dict(font=dict(size=16, color='black'))
                )

                st.plotly_chart(fig_rosca_unidade, use_container_width=True)
            else:
                st.warning("Nenhum dado disponível para quantidade de inspeções por unidade.")

        with col4:
            
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>LOCALIZAÇÕES DAS INSPEÇÕES</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Base única por inspeção
            df_inspecoes_zona = df_filtrado[['nome_inspetor', 'idtb_turnos', 'zona_inspecao']].drop_duplicates()

            # Remove NaN e filtra apenas RURAL e URBANA
            df_inspecoes_zona = df_inspecoes_zona[df_inspecoes_zona['zona_inspecao'].isin(['RURAL', 'URBANA'])]

            # Agrupamento
            inspecoes_por_zona = df_inspecoes_zona.groupby("zona_inspecao").agg(
                quantidade_inspecoes=('idtb_turnos', 'nunique')
            ).reset_index()

            total_inspecoes_zona = inspecoes_por_zona['quantidade_inspecoes'].sum()
            inspecoes_por_zona['porcentagem'] = (inspecoes_por_zona['quantidade_inspecoes'] / total_inspecoes_zona) * 100

            # Gráfico de rosca
            if not inspecoes_por_zona.empty:
                fig_rosca_zona = px.pie(
                    inspecoes_por_zona,
                    names='zona_inspecao',
                    values='quantidade_inspecoes',
                    hole=0.5,
                    hover_data=['porcentagem']
                )

                fig_rosca_zona.update_traces(
                    textposition='inside',
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18)
                )

                fig_rosca_zona.update_layout(
                    showlegend=True,
                    legend_title_text='Zona',
                    template="plotly_white",
                    annotations=[
                        dict(
                            text=f"<b>Inspeções</b><br><span style='font-size:20px; color:black'><b>{total_inspecoes_zona}</b></span>",
                            x=0.5,
                            y=0.5,
                            font=dict(size=20, color='black'),
                            showarrow=False
                        )
                    ],
                    legend=dict(
                        font=dict(size=16, color='black')
                    )
                )

                st.plotly_chart(fig_rosca_zona, use_container_width=True)
            else:
                st.warning("Nenhum dado disponível para quantidade de inspeções por zona.")

    #-------------------------------------------------------------------------------------------------------------------#
    #-------------------------------- Por Tipo de Prefixo --------------------------------------------------------------#         

        st.markdown(
            """
            <div style="text-align: center;">
            <h4 style="font-size:28px;"><strong>INSPEÇÕES POR TIPO DE PREFIXO</strong></h4>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not df_filtrado.empty:
            # Junta com df_turnos para pegar descricao_tipo_prefixo
            df_merged_prefixo = pd.merge(
                df_filtrado[['idtb_turnos']].drop_duplicates(),
                df_turnos[['idtb_turnos', 'descricao_tipo_prefixo']],
                on='idtb_turnos',
                how='left'
            )

            # Agrupa e conta inspeções únicas por prefixo
            prefixo_agg = df_merged_prefixo.groupby('descricao_tipo_prefixo').agg(
                quantidade_blitz=('idtb_turnos', 'nunique')
            ).reset_index()

            # Cálculo para altura dinâmica
            max_valor_prefixo = prefixo_agg['quantidade_blitz'].max()

            fig_prefixo = px.bar(
                prefixo_agg,
                x="descricao_tipo_prefixo",
                y="quantidade_blitz",
                text="quantidade_blitz"
            )

            fig_prefixo.update_traces(
                marker_color='#2ca02c',
                marker_line_color='black',
                marker_line_width=1.5,
                textposition='outside',
                textfont=dict(
                    color='black',
                    size=16,
                    family='Arial'
                )
            )

            fig_prefixo.update_layout(
                xaxis_title="",
                yaxis_title="",
                template="plotly_white",
                font=dict(color='black', size=14, family='Arial'),
                xaxis=dict(tickfont=dict(color='black', size=14)),
                yaxis=dict(
                    tickfont=dict(color='black', size=14),
                    range=[0, max_valor_prefixo * 3.0]  # aumenta para não cortar textos
                ),
                margin=dict(t=100)
            )

            st.plotly_chart(fig_prefixo, use_container_width=True, key=f"grafico_prefixo_{uuid.uuid4()}")
        else:
            st.warning("Nenhum dado disponível para INSPEÇÕES POR TIPO DE PREFIXO.")

        st.markdown("""<hr>""", unsafe_allow_html=True)

    #--------------------------------------------------------------------------------------------------------------------------------#
    #------------------------------------------------Taxa de Contato-----------------------------------------------------------------#
    with CONTATO:
            
        # TAXA DE CONTATO       
        col1, col2 = st.columns(2)

        with col1:
            
            st.markdown("""
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>EQUIPES INSPECIONADAS</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            # Agrupar os dados
            inspecoes_por_equipe = df_filtrado.groupby("prefixo", as_index=False).agg(
                quantidade_inspecoes=('idtb_turnos', 'nunique')
            )

            # Garantir que 'num_operacional' seja string
            inspecoes_por_equipe['prefixo'] = inspecoes_por_equipe['prefixo'].astype(str)

            # Ordenar
            inspecoes_por_equipe = inspecoes_por_equipe.sort_values("quantidade_inspecoes", ascending=False)

            if not inspecoes_por_equipe.empty:
                max_valor_equipe = inspecoes_por_equipe['quantidade_inspecoes'].max()

                fig_inspecoes_por_equipe = px.bar(
                    inspecoes_por_equipe,
                    x='prefixo',
                    y='quantidade_inspecoes',
                    labels={
                        'prefixo': 'Equipe',
                        'quantidade_inspecoes': 'Quantidade de Inspeções'
                    },
                    title='',
                    text='quantidade_inspecoes'
                )

                fig_inspecoes_por_equipe.update_traces(
                    marker_color='#2ca02c',
                    textposition='outside',
                    textfont=dict(size=16, color='black')
                )

                fig_inspecoes_por_equipe.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                    xaxis_title="",
                    yaxis_title="",
                    xaxis_tickangle=-45,
                    template="plotly_white",
                    font=dict(size=14, color='black'),
                    xaxis=dict(tickfont=dict(size=14, color='black')),
                    yaxis=dict(tickfont=dict(size=14, color='black'), range=[0, max_valor_equipe * 1.2]),
                    margin=dict(l=40, r=10, t=80, b=120)  # top aumentado
                )

                st.plotly_chart(fig_inspecoes_por_equipe, use_container_width=True, key=f"grafico_inspecoes_equipe_{uuid.uuid4()}")
            else:
                st.warning("Nenhum dado disponível para quantidade de inspeções por equipe.")

        with col2:
            
            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>PORCENTAGENS DE EQUIPES INSPECIONADAS POR MÊS</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            # Agrupamentos por mês
            inspecionadas_por_mes = df_filtrado.groupby(df_filtrado['data_turno'].dt.month)['prefixo'].nunique()
            total_turnos_por_mes = df_turnos.groupby(df_turnos['dt_inicio'].dt.month)['prefixo'].nunique()

            # Cálculo
            porcentagens_inspecionadas_por_mes = []
            porcentagens_nao_inspecionadas_por_mes = []
            quantidades_inspecionadas_por_mes = []
            quantidades_nao_inspecionadas_por_mes = []

            for mes in meses_selecionados:
                inspecionadas = inspecionadas_por_mes.get(mes, 0)
                total_turnos = total_turnos_por_mes.get(mes, 0)
                if total_turnos > 0:
                    pct_inspecionada = (inspecionadas / total_turnos) * 100
                else:
                    pct_inspecionada = 0
                porcentagens_inspecionadas_por_mes.append(round(pct_inspecionada, 2))
                porcentagens_nao_inspecionadas_por_mes.append(round(100 - pct_inspecionada, 2))
                quantidades_inspecionadas_por_mes.append(inspecionadas)
                quantidades_nao_inspecionadas_por_mes.append(total_turnos - inspecionadas)

            # DataFrame final
            nomes_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

            df_porcentagens = pd.DataFrame({
                'Mês': [nomes_meses[mes - 1] for mes in meses_selecionados],
                'Inspecionada': porcentagens_inspecionadas_por_mes,
                'Não Inspecionada': porcentagens_nao_inspecionadas_por_mes,
                'Quantidade Inspecionada': quantidades_inspecionadas_por_mes,
                'Quantidade Não Inspecionada': quantidades_nao_inspecionadas_por_mes
            })

            df_porcentagens['Mês'] = pd.Categorical(df_porcentagens['Mês'], categories=nomes_meses, ordered=True)
            df_porcentagens = df_porcentagens.sort_values('Mês')

            # Gráfico
            fig_porcentagens_mes = px.bar(
                df_porcentagens,
                x='Mês',
                y=['Inspecionada', 'Não Inspecionada'],
                labels={'value': 'Porcentagem', 'variable': 'Tipo'},
                title='',
                barmode='group',
                color_discrete_map={
                    'Inspecionada': '#2ca02c',
                    'Não Inspecionada': '#d62728'
                },
                text_auto=True
            )

            fig_porcentagens_mes.update_traces(
                texttemplate='%{y:.2f}%',
                textposition='outside',
                textfont=dict(size=16, color='black'),
                hovertemplate="<b>Mês: %{x}</b><br>Porcentagem: %{y:.2f}%",
                customdata=df_porcentagens[['Quantidade Inspecionada', 'Quantidade Não Inspecionada']]
            )

            fig_porcentagens_mes.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                xaxis_title="",
                yaxis_title="",
                template="plotly_white",
                font=dict(size=14, color='black'),
                legend=dict(font=dict(size=16, color='black')),
                xaxis=dict(tickfont=dict(size=14, color='black')),
                yaxis=dict(tickfont=dict(size=14, color='black'), range=[0, 120]),
                hovermode='closest',
                hoverlabel=dict(bgcolor="white", font_size=14, font_color="black"),
                margin=dict(t=80)
            )

            # Exibir
            st.plotly_chart(fig_porcentagens_mes, use_container_width=True, key=f"grafico_porcentagens_mes_{uuid.uuid4()}")

            #----------------------------------------------------------------------------------------------------------------------#
            #----------------------------------------- Taxa de Contado Tipo de Equipe ---------------------------------------------#    

        # Função para encurtar nomes de abas (máximo 31 caracteres para Excel)
        def encurtar_nome_aba(nome):
            return nome[:31]

        # Função para classificar equipes
        def classificar_equipes(df):
            df['tipo_equipe'] = df['num_operacional'].astype(str).apply(
                lambda x: 'Equipe Leve' if x.startswith('9')
                else 'Equipe Pesada' if x.startswith('8')
                else 'Equipe de Linha Viva' if x.startswith('7')
                else 'Equipe de Motocicleta' if x.startswith('4')
                else 'Outros'
        )
            return df

        # Aplicar classificação
        df_filtrado = classificar_equipes(df_filtrado)
        df_turnos = classificar_equipes(df_turnos)

        # Total de equipes distintas nos turnos
        equipes_total_no_turno = sorted(df_turnos['prefixo'].dropna().astype(str).unique())
        equipes_inspecionadas_no_turno = sorted(df_filtrado['prefixo'].dropna().astype(str).unique())

        # Agora sim: diferença correta
        equipes_nao_inspecionadas_no_turno = sorted(
            list(set(equipes_total_no_turno) - set(equipes_inspecionadas_no_turno))
        )

        # Contadores
        total_inspecionadas = len(equipes_inspecionadas_no_turno)
        total_nao_inspecionadas = len(equipes_nao_inspecionadas_no_turno)

        # Cores
        color_map = {
            'Inspecionadas': '#2ca02c',
            'Não Inspecionadas': '#d62728'
        }

        # Colunas de layout
        colunas = st.columns(5)

        # GRÁFICO GERAL
        labels_geral = ['Inspecionadas', 'Não Inspecionadas']
        sizes_geral = [total_inspecionadas, total_nao_inspecionadas]

        fig_geral = px.pie(
            values=sizes_geral,
            names=labels_geral,
            title='Taxa de Contato - Geral',
            color=labels_geral,
            color_discrete_map=color_map
        )

        fig_geral.update_traces(
            textinfo='percent+label',
            pull=[0.1, 0],
            hoverinfo='label+percent+value',
            hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}"
        )

        fig_geral.update_layout(
            showlegend=False,
            template="plotly_white",
            hovermode='closest',
            hoverlabel=dict(bgcolor="white", font_size=14, font_color="black")
        )

        with colunas[0]:
            st.plotly_chart(fig_geral, use_container_width=True)

            # DOWNLOAD GERAL
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame({'Equipes Inspecionadas': equipes_inspecionadas_no_turno}).to_excel(writer, index=False, sheet_name=encurtar_nome_aba('Inspecionadas_Geral'))
                pd.DataFrame({'Equipes Não Inspecionadas': equipes_nao_inspecionadas_no_turno}).to_excel(writer, index=False, sheet_name=encurtar_nome_aba('Não_Inspecionadas_Geral'))

                df_eletricistas = df_filtrado[df_filtrado['funcao'].str.contains('Eletricista', case=False, na=False)][['nome', 'funcao', 'prefixo']]
                df_eletricistas['Status Inspeção'] = df_eletricistas['prefixo'].astype(str).apply(
                    lambda x: 'Inspecionada' if x in equipes_inspecionadas_no_turno else 'Não Inspecionada'
                )
                df_eletricistas = df_eletricistas.rename(columns={'nome': 'Nome', 'funcao': 'Função', 'prefixo': 'Equipe'})
                df_eletricistas.to_excel(writer, index=False, sheet_name=encurtar_nome_aba('Eletricistas'))

            st.download_button(
                label="📥 Baixar Dados do Gráfico Geral (Excel)",
                data=output.getvalue(),
                file_name='taxa_contato_geral.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
        tipos_equipe = ['Equipe Leve', 'Equipe Pesada', 'Equipe de Linha Viva', 'Equipe de Motocicleta']

        for i, tipo in enumerate(tipos_equipe):
            with colunas[i + 1]:  # colunas[0] é o gráfico geral
                df_tipo_filtrado = df_filtrado[df_filtrado['tipo_equipe'] == tipo]
                df_tipo_turnos = df_turnos[
                (df_turnos['tipo_equipe'] == tipo) &
                (df_turnos['unidade'].isin(unidades_selecionadas)) &
                (df_turnos['descricao_tipo_prefixo'].isin(prefixos_selecionados))
            ]

                equipes_total_tipo = sorted(df_tipo_turnos['prefixo'].dropna().astype(str).unique())
                equipes_inspecionadas_tipo = sorted(df_tipo_filtrado['prefixo'].dropna().astype(str).unique())
                equipes_nao_inspecionadas_tipo = sorted(
                    list(set(equipes_total_tipo) - set(equipes_inspecionadas_tipo))
                )

                labels_tipo = ['Inspecionadas', 'Não Inspecionadas']
                sizes_tipo = [len(equipes_inspecionadas_tipo), len(equipes_nao_inspecionadas_tipo)]

                fig_tipo = px.pie(
                    values=sizes_tipo,
                    names=labels_tipo,
                    title=f'Taxa de Contato - {tipo}',
                    color=labels_tipo,
                    color_discrete_map=color_map
                )

                fig_tipo.update_traces(
                    textinfo='percent+label',
                    pull=[0.1, 0],
                    hoverinfo='label+percent+value',
                    hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}"
                )
                fig_tipo.update_layout(
                    showlegend=False,
                    template="plotly_white",
                    hovermode='closest',
                    hoverlabel=dict(bgcolor="white", font_size=18, font_color="black")
                )

                st.plotly_chart(fig_tipo, use_container_width=True)

                # Download Excel por tipo
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    pd.DataFrame({'Equipes Inspecionadas': equipes_inspecionadas_tipo}).to_excel(writer, index=False, sheet_name=encurtar_nome_aba(f'Insp_{tipo}'))
                    pd.DataFrame({'Equipes Não Inspecionadas': equipes_nao_inspecionadas_tipo}).to_excel(writer, index=False, sheet_name=encurtar_nome_aba(f'Nao_Insp_{tipo}'))

                st.download_button(
                    label=f"📥 Baixar Dados do Gráfico {tipo} (Excel)",
                    data=output.getvalue(),
                    file_name=f'taxa_contato_{tipo}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

            #-----------------------------------------------------------------------------------------------------------------------------#
            #-----------------------------------------------Inpecionadas X Não Inspecionadas ---------------------------------------------#

        # Estilo CSS para os cartões
        estilo_bilhetes = """
        <style>
        .card {
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 15px;
            box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
            color: white;
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
        }
        .inspecionado {
            background-color: #2ca02c;
            border: 2px solid #1f7a1f;
        }
        .nao_inspecionado {
            background-color: #d62728;
            border: 2px solid #a81d1d;
        }
        .download-link {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 15px;
            background-color: #16181C;
            color: white;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .download-link:hover {
            background-color: #E7E7EC;
            color: white;
        }
        </style>
        """
        st.markdown(estilo_bilhetes, unsafe_allow_html=True)

        # Corrigir e ordenar os dados corretamente
        equipes_total_no_turno = sorted(df_turnos['prefixo'].dropna().astype(str).unique())
        equipes_inspecionadas_no_turno = sorted(df_filtrado['prefixo'].dropna().astype(str).unique())
        equipes_nao_inspecionadas_no_turno = sorted(list(set(equipes_total_no_turno) - set(equipes_inspecionadas_no_turno)))

        # Contagem
        total_inspecionadas = len(equipes_inspecionadas_no_turno)
        total_nao_inspecionadas = len(equipes_nao_inspecionadas_no_turno)

        # Cartões lado a lado
        col1, col2 = st.columns(2)

        # ✅ Cartão de Equipes Inspecionadas
        with col1:
            st.markdown(f"### ✅ Equipes Inspecionadas ({total_inspecionadas})")
            if total_inspecionadas > 0:
                equipes_texto = ", ".join(equipes_inspecionadas_no_turno)
                st.markdown(f'<div class="card inspecionado">{equipes_texto}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card inspecionado">Nenhuma equipe inspecionada</div>', unsafe_allow_html=True)

        # ❌ Cartão de Equipes Não Inspecionadas + Download
        with col2:
            st.markdown(f"### ❌ Equipes Não Inspecionadas ({total_nao_inspecionadas})")
            if total_nao_inspecionadas > 0:
                equipes_texto = ", ".join(equipes_nao_inspecionadas_no_turno)
                st.markdown(f'<div class="card nao_inspecionado">{equipes_texto}</div>', unsafe_allow_html=True)

                # Criar DataFrame
                df_nao = pd.DataFrame({'Equipes Não Inspecionadas': equipes_nao_inspecionadas_no_turno})
                csv = df_nao.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()

                # Link de download
                st.markdown(f'''
                    <a href="data:file/csv;base64,{b64}" download="equipes_nao_inspecionadas.csv" class="download-link">
                        📥 Baixar Tabela de Equipes Não Inspecionadas
                    </a>
                ''', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card nao_inspecionado">Todas as equipes foram inspecionadas</div>', unsafe_allow_html=True)

    #-----------------------------------------------------------------------------------------------------------------------------------------------#
    #------------------------------------------------ taxa de contato por tipo de prefixo ----------------------------------------------------#
            
        st.markdown("""
            <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>TAXA DE CONTATO POR TIPO DE PREFIXO</strong></h4>
            </div>
        """, unsafe_allow_html=True)

        if not df_filtrado.empty:
            # Inspecionadas por tipo de prefixo (distintas por equipe num_operacional)
            inspecionadas_prefixo = pd.merge(
                df_filtrado[['prefixo', 'idtb_turnos']].drop_duplicates(),
                df_turnos[['idtb_turnos', 'descricao_tipo_prefixo']],
                on='idtb_turnos',
                how='left'
            ).groupby('descricao_tipo_prefixo')['prefixo'].nunique()

            # Totais por tipo de prefixo (todas as equipes que abriram turno)
            total_prefixo = df_turnos.drop_duplicates(['prefixo', 'idtb_turnos']).groupby('descricao_tipo_prefixo')['prefixo'].nunique()

            # Monta DataFrame com as taxas
            taxa_prefixo = pd.DataFrame({
                'Tipo de Prefixo': total_prefixo.index,
                'Total Equipes': total_prefixo.values,
                'Equipes Inspecionadas': [inspecionadas_prefixo.get(prefixo, 0) for prefixo in total_prefixo.index]
            })

            taxa_prefixo['Taxa de Contato (%)'] = (
                taxa_prefixo['Equipes Inspecionadas'] / taxa_prefixo['Total Equipes'] * 100
            ).round(2)

            # Gráfico
            fig_taxa_prefixo = px.bar(
                taxa_prefixo,
                x='Tipo de Prefixo',
                y='Taxa de Contato (%)',
                text='Taxa de Contato (%)',
                color_discrete_sequence=['#2ca02c']
            )

            fig_taxa_prefixo.update_traces(
                texttemplate='%{y:.2f}%',
                textposition='outside',
                textfont=dict(size=16, color='black'),
                marker_line_color='black',
                marker_line_width=1.5
            )

            fig_taxa_prefixo.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                xaxis_title="",
                yaxis_title="",
                template="plotly_white",
                font=dict(size=14, color='black'),
                xaxis=dict(tickfont=dict(size=14, color='black')),
                yaxis=dict(tickfont=dict(size=14, color='black')),
                hovermode='closest',
                hoverlabel=dict(bgcolor="white", font_size=14, font_color="black")
            )

            st.plotly_chart(fig_taxa_prefixo, use_container_width=True, key="taxa_contato_prefixo")

        else:
            st.warning("Nenhum dado disponível para calcular a taxa de contato por prefixo.")
        #-----------------------------------------------------------------------------------------------------------------------------------#
        #--------------------------------------------Reprovações Não Conformidades----------------------------------------------------------#
    with REPROVACAO:
        
        # Garante que a pontuação é numérica
        df_respostas_filtradas['pontuacao'] = pd.to_numeric(df_respostas_filtradas['pontuacao'], errors='coerce').fillna(0).astype(int)

        def classificar_pontuacao(p):
                if p == 2:
                    return "Leve"
                elif p == 3:
                    return "Média"
                elif p == 5:
                    return "Grave"
                elif p == 10:
                    return "Gravíssima"
                return "Não Classificado"

        df_respostas_filtradas['classificacao_limpa'] = df_respostas_filtradas['pontuacao'].apply(classificar_pontuacao)

        total_nc = df_respostas_filtradas['Key'].count()

        col1, col2 = st.columns(2)

            # --- COLUNA 1: Subgrupos ---
        with col1:
                st.markdown(
                    """
                    <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>PONTUAÇÕES POR SUBGRUPO</strong></h4>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # 1. Agrupa e conta os dados (igual ao seu código)
                subgrupos_df = df_respostas_filtradas.groupby('subgrupo')['Key'].count().reset_index(name='quantidade')

                # 2. Calcula a porcentagem (para usar nos rótulos)
                # A variável 'total_nc' deve estar definida no seu código
                subgrupos_df['porcentagem'] = (subgrupos_df['quantidade'] / total_nc) * 100

                # 3. Ordena o DataFrame para o gráfico de barras (melhor visualização)
                subgrupos_df = subgrupos_df.sort_values('quantidade', ascending=False)

                # 4. Cria o gráfico de barras
                fig_subgrupo = go.Figure(data=[go.Bar(
                    x=subgrupos_df['subgrupo'],
                    y=subgrupos_df['quantidade'],
                    # Adiciona o texto em cima das barras (quantidade e porcentagem)
                    text=[f"{qnt}<br>({pct:.1f}%)" for qnt, pct in zip(subgrupos_df['quantidade'], subgrupos_df['porcentagem'])],
                    textposition='outside',
                    textfont=dict(color='black', size=14),
                    marker=dict(color='#1f77b4') # Você pode usar a mesma paleta de cores se desejar
                )])

                # 5. Atualiza o layout do gráfico
                fig_subgrupo.update_layout(
                    height=500,
                    showlegend=False, # Legenda não é necessária para este tipo de gráfico
                    template='plotly_white',
                    xaxis=dict(
                        title=None, # Remove o título do eixo X
                        tickfont=dict(size=14)
                    ),
                    yaxis=dict(
                        title=None, # Remove o título do eixo Y
                        showticklabels=False # Oculta os valores do eixo Y para um visual mais limpo
                    )
                )

                # Ajusta o eixo Y para dar espaço aos rótulos de texto
                fig_subgrupo.update_yaxes(range=[0, subgrupos_df['quantidade'].max() * 1.15])

                st.plotly_chart(fig_subgrupo, use_container_width=True)


            # --- COLUNA 2: NCs Criadas ---

        with col2:
                st.markdown(
                    """
                    <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>ADERÊNCIA DE CRIAÇÃO DE PONTUAÇÕES MONITORIA</strong></h4>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                ncs_criadas = df_respostas_filtradas[df_respostas_filtradas['nc_criada'].str.upper() == 'SIM'].shape[0]
                restantes = total_nc - ncs_criadas

                df_ncs = pd.DataFrame({
                    'Categoria': ['PONTUAÇÕES APP', 'PONTUAÇÕES CRIADAS PELA MONITORIA'],
                    'Quantidade': [restantes, ncs_criadas]
                })

                fig_nc = px.pie(
                    df_ncs,
                    names='Categoria',
                    values='Quantidade',
                    hole=0.5,
                    color='Categoria',
                    color_discrete_map={
                        'PONTUAÇÕES APP': '#1f77b4',
                        'PONTUAÇÕES CRIADAS PELA MONITORIA': '#8B4513'
                    }
                )

                fig_nc.update_traces(
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18),  # Indicadores maiores e brancos
                    hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}"
                )

                fig_nc.update_layout(height=500,  # ⬅️ aumenta a altura para evitar corte
                    title="",
                    annotations=[
                        dict(
                            text=f"<b>NCs</b><br><span style='font-size:20px; color:black'><b>{total_nc}</b></span>",
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                            font=dict(size=20, color='black'),
                            xref='paper',
                            yref='paper'
                        )
                    ],
                    showlegend=True,
                    template="plotly_white",
                    legend=dict(
                        font=dict(size=16, color='black')  # Legenda maior e preta
                    ),
                
                    hoverlabel=dict(
                    font=dict(color='black', size=14),
                    bgcolor='white',
                    bordercolor='gray'
                    )
                )    

                st.plotly_chart(fig_nc, use_container_width=True)


            # --- COLUNA 3: Tabela de Classificação ---

      
            

            #----------------------------------------------- Tabelas de Não Conformidades --------------------------------------------------------------#

        st.markdown(
            """
            <div style="text-align: center;">
            <h4 style="font-size:28px;"><strong>TABELA DE REPROVAÇÕES</strong></h4>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Total de reprovações reais
        total_reprovacoes = df_respostas_filtradas['Key'].count()

        # Agrupamento por pergunta e subgrupo
        tabela_perguntas = df_respostas_filtradas.groupby(['pergunta', 'subgrupo'])['Key'].count().reset_index(name='quantidade')
        tabela_perguntas = tabela_perguntas.sort_values(by='quantidade', ascending=False)

        # Porcentagem
        tabela_perguntas['porcentagem'] = (tabela_perguntas['quantidade'] / total_reprovacoes * 100).round(2).astype(str) + '%'

        # Linha total
        total_row = pd.DataFrame({
            'pergunta': ['Total'],
            'subgrupo': [''],
            'quantidade': [total_reprovacoes],
            'porcentagem': ['100%']
        })
        tabela_perguntas = pd.concat([tabela_perguntas, total_row], ignore_index=True)

        # Plotly Table
        tabela_plotly = go.Figure(go.Table(
            columnwidth=[300, 200, 150, 150],
            header=dict(
                values=['<b>Pergunta</b>', '<b>Subgrupo</b>', '<b>Quantidade de Reprovações</b>', '<b>Porcentagem</b>'],
                fill_color='#f0f0f0',
                font=dict(color='black', size=18),
                align='center',
                height=40
            ),
            cells=dict(
                values=[
                    tabela_perguntas['pergunta'],
                    tabela_perguntas['subgrupo'],
                    tabela_perguntas['quantidade'],
                    tabela_perguntas['porcentagem']
                ],
                font=dict(color='black', size=16),
                align='left',
                height=35
            )
        ))

        # Aumentar o espaço vertical no layout
        tabela_plotly.update_layout(
            height=600  # Tabela maior
        )

        st.plotly_chart(tabela_plotly, use_container_width=True)

        # Botão para baixar Excel
        if not tabela_perguntas.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                tabela_perguntas.to_excel(writer, index=False, sheet_name='Nao_Conformidades')
            output.seek(0)

            st.download_button(
                label="📥 Baixar tabela em Excel",
                data=output,
                file_name="nao_conformidades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum dado disponível para download.")


        #--------------------------------------- Reprovações por Tipo de Equipes --------------------------------------------#  
        
    with REPROVACAO_TIPO_EQUIPE:
            
        def classificar_equipes(df):
            df['tipo_equipe'] = df['num_operacional'].astype(str).apply(
                lambda x: 'Equipe Leve' if x.startswith('9')
                else 'Equipe Pesada' if x.startswith('8')
                else 'Equipe de Linha Viva' if x.startswith('7')
                else 'Equipe de Motocicleta' if x.startswith('4')
                else 'Outros'
            )
            return df

        df_filtrado = classificar_equipes(df_filtrado)
        df_turnos = classificar_equipes(df_turnos)
        tipos_equipe = ['Equipe Leve', 'Equipe Pesada', 'Equipe de Linha Viva', 'Equipe de Motocicleta']

        color_map = {'Sem Reprovação': '#2ca02c', 'Com Reprovações': '#d62728'}

        # ------------------- COLUNAS ------------------- #
        col1, col2, col3, col4, col5 = st.columns(5)

        # ================== 🌟 SUNBURST GERAL ================== #
        df_sunburst_geral = df_filtrado.copy()
        if not df_sunburst_geral.empty:
            df_sunburst_geral['status'] = df_sunburst_geral['num_operacional'].apply(
                lambda x: 'Com Reprovações' if x in df_respostas_filtradas['num_operacional'].unique() else 'Sem Reprovação'
            )
            df_sunburst_geral['tamanho_fatia'] = 1

            fig_sunburst_geral = px.sunburst(
                df_sunburst_geral,
                path=['status', 'prefixo'],
                values='tamanho_fatia',
                title='Pontuações - Geral',
                color='status',
                color_discrete_map=color_map
            )
            fig_sunburst_geral.update_traces(hoverinfo='none')
            fig_sunburst_geral.update_layout(template="plotly_white", hovermode=False)

            with col1:
                st.plotly_chart(fig_sunburst_geral, use_container_width=True)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_sunburst_geral.to_excel(writer, index=False, sheet_name='Geral')
                st.download_button("📥 Dados Geral (Excel)", output.getvalue(),
                                file_name="dados_sunburst_geral.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("Nenhum dado disponível para o Sunburst Geral.")

        # ================== 🌟 SUNBURST POR TIPO ================== #
        for i, tipo in enumerate(tipos_equipe):
            df_tipo_filtrado = df_filtrado[df_filtrado['tipo_equipe'] == tipo]
            equipes_com_reprovacao = df_respostas_filtradas['num_operacional'].unique() if not df_respostas_filtradas.empty else []

            if not df_tipo_filtrado.empty:
                df_sunburst_tipo = df_tipo_filtrado.copy()
                df_sunburst_tipo['status'] = df_sunburst_tipo['num_operacional'].apply(
                    lambda x: 'Com Reprovações' if x in equipes_com_reprovacao else 'Sem Reprovação'
                )
                df_sunburst_tipo['tamanho_fatia'] = 1

                fig_sunburst_tipo = px.sunburst(
                    df_sunburst_tipo,
                    path=['status', 'prefixo'],
                    values='tamanho_fatia',
                    title=f'Pontuação - {tipo}',
                    color='status',
                    color_discrete_map=color_map
                )
                fig_sunburst_tipo.update_traces(hoverinfo='none')
                fig_sunburst_tipo.update_layout(template="plotly_white", hovermode=False)

                with [col2, col3, col4, col5][i]:
                    st.plotly_chart(fig_sunburst_tipo, use_container_width=True)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_sunburst_tipo.to_excel(writer, index=False, sheet_name=tipo)
                    st.download_button(f"📥 Dados {tipo} (Excel)", output.getvalue(),
                                    file_name=f"dados_sunburst_{tipo}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning(f"Nenhum dado disponível para o Sunburst {tipo}.")

        # ================== 🌟 PIE GERAL ================== #
        equipes_inspecionadas = df_filtrado['num_operacional'].unique()
        total_inspecoes = len(equipes_inspecionadas)
        equipes_com_reprovacoes = df_respostas_filtradas['num_operacional'].nunique() if not df_respostas_filtradas.empty else 0

        if total_inspecoes > 0:
            labels = ['Sem Reprovação', 'Com Reprovações']
            values = [total_inspecoes - equipes_com_reprovacoes, equipes_com_reprovacoes]

            fig = px.pie(
                names=labels,
                values=values,
                title="Taxa de Pontuações - Geral",
                color=labels,
                color_discrete_map=color_map,
                hole=0.4
            )
            fig.update_traces(
                textinfo='percent+value',
                textfont=dict(size=18, color='white'),
                hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}"
            )
            fig.update_layout(
                showlegend=False,
                annotations=[dict(
                    text=f"<b>Equipes</b><br><span style='font-size:20px; color:black'><b>{total_inspecoes}</b></span>",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=20, color='black')
                )],
                template="plotly_white"
            )
            with col1:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para o gráfico de Pontuações Geral.")

        # ================== 🌟 PIE POR TIPO DE EQUIPE ================== #
        for idx, tipo in enumerate(tipos_equipe):
            df_tipo = df_filtrado[df_filtrado['tipo_equipe'] == tipo]
            df_resp_tipo = df_respostas_filtradas[df_respostas_filtradas['num_operacional'].isin(df_tipo['num_operacional'])] \
                if not df_respostas_filtradas.empty else pd.DataFrame(columns=['num_operacional'])

            total = df_tipo['num_operacional'].nunique()
            reprovadas = df_resp_tipo['num_operacional'].nunique()

            if total > 0:
                labels = ['Sem Reprovação', 'Com Reprovações']
                values = [total - reprovadas, reprovadas]

                fig = px.pie(
                    names=labels,
                    values=values,
                    title=f"Taxa de Pontuações - {tipo}",
                    color=labels,
                    color_discrete_map=color_map,
                    hole=0.4
                )
                fig.update_traces(
                    textinfo='percent+value',
                    textfont=dict(size=18, color='white'),
                    hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}"
                )
                fig.update_layout(
                    showlegend=False,
                    annotations=[dict(
                        text=f"<b>Equipes</b><br><span style='font-size:20px; color:black'><b>{total}</b></span>",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=20, color='black')
                    )],
                    template="plotly_white"
                )
                with [col2, col3, col4, col5][idx]:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Nenhum dado disponível para o gráfico de Pontuações - {tipo}.")

        # ================== 🌟 BARRAS REPROVADAS POR PREFIXO ================== #
           




    #--------------------------------------------------------------------------------------------------------------------#
    #----------------------------------------- NC por Tipo de Prefixo ---------------------------------------------------#

        st.markdown(
                        """
                        <div style="text-align: center;">
                        <h4 style="font-size:28px;"><strong>EQUIPES REPROVADAS POR TIPO DE PREFIXO</strong></h4>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        if not df_respostas_filtradas.empty:
                        # Junta respostas com turnos para pegar tipo de prefixo
                        df_reprovadas_prefixo = pd.merge(
                            df_respostas_filtradas[['idtb_turnos', 'num_operacional']].drop_duplicates(),
                            df_turnos[['idtb_turnos', 'descricao_tipo_prefixo']],
                            on='idtb_turnos',
                            how='left'
                        )

                        # Conta equipes únicas reprovadas por prefixo
                        reprovadas_por_prefixo = df_reprovadas_prefixo.groupby('descricao_tipo_prefixo')['num_operacional'].nunique().reset_index(name='quantidade')

                        # Gráfico de barras
                        fig_reprovadas_barra = px.bar(
                            reprovadas_por_prefixo,
                            x='descricao_tipo_prefixo',
                            y='quantidade',
                            text='quantidade',
                            color_discrete_sequence=['#d62728']  # Cor vermelha para reprovação
                        )

                        fig_reprovadas_barra.update_traces(
                            textposition='outside',
                            marker_line_color='black',
                            marker_line_width=1.5,
                            textfont=dict(color='black', size=16)
                        )

                        fig_reprovadas_barra.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                            yaxis_title="",
                            template="plotly_white",
                            font=dict(color='black', size=14),
                            xaxis=dict(tickfont=dict(color='black', size=14)),
                            yaxis=dict(tickfont=dict(color='black', size=14)),
                            hovermode='closest',
                            hoverlabel=dict(bgcolor="white", font_size=14, font_color="black")
                        )

                        st.plotly_chart(fig_reprovadas_barra, use_container_width=True, key=f"grafico_reprovadas_{uuid.uuid1()}")

        else:
                        st.warning("Nenhum dado disponível para equipes reprovadas por prefixo.")     
                


    #-----------------------------------------------------------------------------------------------------------------#
    #-------------------------------Não Conformidade Por Inspetor ----------------------------------------------------#

    with REPROVACAO_INSPETOR:
            
        # --- Dados do Script 2: Instrutores e Blitz ---
        # 1. TÉCNICO DE SEGURANÇA e COORDENADOR DE SEGURANÇA (INSPEÇÃO SESMT)
        df_sesmt = df_filtrado[
            df_filtrado['funcao_geral'].isin([
                "TÉCNICO DE SEGURANÇA DO TRABALHO","TECNICO DE SEGURANÇA DO TRABALHO",
                "COORDENADOR DE SEGURANÇA",
                "TECNICO DE SEGURANÇA DO TRABALHO II"
            ])
        ]

        blitz_por_instrutor_sesmt = df_sesmt.groupby("nome_inspetor").agg(
            quantidade_blitz=('idtb_turnos', 'nunique')
        ).reset_index()

        # 2. SUPERVISOR (INSPEÇÃO LIDERANÇA)
        df_lideranca = df_filtrado[df_filtrado['funcao_geral'].isin([
            "SUPERVISOR", "LIDER DE CAMPO", "SUPERVISOR ","COORDENADOR DE OBRAS"
        ])]
        blitz_por_instrutor_lideranca = df_lideranca.groupby("nome_inspetor").agg(
            quantidade_blitz=('idtb_turnos', 'nunique')
        ).reset_index()

        # Reprovações por Instrutor
        reprovacoes_por_instrutor_sesmt = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(df_sesmt['nome_inspetor'])
        ].groupby('nome_inspetor').size().reset_index(name='quantidade_reprovacoes')

        reprovacoes_por_instrutor_lideranca = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(df_lideranca['nome_inspetor'])
        ].groupby('nome_inspetor').size().reset_index(name='quantidade_reprovacoes')

        # Combinar inspeções com reprovações
        dados_sesmt = blitz_por_instrutor_sesmt.merge(
            reprovacoes_por_instrutor_sesmt, on='nome_inspetor', how='left'
        ).fillna(0)

        dados_lideranca = blitz_por_instrutor_lideranca.merge(
            reprovacoes_por_instrutor_lideranca, on='nome_inspetor', how='left'
        ).fillna(0)

    # --- Exibição dos gráficos lado a lado ---

        col1, col2 = st.columns(2)

        # SESMT
        with col1:
            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong> INSPEÇÕES X PONTUAÇÕES - SESMT</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            if not dados_sesmt.empty:
                fig_sesmt = px.bar(
                    dados_sesmt,
                    x='nome_inspetor',
                    y=['quantidade_blitz', 'quantidade_reprovacoes'],
                    barmode='group',
                    labels={'nome_inspetor': 'Instrutor', 'value': 'Quantidade'},
                    text_auto=True
                )

                # Renomear e aplicar cores
                fig_sesmt.data[0].name = 'Inspeções Realizadas'
                fig_sesmt.data[0].marker.color = '#1f77b4'
                fig_sesmt.data[1].name = 'Reprovações'
                fig_sesmt.data[1].marker.color = '#d62728'

                # Aumentar fonte dos textos nas barras
                fig_sesmt.update_traces(textfont=dict(size=16, color='black'))

                # Atualizar layout para deixar tudo preto e maior
                fig_sesmt.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                    xaxis_title="",
                    yaxis_title="",
                    showlegend=True,
                    legend_title="",
                    template="plotly_white",
                    font=dict(size=14, color='black'),
                    legend=dict(font=dict(size=16, color='black')),
                    xaxis=dict(tickfont=dict(size=14, color='black')),
                    yaxis=dict(tickfont=dict(size=14, color='black'))
                )

                st.plotly_chart(fig_sesmt, use_container_width=True)
            else:
                st.warning("Nenhum dado disponível para SESMT.")


        # Liderança
        with col2:

            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>INSPEÇÕES X PONTUAÇÕES - LIDERANÇA</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            if not dados_lideranca.empty:
                fig_lideranca = px.bar(
                    dados_lideranca,
                    x='nome_inspetor',
                    y=['quantidade_blitz', 'quantidade_reprovacoes'],
                    barmode='group',
                    labels={'nome_inspetor': 'Instrutor', 'value': 'Quantidade'},
                    text_auto=True
                )

                # Ajustar nomes e cores das barras
                fig_lideranca.data[0].name = 'Inspeções Realizadas'
                fig_lideranca.data[0].marker.color = '#1f77b4'
                fig_lideranca.data[1].name = 'Reprovações'
                fig_lideranca.data[1].marker.color = '#d62728'

                # Aumentar o tamanho dos textos nas barras e deixar preto
                fig_lideranca.update_traces(textfont=dict(size=16, color='black'))

                # Layout com legenda maior e textos em preto
                fig_lideranca.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                    xaxis_title="",
                    yaxis_title="",
                    showlegend=True,
                    legend_title="",
                    template="plotly_white",
                    font=dict(size=14, color='black'),  # texto geral preto
                    legend=dict(font=dict(size=16, color='black')),  # legenda maior
                    xaxis=dict(tickfont=dict(size=14, color='black')),  # eixo X
                    yaxis=dict(tickfont=dict(size=14, color='black'))   # eixo Y
                )

                st.plotly_chart(fig_lideranca, use_container_width=True)
            else:
                st.warning("Nenhum dado disponível para Supervisão.")


    #----------------------------------------Não Conformidade Por Equipe -----------------------------------#

        col1, col2 = st.columns(2)
        
        with col1:
            # --- Comparação Geral: Total de Inspeções x Total de Reprovações ---
            # (Mantido igual, sem ajustes necessários nessa parte)

            # --- Gráfico de Barras: Inspeções x Reprovações por Equipe ---
            # --- Gráfico de Barras: Inspeções x Reprovações por Equipe ---
            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>INSPEÇÕES X PERGUNTAS PONTUADAS - EQUIPES</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            # 1. Agrupar dados por equipe (como no original)
            inspecoes_por_equipe = df_filtrado.groupby('num_operacional').agg(
                total_inspecoes=('idtb_turnos', 'nunique')
            ).reset_index()

            reprovacoes_por_equipe = df_respostas_filtradas.groupby('num_operacional').agg(
                total_reprovacoes=('Key', 'count')
            ).reset_index()

            # 2. Mesclar os dados calculados
            dados_agrupados = pd.merge(inspecoes_por_equipe, reprovacoes_por_equipe, on='num_operacional', how='outer').fillna(0)

            # 3. <<< NOVA LÓGICA: Criar mapa e adicionar o 'prefixo'
            #    Cria um mapa de 'num_operacional' para 'prefixo' a partir do df principal
            mapa_prefixo = df_filtrado[['num_operacional', 'prefixo']].drop_duplicates()
            #    Junta o prefixo aos dados agrupados
            dados_equipes = pd.merge(dados_agrupados, mapa_prefixo, on='num_operacional', how='left')


            # Formatação dos tipos de dados (sem alterações)
            dados_equipes['total_inspecoes'] = dados_equipes['total_inspecoes'].astype(int)
            dados_equipes['total_reprovacoes'] = dados_equipes['total_reprovacoes'].astype(int)
            dados_equipes['num_operacional'] = dados_equipes['num_operacional'].astype(str)

            # Criando o gráfico de barras agrupadas
            fig = go.Figure()

            # Barras de inspeções
            fig.add_trace(go.Bar(
                x=dados_equipes['prefixo'],  # <<< Eixo X agora usa 'prefixo'
                y=dados_equipes['total_inspecoes'],
                name='Inspeções',
                marker_color='#1f77b4',
                text=dados_equipes['total_inspecoes'],
                textposition='outside',
                textfont=dict(size=16, color='black')
            ))

            # Barras de reprovações
            fig.add_trace(go.Bar(
                x=dados_equipes['prefixo'],  # <<< Eixo X agora usa 'prefixo'
                y=dados_equipes['total_reprovacoes'],
                name='Reprovações',
                marker_color='#d62728',
                text=dados_equipes['total_reprovacoes'],
                textposition='outside',
                textfont=dict(size=16, color='black')
            ))

            # Layout (sem alterações)
            fig.update_layout(height=550,
                barmode='group',
                xaxis_title="",
                yaxis_title="",
                title="",
                template="plotly_white",
                hovermode='x unified',
                legend_title_text='',
                legend=dict(font=dict(size=16, color='black')),
                xaxis=dict(type='category', tickfont=dict(size=14, color='black')),
                yaxis=dict(tickfont=dict(size=14, color='black')),
                font=dict(size=14, color='black')
            )

            # Exibir gráfico
            st.plotly_chart(fig, use_container_width=True)

    #-------------------------------------------------------------------------------------------------------------#
    #---------------------------------------- Reprovação por Equipe Distintas ------------------------------------#

        with col2:
        

            # 🧮 Agrupamento de totais
            total_sesmt = dados_sesmt['quantidade_blitz'].sum()
            total_lideranca = dados_lideranca['quantidade_blitz'].sum()
            total_reprovacoes = df_respostas_filtradas['Key'].nunique()

            dados_comparacao = pd.DataFrame({
                'Categoria': ['Total de Inspeções', 'Total de Reprovações'],
                'Quantidade': [total_sesmt + total_lideranca, total_reprovacoes]
            })

            # 🏷️ Título do gráfico
            with col2:
    # 🧮 Agrupamento de totais (esta parte não precisa de alteração)
    # ... (código de totais mantido) ...

                # 🏷️ Título do gráfico
                st.markdown("""
                    <div style="text-align: center;">
                        <h4 style="font-size:28px;"><strong>INSPEÇÕES X PONTUAÇÕES - EQUIPES</strong></h4>
                    </div>
                """, unsafe_allow_html=True)

                # 1. 🔍 Agrupamentos (como no original)
                inspecoes_por_equipe = df_filtrado.groupby('num_operacional').agg(
                    total_inspecoes=('idtb_turnos', 'nunique')
                ).reset_index()

                reprovacoes_por_equipe = df_respostas_filtradas[['num_operacional', 'idtb_turnos']].drop_duplicates()
                reprovacoes_por_equipe = reprovacoes_por_equipe.groupby('num_operacional').agg(
                    total_reprovacoes=('idtb_turnos', 'nunique')
                ).reset_index()

                # 2. 🔄 Merge dos dados calculados
                dados_agrupados = pd.merge(inspecoes_por_equipe, reprovacoes_por_equipe, on='num_operacional', how='outer').fillna(0)

                # 3. <<< NOVA LÓGICA: Criar mapa e adicionar o 'prefixo'
                mapa_prefixo = df_filtrado[['num_operacional', 'prefixo']].drop_duplicates()
                dados_equipes = pd.merge(dados_agrupados, mapa_prefixo, on='num_operacional', how='left')

                # Formatação (sem alterações)
                dados_equipes['total_inspecoes'] = dados_equipes['total_inspecoes'].astype(int)
                dados_equipes['total_reprovacoes'] = dados_equipes['total_reprovacoes'].astype(int)
                dados_equipes['num_operacional'] = dados_equipes['num_operacional'].astype(str)


                # 📊 Construção do gráfico
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=dados_equipes['prefixo'], # <<< Eixo X agora usa 'prefixo'
                    y=dados_equipes['total_inspecoes'],
                    name='Inspeções',
                    marker_color='#1f77b4',
                    text=dados_equipes['total_inspecoes'],
                    textposition='outside',
                    textfont=dict(size=16, color='black')
                ))

                fig.add_trace(go.Bar(
                    x=dados_equipes['prefixo'], # <<< Eixo X agora usa 'prefixo'
                    y=dados_equipes['total_reprovacoes'],
                    name='Reprovações',
                    marker_color='#d62728',
                    text=dados_equipes['total_reprovacoes'],
                    textposition='outside',
                    textfont=dict(size=16, color='black')
                ))

                # 🎨 Layout (sem alterações)
                fig.update_layout(height=550,
                    barmode='group',
                    template='plotly_white',
                    hovermode='x unified',
                    xaxis_title='',
                    yaxis_title='',
                    title='',
                    showlegend=True,
                    legend_title_text='',
                    legend=dict(font=dict(size=16, color='black')),
                    xaxis=dict(type='category', tickfont=dict(size=14, color='black')),
                    yaxis=dict(tickfont=dict(size=14, color='black')),
                    font=dict(size=14, color='black'),
                    margin=dict(t=80)
                )

                # ✅ Exibir gráfico
                st.plotly_chart(fig, use_container_width=True, key=f"grafico_inspecoes_x_pontuacoes_{uuid.uuid4()}")


    # -------------------------------------------------------------------------------------------------------------#
    # ---------------------------------------- Mapa das Inspeções (PyDeck) ----------------------------------------#
    with REPROVACAO_INSPETOR2:
        

        

        # Agrupando por categoria para cada grupo
        nc_sesmt = df_respostas_filtradas[df_respostas_filtradas['nome_inspetor'].isin(df_sesmt['nome_inspetor'])]
        nc_lideranca = df_respostas_filtradas[df_respostas_filtradas['nome_inspetor'].isin(df_lideranca['nome_inspetor'])]

        cat_sesmt = nc_sesmt.groupby('subgrupo')['Key'].count().reset_index(name='quantidade')
        cat_lideranca = nc_lideranca.groupby('subgrupo')['Key'].count().reset_index(name='quantidade')

        cat_sesmt = cat_sesmt.sort_values(by='quantidade', ascending=True)
        cat_lideranca = cat_lideranca.sort_values(by='quantidade', ascending=True)

        col1, col2 = st.columns(2)

        with col1:
            if not cat_sesmt.empty and not cat_lideranca.empty:
                ordem_subgrupos = cat_sesmt['subgrupo'].tolist()
                cat_sesmt['subgrupo'] = pd.Categorical(cat_sesmt['subgrupo'], categories=ordem_subgrupos, ordered=True)
                cat_lideranca['subgrupo'] = pd.Categorical(cat_lideranca['subgrupo'], categories=ordem_subgrupos, ordered=True)

                cat_sesmt = cat_sesmt.sort_values('subgrupo')
                cat_lideranca = cat_lideranca.sort_values('subgrupo')

            # ✅ Obter a ordem comum dos subgrupos, baseada no SESMT (ou outro critério fixo)
            ordem_subgrupos = cat_sesmt['subgrupo'].tolist()

            # ➕ Garantir que o `subgrupo` seja uma categoria ordenada com base na ordem comum
            cat_sesmt['subgrupo'] = pd.Categorical(cat_sesmt['subgrupo'], categories=ordem_subgrupos, ordered=True)
            cat_lideranca['subgrupo'] = pd.Categorical(cat_lideranca['subgrupo'], categories=ordem_subgrupos, ordered=True)

            # ➕ Reordenar os dataframes de acordo com a nova categoria ordenada
            cat_sesmt = cat_sesmt.sort_values('subgrupo')
            cat_lideranca = cat_lideranca.sort_values('subgrupo')

            st.markdown("""
                <div style="text-align: center;">
                <h4 style="font-size:26px;"><strong>PONTUAÇÕES POR CATEGORIA - SESMT</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            if not cat_sesmt.empty:
                fig_cat_sesmt = px.bar(
                    cat_sesmt,
                    x='quantidade',
                    y='subgrupo',
                    orientation='h',
                    text='quantidade'
                )
                fig_cat_sesmt.update_traces(
                    marker_color='gray',
                    textfont=dict(size=22, color='black')
                )
                fig_cat_sesmt.update_layout(
                    height=500,
                    xaxis_title='',
                    yaxis_title='',
                    template='plotly_white',
                    font=dict(size=20, color='black'),
                    showlegend=False,
                    xaxis=dict(tickfont=dict(size=18, color='black')),
                    yaxis=dict(tickfont=dict(size=20, color='black')),
                    margin=dict(l=20, r=20, t=80, b=40)
                )
                st.plotly_chart(fig_cat_sesmt, use_container_width=True)
            else:
                st.info("Nenhuma NC registrada para SESMT.")

        with col2:
            # ✅ Obter a ordem comum dos subgrupos, baseada no SESMT (ou outro critério fixo)
            ordem_subgrupos = cat_sesmt['subgrupo'].tolist()

            # ➕ Garantir que o `subgrupo` seja uma categoria ordenada com base na ordem comum
            cat_sesmt['subgrupo'] = pd.Categorical(cat_sesmt['subgrupo'], categories=ordem_subgrupos, ordered=True)
            cat_lideranca['subgrupo'] = pd.Categorical(cat_lideranca['subgrupo'], categories=ordem_subgrupos, ordered=True)

            # ➕ Reordenar os dataframes de acordo com a nova categoria ordenada
            cat_sesmt = cat_sesmt.sort_values('subgrupo')
            cat_lideranca = cat_lideranca.sort_values('subgrupo')

            st.markdown("""
                <div style="text-align: center;">
                <h4 style="font-size:26px;"><strong>PONTUAÇÕES POR CATEGORIA - SUPERVISÃO</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            if not cat_lideranca.empty:
                fig_cat_lideranca = px.bar(
                    cat_lideranca,
                    x='quantidade',
                    y='subgrupo',
                    orientation='h',
                    text='quantidade'
                )
                fig_cat_lideranca.update_traces(
                    marker_color='gray',
                    textfont=dict(size=22, color='black')
                )
                fig_cat_lideranca.update_layout(
                    height=500,
                    xaxis_title='',
                    yaxis_title='',
                    template='plotly_white',
                    font=dict(size=20, color='black'),
                    showlegend=False,
                    xaxis=dict(tickfont=dict(size=18, color='black')),
                    yaxis=dict(tickfont=dict(size=20, color='black')),
                    margin=dict(l=20, r=20, t=80, b=40)
                )
                st.plotly_chart(fig_cat_lideranca, use_container_width=True)
            else:
                st.info("Nenhuma NC registrada para Supervisão.")

            # Merge tipo de equipe
        df_respostas_filtradas = df_respostas_filtradas.merge(
            df_filtrado[['num_operacional', 'tipo_equipe']].drop_duplicates(),
            on='num_operacional',
            how='left'
        )

        st.markdown("""
            <div style="text-align: center;">
            <h4 style="font-size:26px;"><strong>PONTUAÇÕES POR CATEGORIA - TIPO DE EQUIPES</strong></h4>
            </div>
        """, unsafe_allow_html=True)

        # Agrupar por tipo de equipe + subgrupo
        df_tipo_categoria = df_respostas_filtradas.groupby(['tipo_equipe', 'subgrupo']).size().reset_index(name='quantidade')

        ordem_equipe = ['Equipe Leve', 'Equipe Pesada', 'Equipe de Linha Viva', 'Equipe de Motocicleta']
        df_tipo_categoria['tipo_equipe'] = pd.Categorical(df_tipo_categoria['tipo_equipe'], categories=ordem_equipe, ordered=True)
        df_tipo_categoria = df_tipo_categoria.sort_values(by='tipo_equipe')

        # Cores neutras personalizadas por subgrupo (se quiser mais, posso ampliar)
        cores_neutras = [
            '#A9A9A9',  # dark gray
            '#C0C0C0',  # silver
            '#BDB76B',  # khaki dark
            '#D2B48C',  # tan
            '#8FBC8F',  # dark sea green
            '#B0C4DE',  # light steel blue
            '#D3D3D3',  # light gray
            '#A0522D',  # sienna
        ]

        # Mapear automaticamente cores neutras para subgrupos únicos
        subgrupos_unicos = df_tipo_categoria['subgrupo'].unique()
        cores_subgrupo = {sub: cor for sub, cor in zip(subgrupos_unicos, cores_neutras)}

        fig_cat_tipo = px.bar(
            df_tipo_categoria,
            x='tipo_equipe',
            y='quantidade',
            color='subgrupo',
            text='quantidade',
            barmode='group',
            color_discrete_map=cores_subgrupo,
            category_orders={'tipo_equipe': ordem_equipe}
        )

        fig_cat_tipo.update_layout(
            title='',
            title_font_size=26,
            height=650,
            xaxis_title="",
            yaxis_title="",
            template='plotly_white',
            font=dict(size=16, color='black'),
            legend_title_text='',
            legend=dict(font=dict(size=22, color='black')),
            xaxis=dict(tickfont=dict(size=22, color='black')),
            yaxis=dict(tickfont=dict(size=16, color='black')),
            margin=dict(l=20, r=20, t=80, b=40)
        )
        fig_cat_tipo.update_traces(
            textposition='outside',
            textfont=dict(size=20, color='black')
        )

        st.plotly_chart(fig_cat_tipo, use_container_width=True)


    with RETROVACAO_INSPETOR3:
        
            # ========== Agrupamentos com Reprovação Única por Turno ==========

        # SESMT
        reprovacoes_unicas_sesmt = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(df_sesmt['nome_inspetor'])
        ][['nome_inspetor', 'idtb_turnos']].drop_duplicates()

        reprovacoes_agrupadas_sesmt = reprovacoes_unicas_sesmt.groupby('nome_inspetor').agg(
            total_reprovacoes=('idtb_turnos', 'nunique')
        ).reset_index()

        dados_sesmt = blitz_por_instrutor_sesmt.merge(
            reprovacoes_agrupadas_sesmt, on='nome_inspetor', how='left'
        ).fillna(0)

        # SUPERVISÃO
        reprovacoes_unicas_lideranca = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(df_lideranca['nome_inspetor'])
        ][['nome_inspetor', 'idtb_turnos']].drop_duplicates()

        reprovacoes_agrupadas_lideranca = reprovacoes_unicas_lideranca.groupby('nome_inspetor').agg(
            total_reprovacoes=('idtb_turnos', 'nunique')
        ).reset_index()

        dados_lideranca = blitz_por_instrutor_lideranca.merge(
            reprovacoes_agrupadas_lideranca, on='nome_inspetor', how='left'
        ).fillna(0)


        # ========== Gráficos lado a lado ==========

        st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>INSPEÇÕES X PONTUAÇÕES - SESMT</strong></h4>
                </div>
            """, unsafe_allow_html=True)

        if not dados_sesmt.empty:
                fig_sesmt = go.Figure()

                fig_sesmt.add_trace(go.Bar(
                    x=dados_sesmt['nome_inspetor'],
                    y=dados_sesmt['quantidade_blitz'],
                    name='Inspeções',
                    marker_color='#1f77b4',
                    text=dados_sesmt['quantidade_blitz'],
                    textposition='outside',
                    textfont=dict(size=22, color='black')
                ))

                fig_sesmt.add_trace(go.Bar(
                    x=dados_sesmt['nome_inspetor'],
                    y=dados_sesmt['total_reprovacoes'],
                    name='Reprovações',
                    marker_color='#d62728',
                    text=dados_sesmt['total_reprovacoes'],
                    textposition='outside',
                    textfont=dict(size=22, color='black')
                ))

                fig_sesmt.update_layout(
                    height=800,
                    barmode='group',
                    template='plotly_white',
                    legend_title_text='',
                    legend=dict(font=dict(size=22, color='black')),
                    xaxis=dict(tickfont=dict(size=22, color='black')),
                    yaxis=dict(tickfont=dict(size=22, color='black')),
                    font=dict(size=22, color='black'),
                    margin=dict(t=90)
                )

                st.plotly_chart(fig_sesmt, use_container_width=True)
        else:
                st.warning("Nenhum dado disponível para SESMT.")
                


    # --- LIDERANÇA ---
    
        st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:28px;"><strong>INSPEÇÕES X PONTUAÇÕES - LIDERANÇA</strong></h4>
                </div>
            """, unsafe_allow_html=True)

        if not dados_lideranca.empty:
                fig_lideranca = go.Figure()

                fig_lideranca.add_trace(go.Bar(
                    x=dados_lideranca['nome_inspetor'],
                    y=dados_lideranca['quantidade_blitz'],
                    name='Inspeções',
                    marker_color='#1f77b4',
                    text=dados_lideranca['quantidade_blitz'],
                    textposition='outside',
                    textfont=dict(size=16, color='black')
                ))

                fig_lideranca.add_trace(go.Bar(
                    x=dados_lideranca['nome_inspetor'],
                    y=dados_lideranca['total_reprovacoes'],
                    name='Reprovações',
                    marker_color='#d62728',
                    text=dados_lideranca['total_reprovacoes'],
                    textposition='outside',
                    textfont=dict(size=22, color='black'),
                    cliponaxis=False
                ))

                fig_lideranca.update_layout(
                    height=800,
                    barmode='group',
                    template='plotly_white',
                    legend_title_text='',
                    legend=dict(font=dict(size=22, color='black')),
                    xaxis=dict(tickfont=dict(size=22, color='black')),
                    yaxis=dict(tickfont=dict(size=22, color='black')),
                    font=dict(size=22, color='black'),
                    margin=dict(t=90)
                )

                st.plotly_chart(fig_lideranca, use_container_width=True)
        else:
                st.warning("Nenhum dado disponível para Supervisão.")
        

    #teste 2 
        

    with ICIT_INSPETOR:
        
        
        

        st.markdown("""
            <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES X PONTUAÇÕES GERAL ICIT</strong></h4>
            </div>
        """, unsafe_allow_html=True)

        # Supondo que df_sem_pessoas e df_respostas_filtradas já estejam carregados antes deste trecho
        # Exemplo para evitar erro, você deve carregar seus dados reais
        # df_sem_pessoas = pd.read_csv("seu_arquivo_sem_pessoas.csv")
        # df_respostas_filtradas = pd.read_csv("seu_arquivo_respostas_filtradas.csv")

        # Evitar warning de SettingWithCopy
        df_sem_pessoas = df_sem_pessoas.copy()

        # Normalizar coluna de função para evitar problemas de espaços e maiúsculas/minúsculas
        df_sem_pessoas['funcao_geral'] = df_sem_pessoas['funcao_geral'].str.strip().str.upper()

        # Definir listas de funções SESMT e Liderança normalizadas
        funcoes_sesmt = [
            "TÉCNICO DE SEGURANÇA DO TRABALHO",
            "TECNICO DE SEGURANÇA DO TRABALHO",
            "COORDENADOR DE SEGURANÇA",
            "TECNICO DE SEGURANÇA DO TRABALHO II"
        ]
        funcoes_sesmt = [f.upper() for f in funcoes_sesmt]

        funcoes_lideranca = [
            "SUPERVISOR",
            "LIDER DE CAMPO",
            "COORDENADOR DE OBRAS",
            "COORDENADOR OPERACIONAL"
        ]
        funcoes_lideranca = [f.upper() for f in funcoes_lideranca]

        # Filtrar SESMT
        df_sesmt_sem_pessoas = df_sem_pessoas[df_sem_pessoas['funcao_geral'].isin(funcoes_sesmt)]

        # Contar inspeções SESMT por instrutor (turnos únicos)
        blitz_por_instrutor_sesmt_sem_pessoas = (
            df_sesmt_sem_pessoas.groupby('nome_inspetor')['idtb_turnos_blitz_contatos']
            .nunique()
            .reset_index()
            .rename(columns={'idtb_turnos_blitz_contatos': 'quantidade_blitz'})
            .sort_values(by='quantidade_blitz', ascending=False)
        )

        # Filtrar Liderança
        df_lideranca_sem_pessoas = df_sem_pessoas[df_sem_pessoas['funcao_geral'].isin(funcoes_lideranca)]

        # Contar inspeções Liderança por instrutor (turnos únicos)
        blitz_por_instrutor_lideranca_sem_pessoas = (
            df_lideranca_sem_pessoas.groupby('nome_inspetor')['idtb_turnos_blitz_contatos']
            .nunique()
            .reset_index()
            .rename(columns={'idtb_turnos_blitz_contatos': 'quantidade_blitz'})
            .sort_values(by='quantidade_blitz', ascending=False)
        )

        # Criar base única de inspeções para o geral (turno + inspetor)
        df_inspecoes_unicas = df_sem_pessoas[['idtb_turnos_blitz_contatos', 'nome_inspetor']].drop_duplicates()

        # Totais de inspeções SESMT e Liderança
        total_sesmt = blitz_por_instrutor_sesmt_sem_pessoas['quantidade_blitz'].sum()
        total_lider = blitz_por_instrutor_lideranca_sem_pessoas['quantidade_blitz'].sum()

        # Total geral de inspeções únicas na base
        total_geral_inspecoes = df_inspecoes_unicas.shape[0]

        # Contar reprovações (NC) SESMT
        com_nc_sesmt = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(blitz_por_instrutor_sesmt_sem_pessoas['nome_inspetor'])
        ][['nome_inspetor', 'idtb_turnos']].drop_duplicates().shape[0]

        # Contar reprovações (NC) Liderança
        com_nc_lider = df_respostas_filtradas[
            df_respostas_filtradas['nome_inspetor'].isin(blitz_por_instrutor_lideranca_sem_pessoas['nome_inspetor'])
        ][['nome_inspetor', 'idtb_turnos']].drop_duplicates().shape[0]

        # Contar reprovações (NC) Geral
        com_nc_geral = df_respostas_filtradas[['nome_inspetor', 'idtb_turnos']].drop_duplicates().shape[0]

        # Calcular inspeções sem NC
        sem_nc_sesmt = total_sesmt - com_nc_sesmt
        sem_nc_lider = total_lider - com_nc_lider
        sem_nc_geral = total_geral_inspecoes - com_nc_geral

        # Função para gráfico de rosca
        def grafico_rosca(titulo, nao_conforme, conforme, total):
            fig = go.Figure(go.Pie(
                labels=['Não Conforme', 'Conforme'],
                values=[nao_conforme, conforme],
                hole=0.6,
                marker=dict(colors=['#d62728', '#1f77b4']),
                textinfo='value+percent',
                textfont=dict(size=24, color='black')
            ))

            fig.update_layout(
                title=dict(text=titulo, font_size=24, x=0.5),
                annotations=[dict(
                    text=f"<b>{total}</b><br>Inspeções",
                    font_size=24,
                    font_color='black',
                    showarrow=False
                )],
                showlegend=True,
                legend=dict(
                    orientation='h',
                    y=-0.1,
                    x=0.5,
                    xanchor='center',
                    font=dict(size=22, color='black')
                ),
                margin=dict(t=60, b=60, l=10, r=10)
            )
            return fig

        # Layout com 3 colunas para os gráficos
        col1, col2, col3 = st.columns(3)

        with col1:
            st.plotly_chart(grafico_rosca("SESMT", com_nc_sesmt, sem_nc_sesmt, total_sesmt), use_container_width=True)

        with col2:
            st.plotly_chart(grafico_rosca("SUPERVISÃO", com_nc_lider, sem_nc_lider, total_lider), use_container_width=True)

        with col3:
            st.plotly_chart(grafico_rosca("GERAL", com_nc_geral, sem_nc_geral, total_geral_inspecoes), use_container_width=True)



    # REPROVAÇÕES POR EQUIPE
        # ✅ Verifica se os dois grupos de inspetores estão selecionados
        categorias_selecionadas = funcao_geral_selecionada  # ou o nome que estiver usando na seleção lateral

        tem_sesmt = any(func in categorias_funcao["SESMT"] for func in categorias_selecionadas)
        tem_supervisao = any(func in categorias_funcao["SUPERVISÃO"] for func in categorias_selecionadas)

        if not (tem_sesmt and tem_supervisao):
            st.warning("⚠️ Este indicador só funciona quando **ambos os tipos de inspetor (SESMT e SUPERVISÃO)** estão selecionados.")
            st.stop()

    # 🧮 INSPEÇÕES ÚNICAS (corrigido com num_operacional incluso)
        df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'funcao_geral', 'num_operacional']].drop_duplicates()

        # ➕ Agrupar SESMT
        df_sesmt = df_inspecoes_unicas[df_inspecoes_unicas['funcao_geral'].isin([
            "TÉCNICO DE SEGURANÇA DO TRABALHO","TECNICO DE SEGURANÇA DO TRABALHO",
            "COORDENADOR DE SEGURANÇA",
            "TECNICO DE SEGURANÇA DO TRABALHO II"
        ])]
        insp_sesmt = df_sesmt[['num_operacional', 'idtb_turnos']].drop_duplicates()

        # ➕ Agrupar LIDERANÇA
        df_lideranca = df_inspecoes_unicas[df_inspecoes_unicas['funcao_geral'].isin([
            "SUPERVISOR", "LIDER DE CAMPO", "SUPERVISOR ", "COORDENADOR DE OBRAS"
        ])]
        insp_lider = df_lideranca[['num_operacional', 'idtb_turnos']].drop_duplicates()

        # ➕ Reprovações por inspetor
        reprovacoes = df_respostas_filtradas[['num_operacional', 'idtb_turnos', 'nome_inspetor']].drop_duplicates()

        # SESMT com NCs
        reprovacoes_sesmt = reprovacoes[reprovacoes['nome_inspetor'].isin(df_sesmt['nome_inspetor'])][['num_operacional', 'idtb_turnos']].drop_duplicates()

        # LIDERANÇA com NCs
        reprovacoes_lider = reprovacoes[reprovacoes['nome_inspetor'].isin(df_lideranca['nome_inspetor'])][['num_operacional', 'idtb_turnos']].drop_duplicates()

        # --- AGRUPAMENTOS POR EQUIPE ---
        equipes_sesmt = set(insp_sesmt['num_operacional'])
        equipes_lider = set(insp_lider['num_operacional'])

        equipes_ambas = equipes_sesmt & equipes_lider
        equipes_so_sesmt = equipes_sesmt - equipes_lider
        equipes_so_lider = equipes_lider - equipes_sesmt

        # --- REPROVAÇÕES POR EQUIPE ---
        equipes_nc_sesmt = set(reprovacoes_sesmt['num_operacional'])
        equipes_nc_lider = set(reprovacoes_lider['num_operacional'])

        # --- CATEGORIZAÇÃO ---
        resultado = []
        for equipe in equipes_ambas:
            nc_sesmt = equipe in equipes_nc_sesmt
            nc_lider = equipe in equipes_nc_lider

            if nc_sesmt and nc_lider:
                categoria = 'NC por ambos'
            elif nc_sesmt:
                categoria = 'NC apenas SESMT'
            elif nc_lider:
                categoria = 'NC apenas Liderança'
            else:
                categoria = 'Sem NC por nenhum'

            resultado.append({'num_operacional': equipe, 'categoria': categoria})

        # ... (código anterior para criar a lista 'resultado') ...

        # ➕ Montar DataFrame
        df_comparacao = pd.DataFrame(resultado)

        # ➕ Contagem por categoria
        # --- CORREÇÃO ADICIONADA AQUI ---
        if not df_comparacao.empty:
            resumo = df_comparacao['categoria'].value_counts().reset_index()
            resumo.columns = ['Categoria', 'Quantidade']
            # O restante do seu código que usa o DataFrame 'resumo' vai aqui.
            # Por exemplo, a criação do gráfico de pizza/rosca.
        else:
            # Adiciona um aviso na tela se não houver dados para comparar
            st.warning("Não foram encontradas equipes inspecionadas por ambos (SESMT e Liderança) para os filtros selecionados.")

        # O restante do seu código para a aba continua aqui...

    

        # 🔄 Preparar DataFrames de inspeções únicas com colunas necessárias
        df_inspecoes_unicas = df_filtrado[['idtb_turnos', 'num_operacional', 'nome_inspetor', 'funcao_geral']].drop_duplicates()

        # 🎯 Filtrar SESMT e Liderança
        df_sesmt = df_inspecoes_unicas[df_inspecoes_unicas['funcao_geral'].isin([
            "TÉCNICO DE SEGURANÇA DO TRABALHO","TECNICO DE SEGURANÇA DO TRABALHO",
            "COORDENADOR DE SEGURANÇA",
            "TECNICO DE SEGURANÇA DO TRABALHO II"
        ])]
        df_lideranca = df_inspecoes_unicas[df_inspecoes_unicas['funcao_geral'].isin([
            "SUPERVISOR", "LIDER DE CAMPO", "SUPERVISOR ", "COORDENADOR DE OBRAS"
        ])]

        # 🔍 Equipes inspecionadas por SESMT e Liderança
        insp_sesmt = df_sesmt[['num_operacional', 'idtb_turnos']].drop_duplicates()
        insp_lideranca = df_lideranca[['num_operacional', 'idtb_turnos']].drop_duplicates()

        # 🔎 Respostas (NCs) por turno para identificar reprovações
        reprovacoes = df_respostas_filtradas[['idtb_turnos', 'num_operacional']].drop_duplicates()

        # 👉 Equipes inspecionadas por ambos
        equipes_sesmt = set(insp_sesmt['num_operacional'].unique())
        equipes_lideranca = set(insp_lideranca['num_operacional'].unique())
        equipes_ambas = equipes_sesmt & equipes_lideranca

        # 🔍 Turnos com NC
        turnos_com_nc = set(reprovacoes['idtb_turnos'])

        # ➕ Adiciona flag se teve NC na inspeção da equipe
        insp_sesmt['com_nc'] = insp_sesmt['idtb_turnos'].isin(turnos_com_nc)
        insp_lideranca['com_nc'] = insp_lideranca['idtb_turnos'].isin(turnos_com_nc)

        # 🔄 Agrupa por equipe
        sesmt_nc_map = insp_sesmt.groupby('num_operacional')['com_nc'].any().to_dict()
        lideranca_nc_map = insp_lideranca.groupby('num_operacional')['com_nc'].any().to_dict()

        # 🎯 Classificação por categoria
        equipes_ambos_com_nc = []
        equipes_ambos_sem_nc = []
        equipes_nc_so_sesmt = []
        equipes_nc_so_lider = []

        for equipe in sorted(equipes_ambas):
            nc_sesmt = sesmt_nc_map.get(equipe, False)
            nc_lider = lideranca_nc_map.get(equipe, False)

            if nc_sesmt and nc_lider:
                equipes_ambos_com_nc.append(equipe)
            elif not nc_sesmt and not nc_lider:
                equipes_ambos_sem_nc.append(equipe)
            elif nc_sesmt and not nc_lider:
                equipes_nc_so_sesmt.append(equipe)
            elif not nc_sesmt and nc_lider:
                equipes_nc_so_lider.append(equipe)

    #------------------------------------------------------------
            
        st.markdown("""<hr>""", unsafe_allow_html=True)


        st.markdown("""
            <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong> INSPEÇÕES - REPROVAÇÕES E NÃO INSPECIONADAS</strong></h4>
            </div>
        """, unsafe_allow_html=True)

        # =========================
        # 🔧 Função para gráfico
        # =========================
        def grafico_pizza_inspecao(titulo, reprovadas, aprovadas, nao_inspecionadas, total_turno):
        
            labels = ['Reprovadas', 'Sem Reprovação', 'Não Inspecionadas']
            values = [reprovadas, aprovadas, nao_inspecionadas]

            total = sum(values)
            custom_text = [f'{val} ({val/total:.1%})' for val in values]

            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.65,
                marker=dict(colors=['#d62728', '#2ca02c', "#cccc35"]),
                text=custom_text,
                textinfo='text',
                textposition='outside',
                textfont=dict(size=20, color='black'),
                hoverinfo='label+percent+value',
            showlegend=True,
            domain=dict(x=[0, 1], y=[0, 1])  # ❗ ocupa toda a área disponível
        ))

            fig.update_layout(
                title=dict(text=f"<b>{titulo}</b>", font_size=22, x=0.5),
                annotations=[dict(
                    text=f"<b>{total_turno}</b><br>Equipes<br>",
                    x=0.5,
                    y=0.5,
                    font_size=20,
                    font=dict(color='black'),  # Cor preta no centro
                    showarrow=False
                )],
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.4,          # Descer a legenda mais para baixo
                    xanchor="center",
                    x=0.5,
                    font=dict(size=20, color='black'),
                    borderwidth=1,   # Borda fina para melhor visualização
                    bordercolor='LightGray',
                    itemclick=False,
                    itemdoubleclick=False,
                    bgcolor='rgba(0,0,0,0)'  # Fundo transparente
                ),
                margin=dict(t=80, b=150, l=20, r=20),  # Aumentar margem inferior para a legenda
                showlegend=True,
                template='plotly_white'
            )

            return fig


        # =========================
        # 📊 Bases de dados
        # =========================
        # Substitua abaixo com seus próprios DataFrames e dicionários
        equipes_total_turno = sorted(df_turnos['num_operacional'].dropna().astype(str).unique())

        eq_insp_sesmt = sorted(insp_sesmt['num_operacional'].dropna().astype(str).unique())
        eq_nc_sesmt = sorted([eq for eq, nc in sesmt_nc_map.items() if nc])
        eq_sem_nc_sesmt = sorted([eq for eq, nc in sesmt_nc_map.items() if not nc])
        eq_nao_insp_sesmt = sorted(list(set(equipes_total_turno) - set(eq_insp_sesmt)))

        eq_insp_lider = sorted(insp_lideranca['num_operacional'].dropna().astype(str).unique())
        eq_nc_lider = sorted([eq for eq, nc in lideranca_nc_map.items() if nc])
        eq_sem_nc_lider = sorted([eq for eq, nc in lideranca_nc_map.items() if not nc])
        eq_nao_insp_lider = sorted(list(set(equipes_total_turno) - set(eq_insp_lider)))

        

        # =========================
        # 📊 Layout com 3 colunas
        # =========================
        col1, col2, col3 = st.columns(3)

        with col1:
            fig_sesmt = grafico_pizza_inspecao(
                titulo="SESMT",
                reprovadas=len(eq_nc_sesmt),
                aprovadas=len(eq_sem_nc_sesmt),
                nao_inspecionadas=len(eq_nao_insp_sesmt),
                total_turno=len(equipes_total_turno)
            )
            st.plotly_chart(fig_sesmt, use_container_width=True)

        with col2:
            fig_lider = grafico_pizza_inspecao(
                titulo="SUPERVISÃO",
                reprovadas=len(eq_nc_lider),
                aprovadas=len(eq_sem_nc_lider),
                nao_inspecionadas=len(eq_nao_insp_lider),
                total_turno=len(equipes_total_turno)
            )
            st.plotly_chart(fig_lider, use_container_width=True)

        with col3:
            # Corrigir lógica apenas para a coluna GERAL

            

            # Construir os conjuntos normalizados
            eq_nc_sesmt = set(str(eq).strip() for eq, nc in sesmt_nc_map.items() if nc)
            eq_nc_lider = set(str(eq).strip() for eq, nc in lideranca_nc_map.items() if nc)

            # Ambas reprovaram
            eq_nc_ambas = eq_nc_sesmt & eq_nc_lider

            # Apenas SESMT e apenas Liderança
            eq_nc_apenas_sesmt = eq_nc_sesmt - eq_nc_ambas
            eq_nc_apenas_lider = eq_nc_lider - eq_nc_ambas

            # Reprovação geral correta
            eq_nc_geral = eq_nc_apenas_sesmt | eq_nc_apenas_lider | eq_nc_ambas

            # Inspecionadas no geral
            eq_insp_sesmt = set(insp_sesmt['num_operacional'].dropna().astype(str).str.strip())
            eq_insp_lider = set(insp_lideranca['num_operacional'].dropna().astype(str).str.strip())
            eq_insp_geral = eq_insp_sesmt | eq_insp_lider

            # Sem reprovação
            eq_sem_nc_geral = eq_insp_geral - eq_nc_geral

            # Não inspecionadas
            equipes_total_turno = set(df_turnos['num_operacional'].dropna().astype(str).str.strip())
            eq_nao_insp_geral = equipes_total_turno - eq_insp_geral

            # Plotar
            fig_geral = grafico_pizza_inspecao(
                titulo="GERAL",
                reprovadas=len(eq_nc_geral),
                aprovadas=len(eq_sem_nc_geral),
                nao_inspecionadas=len(eq_nao_insp_geral),
                total_turno=len(equipes_total_turno)
            )
            st.plotly_chart(fig_geral, use_container_width=True)







    
    
    
    
    #----------------------------------------------------------------  
        # TESTE TABELA
        # --- TABELA DETALHADA POR CATEGORIA ---
        
        # =========================
        # Título da seção
        # =========================
        #----------------------------------------------------------------
        #----------------------------------------------------------------
        # TESTE TABELA
        # --- TABELA DETALHADA POR CATEGORIA ---

        # =========================
        # Título da seção
        # =========================
        st.markdown("""
            <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong> DETALHAMENTO DAS EQUIPES POR CATEGORIA </strong></h4>
            </div>
        """, unsafe_allow_html=True)


        # =========================
        # PASSO 1: Criar o mapa de tradução
        # =========================
        # Garante que não haja valores nulos e converte para string para segurança
        df_mapa = df_filtrado[['num_operacional', 'prefixo']].dropna().copy()
        df_mapa['num_operacional'] = df_mapa['num_operacional'].astype(str)
        df_mapa['prefixo'] = df_mapa['prefixo'].astype(str)

        # Cria o dicionário final
        # <<< LINHA CORRIGIDA (usa df_turnos) >>>
        mapa_prefixo = df_turnos.drop_duplicates(subset=['num_operacional']).set_index('num_operacional')['prefixo'].to_dict()


        # =========================
        # PASSO 2: Cálculos baseados em num_operacional (sem alterações)
        # =========================
        # Toda a sua lógica de cálculo para obter as listas 'eq_...' permanece aqui.
        # Colei novamente para garantir que nada seja perdido.

        # Normalização completa das chaves
        sesmt_nc_map = {str(k).strip(): v for k, v in sesmt_nc_map.items() if pd.notna(k)}
        lideranca_nc_map = {str(k).strip(): v for k, v in lideranca_nc_map.items() if pd.notna(k)}

        eq_insp_sesmt = sorted(insp_sesmt['num_operacional'].dropna().astype(str).str.strip().unique())
        eq_insp_lider = sorted(insp_lideranca['num_operacional'].dropna().astype(str).str.strip().unique())

        eq_nc_sesmt = sorted([eq for eq, nc in sesmt_nc_map.items() if nc])
        eq_nc_lider = sorted([eq for eq, nc in lideranca_nc_map.items() if nc])
        eq_sem_nc_sesmt = sorted([eq for eq, nc in sesmt_nc_map.items() if not nc])
        eq_sem_nc_lider = sorted([eq for eq, nc in lideranca_nc_map.items() if not nc])
        eq_nc_comum_geral = sorted(list(set(eq_nc_sesmt) & set(eq_nc_lider)))
        equipes_total_turno = sorted(df_turnos['num_operacional'].dropna().astype(str).str.strip().unique())
        eq_nao_insp_sesmt = sorted(list(set(equipes_total_turno) - set(eq_insp_sesmt)))
        eq_nao_insp_lider = sorted(list(set(equipes_total_turno) - set(eq_insp_lider)))
        equipes_ambos_sem_inspecao = sorted(list(set(eq_nao_insp_sesmt) & set(eq_nao_insp_lider)))
        eq_nc_geral = sorted(set(eq_nc_sesmt) | set(eq_nc_lider))
        eq_insp_geral = sorted(set(eq_insp_sesmt) | set(eq_insp_lider))
        eq_sem_nc_geral = sorted(set(eq_insp_geral) - set(eq_nc_geral))
        eq_nao_insp_geral = sorted(set(equipes_total_turno) - set(eq_insp_geral))


        # =========================
        # PASSO 3: Bloco de Diagnóstico (NOVO!)
        # =========================
        # Esta seção irá verificar quais equipes estão sem prefixo e te avisar.

        # 1. Juntar todos os num_operacional únicos que você usa nos cálculos
        todos_num_op_usados = set(map(str, eq_insp_sesmt)) | \
                            set(map(str, eq_insp_lider)) | \
                            set(map(str, eq_nc_sesmt)) | \
                            set(map(str, eq_nc_lider)) | \
                            set(map(str, equipes_ambos_sem_inspecao)) | \
                            set(map(str, equipes_total_turno))

        # 2. Pegar todas as chaves (num_operacional) do nosso mapa
        num_op_no_mapa = set(mapa_prefixo.keys())

        # 3. Encontrar quais estão faltando no mapa
        num_op_faltando = sorted(list(todos_num_op_usados - num_op_no_mapa))

        #with st.expander("🔍 Verificação de Dados (Clique para expandir)"):
            #if num_op_faltando:
                #st.warning("⚠️ **Atenção:** Os `num_operacional` listados abaixo foram encontrados nos cálculos da tabela, mas não foi encontrado um `prefixo` correspondente para eles. Por isso, eles aparecerão como números na tabela final.")
               #df_faltando = pd.DataFrame(num_op_faltando, columns=["'num_operacional' sem 'prefixo' correspondente"])
               # st.dataframe(df_faltando)
            #else:
               # st.success("✅ Ótimo! Todos os `num_operacional` foram mapeados para um `prefixo` com sucesso!")

          #  st.info("Abaixo, um exemplo do mapeamento que foi criado (`num_operacional` -> `prefixo`):")
           # st.json(dict(list(mapa_prefixo.items())[:10]))


        # =========================
        # PASSO 4: Tradução e montagem da tabela (usando o mapa)
        # =========================

        # Função para traduzir uma lista de num_operacional para prefixo
        def traduzir_para_prefixo(lista_num_op, mapa):
            # Usa .get(num, num) que retorna o próprio número se ele não for encontrado no mapa
            return sorted([mapa.get(str(num), str(num)) for num in lista_num_op])

        # Funções auxiliares para formatação
        def resumir_com_tooltip(lista, limite=15):
            lista_str = sorted(map(str, lista))
            curta = ', '.join(lista_str[:limite])
            if len(lista_str) > limite:
                curta += f", ... (+{len(lista_str) - limite})"
            tooltip = ', '.join(lista_str)
            return f'<span title="{tooltip}">{curta}</span>'

        def formatar_lista_completa(lista):
            return ', '.join(sorted(map(str, lista)))

        def render_tabela_html(df):
            # (código da função render_tabela_html mantido igual)
            html = "<table style='border-collapse: collapse; width: 100%; text-align: center;'>"
            html += "<thead><tr>"
            for col in df.columns:
                html += f"<th style='border: 1px solid #ddd; padding: 8px;'>{col}</th>"
            html += "</tr></thead><tbody>"
            for _, row in df.iterrows():
                html += "<tr>"
                for cell in row:
                    html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{cell}</td>"
                html += "</tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)


        # Traduz TODAS as listas que serão exibidas
        prefixo_insp_sesmt = traduzir_para_prefixo(eq_insp_sesmt, mapa_prefixo)
        prefixo_insp_lider = traduzir_para_prefixo(eq_insp_lider, mapa_prefixo)
        prefixo_nc_sesmt = traduzir_para_prefixo(eq_nc_sesmt, mapa_prefixo)
        prefixo_nc_lider = traduzir_para_prefixo(eq_nc_lider, mapa_prefixo)
        prefixo_nc_comum = traduzir_para_prefixo(eq_nc_comum_geral, mapa_prefixo)
        prefixo_sem_nc_sesmt = traduzir_para_prefixo(eq_sem_nc_sesmt, mapa_prefixo)
        prefixo_sem_nc_lider = traduzir_para_prefixo(eq_sem_nc_lider, mapa_prefixo)
        prefixo_nao_insp_sesmt = traduzir_para_prefixo(eq_nao_insp_sesmt, mapa_prefixo)
        prefixo_nao_insp_lider = traduzir_para_prefixo(eq_nao_insp_lider, mapa_prefixo)
        prefixo_ambos_sem_inspecao = traduzir_para_prefixo(equipes_ambos_sem_inspecao, mapa_prefixo)
        prefixo_insp_geral = traduzir_para_prefixo(eq_insp_geral, mapa_prefixo)
        prefixo_nc_geral = traduzir_para_prefixo(eq_nc_geral, mapa_prefixo)
        prefixo_sem_nc_geral = traduzir_para_prefixo(eq_sem_nc_geral, mapa_prefixo)
        prefixo_nao_insp_geral = traduzir_para_prefixo(eq_nao_insp_geral, mapa_prefixo)

        # Monta o DataFrame para a tabela HTML
        # (A lógica aqui está correta, apenas se certifica que está usando as listas 'prefixo_...')
        df_equipes = pd.DataFrame({
            "Grupo": ["SESMT", "LIDERANÇA"],
            "EQUIPES (n)": [len(prefixo_insp_sesmt), len(prefixo_insp_lider)],
            "Equipes Inspecionadas": [resumir_com_tooltip(prefixo_insp_sesmt), resumir_com_tooltip(prefixo_insp_lider)],
            "REPROVAÇÕES (n)": [len(prefixo_nc_sesmt), len(prefixo_nc_lider)],
            "Equipes Reprovadas": [resumir_com_tooltip(prefixo_nc_sesmt), resumir_com_tooltip(prefixo_nc_lider)],
            "EM COMUM COM NC(n)": [len(prefixo_nc_comum), len(prefixo_nc_comum)],
            "Equipes em Comum NC": [resumir_com_tooltip(prefixo_nc_comum), resumir_com_tooltip(prefixo_nc_comum)],
            "SEM REPROVAÇÕES (n)": [len(prefixo_sem_nc_sesmt), len(prefixo_sem_nc_lider)],
            "Equipes Sem Reprovação": [resumir_com_tooltip(prefixo_sem_nc_sesmt), resumir_com_tooltip(prefixo_sem_nc_lider)],
            "EQUIPES NÃO INSPECIONADAS (n)": [len(prefixo_nao_insp_sesmt), len(prefixo_nao_insp_lider)],
            "Equipes Não Inspecionadas": [resumir_com_tooltip(prefixo_nao_insp_sesmt), resumir_com_tooltip(prefixo_nao_insp_lider)],
            "AMBOS SEM INSPEÇÃO (n)": [len(prefixo_ambos_sem_inspecao)] * 2,
            "Equipes Ambos Sem Inspeção": [resumir_com_tooltip(prefixo_ambos_sem_inspecao)] * 2
        })
        linha_geral = pd.DataFrame({
            # (lógica da linha_geral mantida)
            "Grupo": ["GERAL"], "EQUIPES (n)": [len(prefixo_insp_geral)], "Equipes Inspecionadas": [resumir_com_tooltip(prefixo_insp_geral)], "REPROVAÇÕES (n)": [len(prefixo_nc_geral)], "Equipes Reprovadas": [resumir_com_tooltip(prefixo_nc_geral)], "EM COMUM COM NC(n)": [len(prefixo_nc_comum)], "Equipes em Comum NC": [resumir_com_tooltip(prefixo_nc_comum)], "SEM REPROVAÇÕES (n)": [len(prefixo_sem_nc_geral)], "Equipes Sem Reprovação": [resumir_com_tooltip(prefixo_sem_nc_geral)], "EQUIPES NÃO INSPECIONADAS (n)": [len(prefixo_nao_insp_geral)], "Equipes Não Inspecionadas": [resumir_com_tooltip(prefixo_nao_insp_geral)], "AMBOS SEM INSPEÇÃO (n)": [len(prefixo_ambos_sem_inspecao)], "Equipes Ambos Sem Inspeção": [resumir_com_tooltip(prefixo_ambos_sem_inspecao)]
        })
        df_equipes = pd.concat([df_equipes, linha_geral], ignore_index=True)
        render_tabela_html(df_equipes)

        # =========================
        # PASSO 5: Geração do Excel (usando as mesmas listas traduzidas)
        # =========================
        # (código para gerar o Excel mantido, mas garantindo que usa as listas 'prefixo_...')
        df_para_excel = pd.DataFrame({
            "Grupo": ["SESMT", "LIDERANÇA"], "EQUIPES (n)": [len(prefixo_insp_sesmt), len(prefixo_insp_lider)], "Equipes Inspecionadas": [formatar_lista_completa(prefixo_insp_sesmt), formatar_lista_completa(prefixo_insp_lider)], "REPROVAÇÕES (n)": [len(prefixo_nc_sesmt), len(prefixo_nc_lider)], "Equipes Reprovadas": [formatar_lista_completa(prefixo_nc_sesmt), formatar_lista_completa(prefixo_nc_lider)], "EM COMUM (n)": [len(prefixo_nc_comum), len(prefixo_nc_comum)], "Equipes em Comum Reprov": [formatar_lista_completa(prefixo_nc_comum), formatar_lista_completa(prefixo_nc_comum)], "SEM REPROVAÇÕES (n)": [len(prefixo_sem_nc_sesmt), len(prefixo_sem_nc_lider)], "Equipes Sem Reprovação": [formatar_lista_completa(prefixo_sem_nc_sesmt), formatar_lista_completa(prefixo_sem_nc_lider)], "EQUIPES NÃO INSPECIONADAS (n)": [len(prefixo_nao_insp_sesmt), len(prefixo_nao_insp_lider)], "Equipes Não Inspecionadas": [formatar_lista_completa(prefixo_nao_insp_sesmt), formatar_lista_completa(prefixo_nao_insp_lider)], "AMBOS SEM NC (n)": [len(traduzir_para_prefixo(sorted([eq for eq in (set(eq_insp_sesmt) & set(eq_insp_lider)) if eq in eq_sem_nc_sesmt and eq in eq_sem_nc_lider]), mapa_prefixo))] * 2, "AMBOS SEM INSPEÇÃO (n)": [len(prefixo_ambos_sem_inspecao)] * 2, "Equipes Ambos Sem Inspeção": [formatar_lista_completa(prefixo_ambos_sem_inspecao)] * 2,
        })
        linha_geral_excel = pd.DataFrame({
            "Grupo": ["GERAL"], "EQUIPES (n)": [len(prefixo_insp_geral)], "Equipes Inspecionadas": [formatar_lista_completa(prefixo_insp_geral)], "REPROVAÇÕES (n)": [len(prefixo_nc_geral)], "Equipes Reprovadas": [formatar_lista_completa(prefixo_nc_geral)], "EM COMUM (n)": [len(prefixo_nc_comum)], "Equipes em Comum Reprov": [formatar_lista_completa(prefixo_nc_comum)], "SEM REPROVAÇÕES (n)": [len(prefixo_sem_nc_geral)], "Equipes Sem Reprovação": [formatar_lista_completa(prefixo_sem_nc_geral)], "EQUIPES NÃO INSPECIONADAS (n)": [len(prefixo_nao_insp_geral)], "Equipes Não Inspecionadas": [formatar_lista_completa(prefixo_nao_insp_geral)], "AMBOS SEM NC (n)": [""], "AMBOS SEM INSPEÇÃO (n)": [len(prefixo_ambos_sem_inspecao)], "Equipes Ambos Sem Inspeção": [formatar_lista_completa(prefixo_ambos_sem_inspecao)]
        })
        df_para_excel = pd.concat([df_para_excel, linha_geral_excel], ignore_index=True)

        # Geração do buffer e botão de download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_para_excel.to_excel(writer, index=False, sheet_name='Detalhamento_Equipes')
        buffer.seek(0)
        st.download_button(
            label="📥 Baixar tabela completa em Excel",
            data=buffer,
            file_name='detalhamento_equipes.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# <<< FIM DAS ALTERAÇÕES >>>




    with MAPA:
        
        

        st.markdown("""
            <div style="text-align: center;">
            <h4 style="font-size:28px;"><strong>MAPA REGIONAL DAS INSPEÇÕES</strong></h4>
            </div>
        """, unsafe_allow_html=True)

        # ------------------- FILTROS ------------------- #
        turnos_validos = df_filtrado['idtb_turnos'].unique() if not df_filtrado.empty else []

        # Filtra eventos "INÍCIO DA APR"
        df_eventos_apr = df_eventos[
            (df_eventos['evento'].astype(str).str.strip().str.upper() == "INÍCIO DA APR") &
            (df_eventos['idtb_turnos'].isin(turnos_validos))
        ] if not df_eventos.empty else pd.DataFrame()

        # Junta com dados da blitz, apenas se houver dados
        if not df_eventos_apr.empty and not df_filtrado.empty:
            df_eventos_apr = df_eventos_apr.merge(
                df_filtrado[['idtb_turnos', 'nome_inspetor', 'num_operacional', 'unidade', 'nom_fant']],
                on='idtb_turnos',
                how='left'
            )

            # Remove duplicatas reais
            df_eventos_apr = df_eventos_apr.drop_duplicates(subset=['idtb_turnos', 'nome_inspetor', 'num_operacional'])

            # Limpa coordenadas inválidas
            df_eventos_apr['latitude'] = pd.to_numeric(df_eventos_apr['latitude'], errors='coerce')
            df_eventos_apr['longitude'] = pd.to_numeric(df_eventos_apr['longitude'], errors='coerce')
            df_eventos_apr = df_eventos_apr.dropna(subset=['latitude', 'longitude'])
            df_eventos_apr = df_eventos_apr[(df_eventos_apr['latitude'] != 0) & (df_eventos_apr['longitude'] != 0)]

        # ------------------- MAPA ------------------- #
        def cor_rgb_do_nome(nome):
            h = hashlib.md5(nome.encode()).hexdigest()
            return [int(h[i:i+2], 16) for i in (0, 2, 4)]

        if not df_eventos_apr.empty:
            df_eventos_apr['color'] = df_eventos_apr['nome_inspetor'].fillna("desconhecido").apply(cor_rgb_do_nome)

            # Define view centralizada
            view_state = pdk.ViewState(
                latitude=df_eventos_apr['latitude'].mean(),
                longitude=df_eventos_apr['longitude'].mean(),
                zoom=9,
                pitch=0
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_eventos_apr,
                get_position='[longitude, latitude]',
                get_fill_color='color',
                get_radius=1200,
                pickable=True
            )

            tooltip = {
                "html": "<b>Inspetor:</b> {nome_inspetor} <br/>"
                        "<b>Equipe:</b> {num_operacional} <br/>"
                        "<b>Unidade:</b> {unidade}",
                "style": {"backgroundColor": "rgba(0,0,0,0.7)", "color": "white"}
            }

            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip=tooltip,
                    map_style="mapbox://styles/mapbox/dark-v10"
                ),
                use_container_width=True,
                height=800
            )
        else:
            st.info("Nenhum evento 'INÍCIO DA APR' encontrado para os filtros aplicados.")



    # -------------------------------- EQUIPES INSPECIONADAS POR INSPETOR (2 COLUNAS) --------------------------------- #
    with EQUIPES_INSTRUTOR:
            
        

        


        # 🔷 Categorias de função
        categorias_funcao = {
            "SESMT": [
                "TÉCNICO DE SEGURANÇA DO TRABALHO", "TECNICO DE SEGURANÇA DO TRABALHO",
                "TECNICO DE SEGURANÇA DO TRABALHO II", "COORDENADOR DE SEGURANÇA"
            ],
            "LIDERANÇA": [
                "SUPERVISOR", "LIDER DE CAMPO", "SUPERVISOR ", "COORDENADOR DE OBRAS", "COORDENADOR OPERACIONAL"
            ]
        }

        # 🔠 Padroniza função
        df_filtrado['funcao_geral'] = df_filtrado['funcao_geral'].str.upper().str.strip()

        # 🔎 Filtra apenas inspeções sem pessoa associada
        df_sem_pessoas = df_filtrado[df_filtrado['idtb_pessoas'].isna()]

        # 🔎 Filtra eventos de "INÍCIO DA APR"
        df_eventos_apr = df_eventos[
            (df_eventos['evento'].astype(str).str.strip().str.upper() == "INÍCIO DA APR") &
            (df_eventos['idtb_turnos'].isin(df_sem_pessoas['idtb_turnos']))
        ]

        # Junta com dados do Blitz
        df_eventos_apr = df_eventos_apr.merge(
            df_sem_pessoas[['idtb_turnos', 'nome_inspetor', 'prefixo', 'unidade', 'nom_fant', 'funcao_geral']],
            on='idtb_turnos',
            how='left'
        ).drop_duplicates(subset=['idtb_turnos', 'nome_inspetor', 'prefixo'])

        # 🔹 Garante que a coluna extra exista
        df_eventos_apr['idtb_turnos_blitz_contatos'] = df_eventos_apr['idtb_turnos']

        # 🧩 Divide os grupos
        df_sesmt = df_eventos_apr[df_eventos_apr['funcao_geral'].isin(categorias_funcao["SESMT"])]
        df_lideranca = df_eventos_apr[df_eventos_apr['funcao_geral'].isin(categorias_funcao["LIDERANÇA"])]

        # 📊 Função de exibição
        def render_blocos(df_base, funcoes, titulo, emoji, coluna):
            if df_base.empty:
                with coluna:
                    st.info(f"Nenhuma inspeção disponível para {titulo}.")
                return

            df_base['funcao_geral'] = df_base['funcao_geral'].str.upper().str.strip()
            df_filtrado = df_base[df_base['funcao_geral'].isin(funcoes)]

            if df_filtrado.empty:
                with coluna:
                    st.info(f"Nenhuma inspeção disponível para {titulo}.")
                return

            # Agrupa por inspetor e equipe
            grupo = df_filtrado.groupby(['nome_inspetor', 'prefixo'])['idtb_turnos_blitz_contatos'] \
                .nunique().reset_index(name='quantidade')

            grupo_total = grupo.groupby('nome_inspetor')['quantidade'].sum().reset_index()

            with coluna:
                st.markdown(f"### {emoji} **{titulo}**")

                for _, linha in grupo_total.iterrows():
                    inspetor = linha['nome_inspetor']
                    total = linha['quantidade']
                    st.markdown(f"""
                        <div style="text-align: center; font-weight: bold; font-size: 18px;">
                            👷 {inspetor} – <span style="color:darkblue">{total} inspeções</span>
                        </div>
                    """, unsafe_allow_html=True)

                    equipes = grupo[grupo['nome_inspetor'] == inspetor]
                    linhas = [f"Equipe {row['prefixo']} – **{row['quantidade']}x**" for _, row in equipes.iterrows()]

                    for i in range(0, len(linhas), 3):
                        col1, col2, col3 = st.columns(3)
                        for j, col in enumerate([col1, col2, col3]):
                            if i + j < len(linhas):
                                col.markdown(f"- {linhas[i + j]}")
                    st.markdown("<hr style='border-top: 2px solid #bbb;'>", unsafe_allow_html=True)

        # 📍 Colunas de exibição
        col_sesmt, col_lideranca = st.columns(2)

        # ▶️ Renderiza
        render_blocos(df_eventos_apr, categorias_funcao["SESMT"], "INSPEÇÕES SESMT", "🔵", col_sesmt)
        render_blocos(df_eventos_apr, categorias_funcao["LIDERANÇA"], "INSPEÇÕES LIDERANÇA", "🟠", col_lideranca)

        # 📦 Exportação Excel
        df_export = pd.concat([
            df_sesmt.assign(tipo_inspecao='SESMT'),
            df_lideranca.assign(tipo_inspecao='LIDERANÇA')
        ])

        if not df_export.empty:
            df_export_grouped = df_export.groupby(['tipo_inspecao', 'nome_inspetor', 'prefixo']) \
                .size().reset_index(name='quantidade')

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for grupo in ['SESMT', 'LIDERANÇA']:
                    df_temp = df_export_grouped[df_export_grouped['tipo_inspecao'] == grupo]
                    df_temp[['nome_inspetor', 'prefixo', 'quantidade']].to_excel(
                        writer, sheet_name=grupo, index=False
                    )
            output.seek(0)

            st.download_button(
                label="📥 Baixar Inspeções por Inspetor (Excel)",
                data=output,
                file_name="inspecoes_por_inspetor.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Nenhuma inspeção disponível para exportação.")




    #------------------------------------------------------------------------------------------------------#

    with Horas_das_inspecao:    
        col1,col2 = st.columns(2)
        with col1:


            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES POR HORA DO DIA DO TURNO ABERTO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Usa a contagem correta de inspeções únicas
            df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'data_turno']].drop_duplicates()
            df_inspecoes_unicas['data_turno'] = pd.to_datetime(df_inspecoes_unicas['data_turno'], errors='coerce')
            df_inspecoes_unicas['hora'] = df_inspecoes_unicas['data_turno'].dt.hour

            # Conta quantas inspeções ocorreram por hora
            df_por_hora = df_inspecoes_unicas.groupby('hora').size().reset_index(name='quantidade')
            df_por_hora = df_por_hora.sort_values('hora')

            # Classifica turno por hora
            def classificar_turno(hora):
                if 1 <= hora <= 11:
                    return 'MANHÃ'
                elif 12 <= hora <= 17:
                    return 'TARDE'
                elif 18 <= hora <= 23 or hora == 0:
                    return 'NOITE'

            df_por_hora['turno'] = df_por_hora['hora'].apply(classificar_turno)

            # Coluna para exibição no eixo X
            df_por_hora['hora_str'] = df_por_hora['hora'].astype(str) + ' h'

            # Mapeia cores personalizadas por turno
            cores_turno = {'MANHÃ': '#1f77b4', 'TARDE': '#2ca02c', 'NOITE': '#d62728'}

            fig_horas = px.bar(
            df_por_hora,
            x='hora_str',
            y='quantidade',
            text='quantidade',
            labels={'hora_str': 'Hora do Dia', 'quantidade': 'Qtd. de Inspeções'},
            color='turno',
            color_discrete_map=cores_turno
        )

            fig_horas.update_traces(
                textposition='outside',
                textfont=dict(size=18, color='black')
            )

            fig_horas.update_layout(
                height=550,  # ⬅️ aumenta a altura para evitar corte
                title_font_size=24,
                xaxis_title='',
                title='',
                yaxis_title='',
                legend_title_text='Turno',
                font=dict(size=16),
                xaxis=dict(
                    tickfont=dict(size=16, color='black')
                ),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=14,
                    font_color="black"
                )
            )

            st.plotly_chart(fig_horas, use_container_width=True, key=f"grafico_horas_{uuid.uuid4()}")

        #------------------------------------- Por periodo de horario --------------------------------------------------------------#

        with col2:
        
            

            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES POR TURNO DO DIA</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Usa a contagem correta de inspeções únicas
            df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'data_turno']].drop_duplicates()
            df_inspecoes_unicas['data_turno'] = pd.to_datetime(df_inspecoes_unicas['data_turno'], errors='coerce')
            df_inspecoes_unicas['hora'] = df_inspecoes_unicas['data_turno'].dt.hour

            # Classifica o turno com base na hora
            def classificar_turno(hora):
                if 1 <= hora <= 11:
                    return 'MANHÃ'
                elif 12 <= hora <= 17:
                    return 'TARDE'
                elif 18 <= hora <= 23 or hora == 0:
                    return 'NOITE'

            df_inspecoes_unicas['turno'] = df_inspecoes_unicas['hora'].apply(classificar_turno)

            # Agrupa por turno
            df_turno = df_inspecoes_unicas.groupby('turno').size().reset_index(name='quantidade')
            df_turno = df_turno.sort_values('turno', key=lambda x: x.map({'MANHÃ': 0, 'TARDE': 1, 'NOITE': 2}))

            # Total de inspeções
            total_inspecoes = df_turno['quantidade'].sum()

            # Cria gráfico de rosca com texto preto e cores personalizadas
            fig_pizza_turnos = go.Figure(data=[
                go.Pie(
                    labels=df_turno['turno'],
                    values=df_turno['quantidade'],
                    hole=0.5,
                    textinfo='percent+label+value',
                    textfont=dict(size=20, color='black'),  # Texto preto
                    marker=dict(colors=['#1f77b4', '#2ca02c', '#d62728']),  # Manhã: azul, Tarde: verde, Noite: vermelho
                    insidetextorientation='radial'
                )
            ])

            fig_pizza_turnos.update_layout(height=550,  # ⬅️ aumenta a altura para evitar corte
                title='Distribuição de Inspeções por Turno',
                title_font_size=18,
                annotations=[dict(
                    text=f"<b>{total_inspecoes}<br>Inspeções</b>",
                    x=0.5, y=0.5,
                    font=dict(size=18, color="black"),  # Texto central preto
                    showarrow=False
                )],
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=14,
                    font_color="black"
                )
            )
            

            st.plotly_chart(fig_pizza_turnos, use_container_width=True, key=f"grafico_turnos_{uuid.uuid4()}")


    #-----------------------------teste

        col1,col2 = st.columns(2)

        with col1 :

            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES POR DIA DA SEMANA E TURNO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Base de dados
            df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'data_turno']].drop_duplicates()
            df_inspecoes_unicas['data_turno'] = pd.to_datetime(df_inspecoes_unicas['data_turno'], errors='coerce')
            df_inspecoes_unicas['hora'] = df_inspecoes_unicas['data_turno'].dt.hour
            df_inspecoes_unicas['dia_semana'] = df_inspecoes_unicas['data_turno'].dt.dayofweek

            # Mapeia nome do dia da semana
            dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            df_inspecoes_unicas['dia_semana_nome'] = df_inspecoes_unicas['dia_semana'].map(lambda x: dias_semana[x])

            def classificar_turno(hora):
                if 1 <= hora <= 11:
                    return 'MANHÃ'
                elif 12 <= hora <= 17:
                    return 'TARDE'
                elif 18 <= hora <= 23 or hora == 0:
                    return 'NOITE'

            df_inspecoes_unicas['turno'] = df_inspecoes_unicas['hora'].apply(classificar_turno)

            # Agrupa por dia da semana e turno
            df_turno_dia = df_inspecoes_unicas.groupby(['dia_semana_nome', 'turno']).size().reset_index(name='quantidade')

            # Ordena corretamente os dias da semana
            df_turno_dia['dia_semana_nome'] = pd.Categorical(df_turno_dia['dia_semana_nome'], categories=dias_semana, ordered=True)
            df_turno_dia = df_turno_dia.sort_values(['dia_semana_nome', 'turno'])

            # Define cores dos turnos
            cores_turno = {'MANHÃ': '#1f77b4', 'TARDE': '#2ca02c', 'NOITE': '#d62728'}

            # Cria gráfico de barras empilhadas
            fig = px.bar(
                df_turno_dia,
                x='dia_semana_nome',
                y='quantidade',
                color='turno',
                text='quantidade',
                color_discrete_map=cores_turno,
                labels={'dia_semana_nome': 'Dia da Semana', 'quantidade': 'Qtd. de Inspeções', 'turno': 'Turno'}
            )

            fig.update_traces(textposition='inside')

            # Adiciona totais no topo das barras
            df_totais = df_turno_dia.groupby('dia_semana_nome')['quantidade'].sum().reset_index()
            for i, row in df_totais.iterrows():
                fig.add_annotation(
                    x=row['dia_semana_nome'],
                    y=row['quantidade'] + 1,  # um pouco acima do topo
                    text=f"<b>{int(row['quantidade'])}</b>",
                    showarrow=False,
                    font=dict(size=18, color='black')
                )

            # Atualiza layout
            fig.update_layout(
                barmode='stack',
                title='',
                title_font_size=24,
                xaxis_title='',
                yaxis_title='',
                legend_title_text='Turno',
                font=dict(size=16),
                xaxis=dict(
                    tickfont=dict(size=18, color='black')
                )
                ,
            hoverlabel=dict(
                bgcolor="white",
                font_size=14,
                font_color="black"
            )
        )
            

            st.plotly_chart(fig, use_container_width=True, key=f"grafico_barras_turno_{uuid.uuid4()}")
        
        with col2:


            
            st.markdown(
                """
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>INSPEÇÕES POR SEMANA DO ANO E TURNO</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Base de dados
            df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'data_turno']].drop_duplicates()
            df_inspecoes_unicas['data_turno'] = pd.to_datetime(df_inspecoes_unicas['data_turno'], errors='coerce')
            df_inspecoes_unicas = df_inspecoes_unicas.dropna(subset=['data_turno'])
            df_inspecoes_unicas['hora'] = df_inspecoes_unicas['data_turno'].dt.hour

            # Classifica turno por hora
            def classificar_turno(hora):
                if 1 <= hora <= 11:
                    return 'MANHÃ'
                elif 12 <= hora <= 17:
                    return 'TARDE'
                elif 18 <= hora <= 23 or hora == 0:
                    return 'NOITE'

            df_inspecoes_unicas['turno'] = df_inspecoes_unicas['hora'].apply(classificar_turno)

            # Semana do ano
            df_inspecoes_unicas['semana_ano'] = df_inspecoes_unicas['data_turno'].dt.isocalendar().week
            df_inspecoes_unicas['ano'] = df_inspecoes_unicas['data_turno'].dt.year
            df_inspecoes_unicas['semana_completa'] = 'Semana ' + df_inspecoes_unicas['semana_ano'].astype(str) + ' - ' + df_inspecoes_unicas['ano'].astype(str)

            # Agrupa por semana e turno
            df_semana_turno = df_inspecoes_unicas.groupby(['semana_completa', 'turno']).size().reset_index(name='quantidade')

            # Ordenação correta
            extraido = df_semana_turno['semana_completa'].str.extract(r'Semana (\d+) - (\d{4})')
            df_semana_turno['ordem'] = extraido[1] + '-' + extraido[0].astype(int).astype(str).str.zfill(2)
            df_semana_turno = df_semana_turno.sort_values('ordem')

            # Cores por turno
            cores_turno = {'MANHÃ': '#1f77b4', 'TARDE': '#2ca02c', 'NOITE': '#d62728'}

            # Gráfico
            fig = px.bar(
                df_semana_turno,
                x='semana_completa',
                y='quantidade',
                color='turno',
                text='quantidade',
                color_discrete_map=cores_turno,
                labels={'semana_completa': 'Semana do Ano', 'quantidade': 'Qtd. de Inspeções', 'turno': 'Turno'}
            )

            fig.update_traces(textposition='inside')

            # Total por semana no topo da barra
            df_totais = df_semana_turno.groupby('semana_completa')['quantidade'].sum().reset_index()
            for _, row in df_totais.iterrows():
                fig.add_annotation(
                    x=row['semana_completa'],
                    y=row['quantidade'] + 1,
                    text=f"<b>{int(row['quantidade'])}</b>",
                    showarrow=False,
                    font=dict(size=18, color='black')
                )

            # Layout visual mantido
            fig.update_layout(
                barmode='stack',
                title='',
                title_font_size=24,
                xaxis_title='',
                yaxis_title='',
                legend_title_text='Turno',
                font=dict(size=16),
                xaxis=dict(tickfont=dict(size=16, color='black')),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=14,
                    font_color="black"
                ),
                plot_bgcolor='white',
                bargap=0.15
            )

            st.plotly_chart(fig, use_container_width=True, key=f"grafico_semanal_turno_{uuid.uuid4()}")



        col1,col2 = st.columns(2)

        with col1 :

            

            st.markdown("""
                <div style="text-align: center;">
                <h4 style="font-size:28px;"><strong>CALENDÁRIO DE INSPEÇÕES</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            # Usa a mesma base do gráfico de inspeções por dia da semana
            df_inspecoes_unicas = df_filtrado[['nome_inspetor', 'idtb_turnos', 'data_turno']].drop_duplicates()
            df_inspecoes_unicas['data_turno'] = pd.to_datetime(df_inspecoes_unicas['data_turno'], errors='coerce')

            # Verifica se há dados válidos
            if df_inspecoes_unicas['data_turno'].notna().sum() == 0:
                st.warning("📆 Sem inspeções registradas neste período.")
            else:
                ano = df_inspecoes_unicas['data_turno'].dt.year.max()
                mes = df_inspecoes_unicas[df_inspecoes_unicas['data_turno'].dt.year == ano]['data_turno'].dt.month.max()

                if pd.isna(mes) or pd.isna(ano):
                    st.warning("📆 Sem inspeções registradas neste período.")
                else:
                    # Filtra dados do mês correto
                    df_mes = df_inspecoes_unicas[
                        (df_inspecoes_unicas['data_turno'].dt.year == ano) &
                        (df_inspecoes_unicas['data_turno'].dt.month == mes)
                    ]

                    # Conta inspeções por dia
                    df_mes['dia'] = df_mes['data_turno'].dt.day
                    dias_inspecao = df_mes['dia'].value_counts().to_dict()

                    # Gradiente de cor: normaliza para escalar de 0 a 1
                    max_inspecoes = max(dias_inspecao.values()) if dias_inspecao else 1
                    norm = mcolors.Normalize(vmin=0, vmax=max_inspecoes)
                    cmap = cm.Blues  # Mapa de cor azul

                    # Monta estrutura de calendário
                    cal = calendar.Calendar(firstweekday=0)
                    month_days = cal.monthdayscalendar(int(ano), int(mes))

                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.set_axis_off()

                    table_data = []
                    for week in month_days:
                        row = []
                        for day in week:
                            if day == 0:
                                row.append("")
                            elif day in dias_inspecao:
                                row.append(f"{day}\n{dias_inspecao[day]} inspeções")
                            else:
                                row.append(f"{day}")
                        table_data.append(row)

                    table = ax.table(
                        cellText=table_data,
                        colLabels=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
                        cellLoc='center',
                        loc='center',
                        colLoc='center'
                    )

                    # Estiliza células
                    for (i, j), cell in table.get_celld().items():
                        cell.set_height(0.15)
                        if i == 0:
                            cell.set_text_props(weight='bold', size=12)
                        else:
                            cell.set_text_props(size=10)
                            text = table_data[i-1][j]
                            if "\n" in text:
                                # Extrai número de inspeções
                                num = int(text.split("\n")[1].split()[0])
                                cor = cmap(norm(num))
                                cell.set_facecolor(cor)
                            else:
                                cell.set_facecolor("white")

                    ax.set_title(f"Calendário de Inspeções - {calendar.month_name[int(mes)]} {int(ano)}", fontsize=16, pad=20)
                    st.pyplot(fig)




if __name__ == "__main__":
    app()
