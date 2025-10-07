import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
import os
from io import BytesIO

# Configuração inicial da página


# Funções auxiliares (definidas uma única vez no início)
def ajustar_valores_grafico(total_pessoas, total_inspecionadas):
    if total_inspecionadas > total_pessoas:
        total_inspecionadas = total_pessoas
    total_nao_inspecionadas = total_pessoas - total_inspecionadas
    return total_inspecionadas, total_nao_inspecionadas

def criar_tabela_aggrid(df, titulo, altura=600):
    st.markdown(f"<h3 style='text-align:center'><strong>{titulo}</strong></h3>", unsafe_allow_html=True)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    gb.configure_default_column(groupable=True, sortable=True, filterable=True)
    grid_options = gb.build()
    AgGrid(df, gridOptions=grid_options, height=altura, theme='streamlit')

def gerar_excel_download(df, nome_aba):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=nome_aba, index=False)
    output.seek(0)
    return output

# Funções de carregamento de dados
@st.cache_data
def carregar_dados():
    df_blitz = pd.read_csv("data/blitzPessoas.csv", parse_dates=["data_turno", "dt_admissao"])
    df_turnos_pessoas = pd.read_csv("data/turnos_pessoas_pessoas.csv")
    df_turnos = pd.read_csv("data/turnosPessoas.csv", parse_dates=["dt_inicio"])
    df_pessoas = pd.read_csv("data/pessoas.csv", parse_dates=["dt_admissao"])
    return df_blitz, df_turnos_pessoas, df_turnos, df_pessoas

@st.cache_data
def carregar_dados_ncs():
    try:
        df_respostas = pd.read_csv("data/respostas.csv")
        return df_respostas[df_respostas['resposta_int'] == 2]
    except Exception as e:
        st.error(f"Erro ao carregar dados de NCs: {e}")
        return pd.DataFrame()


# Função principal
def app():
    # Carrega os dados
    df_blitz, df_turnos_pessoas, df_turnos, df_pessoas = carregar_dados()

    # Prepara os dados
    df = df_blitz.copy()
    df = df[df['data_turno'].dt.year >= 2025]
    df['funcao_geral'] = df.sort_values('dt_admissao').groupby('idtb_oper_pessoa')['funcao_geral'].transform('last')
   
    # Configuração da barra lateral
    st.sidebar.header("Filtros")
    
    # Botão para atualizar dados
    if st.sidebar.button('🔄 Atualizar Dados'):
        try:
            from exporta_dados_para_pessoasblitz_csv import exportar_dados
            exportar_dados()
            st.success("✅ Dados atualizados com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro ao atualizar os dados: {e}")

    # Data da última atualização
    caminho_csv = 'data/blitzPessoas.csv'
    if os.path.exists(caminho_csv):
        ultima_modificacao = os.path.getmtime(caminho_csv)
        data_formatada = datetime.fromtimestamp(ultima_modificacao).strftime('%d/%m/%Y %H:%M:%S')
        st.sidebar.caption(f"🕒 Última atualização: {data_formatada}")

    # Filtros
    ano_mais_recente = df['data_turno'].dt.year.max()
    mes_mais_recente = df[df['data_turno'].dt.year == ano_mais_recente]['data_turno'].dt.month.max()

    ano_selecionado = st.sidebar.selectbox("Ano", sorted(df['data_turno'].dt.year.unique()), index=0)
    meses_disponiveis = df[df['data_turno'].dt.year == ano_selecionado]['data_turno'].dt.month.unique()
    meses_selecionados = st.sidebar.multiselect("Meses", sorted(meses_disponiveis), default=[mes_mais_recente])

    # Filtro por semanas (1 a 52)
    df['semana'] = df['data_turno'].dt.isocalendar().week
    semanas_disponiveis = sorted(df[(df['data_turno'].dt.year == ano_selecionado) & 
                                    (df['data_turno'].dt.month.isin(meses_selecionados))]['semana'].unique())
    semanas_selecionadas = st.sidebar.multiselect("Semanas (1-52)", semanas_disponiveis, default=semanas_disponiveis)


    empresas = df['nom_fant'].unique()
    empresa_selecionada = st.sidebar.selectbox("Empresa", sorted(empresas), index=0)

    unidades = df[df['nom_fant'] == empresa_selecionada]['unidade'].unique()
    unidades_selecionadas = st.sidebar.multiselect("Unidades", sorted(unidades), default=sorted(unidades))

    nomes = df['nome'].unique().tolist()
    nomes_selecionados = st.sidebar.multiselect("Nomes", nomes)

    funcoes = df['funcao_geral'].dropna().unique().tolist()
    funcoes_selecionadas = st.sidebar.multiselect("Funções Gerais", sorted(funcoes), key="filtro_funcoes")

    # Filtra por situação
    situacoes_selecionadas = ["Em Atividade"]
    df_pessoas = df_pessoas[df_pessoas['situacao'].isin(situacoes_selecionadas)]

    # Aplica filtros principais
    df_filtrado = df[
    (df['data_turno'].dt.year == ano_selecionado) &
    (df['data_turno'].dt.month.isin(meses_selecionados)) &
    (df['semana'].isin(semanas_selecionadas)) &
    (df['nom_fant'] == empresa_selecionada) &
    (df['unidade'].isin(unidades_selecionadas))
]


    if nomes_selecionados:
        df_filtrado = df_filtrado[df_filtrado['nome'].isin(nomes_selecionados)]

    if funcoes_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['funcao_geral'].isin(funcoes_selecionadas)]

    # Filtro de instrutor (mantido do seu código original)
    categorias_funcao = {
        "SESMT": ["TÉCNICO DE SEGURANÇA DO TRABALHO", "TECNICO DE SEGURANÇA DO TRABALHO II", "COORDENADOR DE SEGURANÇA","TECNICO DE SEGURANÇA DO TRABALHO"],
        "SUPERVISÃO": ["SUPERVISOR", "SUPERVISOR ", "LIDER DE CAMPO"]
    }

    df_inspetores = df_filtrado[['nome_inspetor']].dropna().drop_duplicates()
    df_inspetores = df_inspetores.merge(
        df_pessoas[['nome', 'funcao_geral']],
        left_on='nome_inspetor',
        right_on='nome',
        how='left'
    )
    df_inspetores = df_inspetores[['nome_inspetor', 'funcao_geral']].drop_duplicates()
    df_inspetores = df_inspetores.rename(columns={'nome_inspetor': 'Inspetor', 'funcao_geral': 'Função'}).dropna()

    seleciona_sesmt = st.sidebar.checkbox("SESMT", value=True)
    seleciona_supervisao = st.sidebar.checkbox("SUPERVISÃO", value=True)

    funcoes_instrutor_selecionadas = []
    if seleciona_sesmt:
        funcoes_instrutor_selecionadas.extend(categorias_funcao["SESMT"])
    if seleciona_supervisao:
        funcoes_instrutor_selecionadas.extend(categorias_funcao["SUPERVISÃO"])

    df_inspetores_filtrado = df_inspetores[df_inspetores['Função'].isin(funcoes_instrutor_selecionadas)]
    inspetores_validos = df_inspetores_filtrado['Inspetor'].unique().tolist()
    df_filtrado = df_filtrado[df_filtrado['nome_inspetor'].isin(inspetores_validos)]

    instrutores_disponiveis = sorted(inspetores_validos)
    instrutores_disponiveis.insert(0, "Todos")

    instrutor_selecionado = st.sidebar.selectbox("Instrutor", options=instrutores_disponiveis, key="instrutor_categoria")

    if instrutor_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['nome_inspetor'] == instrutor_selecionado]

    # Conteúdo principal
    st.markdown("<h3 style='text-align:center;'>📊 INDICADORES DE TAXA DE CONTATO POR FUNÇÃO</h3><hr>", unsafe_allow_html=True)
    
    # Abas principais
    tabelas, taxa_ont, funcao, unidade, icit, detanhe_nc = st.tabs(['📌 PESSOAS INSPECIONADAS X NÃO INSPECIONADAS', 'TAXA DE CONTATO MENSAL', '📈 TAXA DE CONTATO POR FUNÇÃO', '📉 TAXA DE CONTATO POR UNIDADE', 'ICIT',' DETALHE REPROVAÇÃO'])
    
    with tabelas:
        
        df_inspecoes = df_filtrado.groupby('nome').agg(
            QT_INSPEÇÕES=('idtb_turnos', 'nunique'),
            FUNÇÃO=('funcao_geral', 'last'),
            dt_admissao=('dt_admissao', 'last'),
            unidade=('unidade', 'last'),
            ultima_inspecao=('data_turno', 'max'),
            inspetor=('nome_inspetor', 'last')
        ).reset_index()

        
        # Tabela de nomes não inspecionados
        df_turnos_filtrado = df_turnos[
            (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
            (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados)) &
            (df_turnos['nom_fant'] == empresa_selecionada) &
            (df_turnos['unidade'].isin(unidades_selecionadas))
        ]
        ids_turnos_filtrados = df_turnos_filtrado['idtb_turnos'].unique()
        df_tp_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(ids_turnos_filtrados)]

        df_pessoas_turnos = df_tp_filtrado.merge(
            df_pessoas, left_on="idtb_pessoas", right_on="idtb_oper_pessoa", how="left"
        ).merge(
            df_turnos[['idtb_turnos', 'unidade']], on='idtb_turnos', how='left'
        ).drop_duplicates("nome")

        df_nao_inspecionadas = df_pessoas_turnos[~df_pessoas_turnos['nome'].isin(df_inspecoes['nome'])]
        df_nao_inspecionadas['dt_admissao'] = pd.to_datetime(df_nao_inspecionadas['dt_admissao']).dt.strftime('%d/%m/%Y')

        df_nao_inspecionadas_final = df_nao_inspecionadas[["nome", "funcao_geral", "unidade", "dt_admissao"]]
        
 

        # Garante que ambos os DataFrames tenham a coluna 'nome'
        if 'nome' in df_pessoas_turnos.columns and 'nome' in df_inspecoes.columns:
            
            total_pessoas = df_pessoas_turnos['nome'].nunique()

            # Pega os nomes únicos de cada DataFrame
            nomes_com_turno = set(df_pessoas_turnos['nome'].unique())
            nomes_inspecionados = set(df_inspecoes['nome'].unique())

            # Calcula a interseção para saber quem tem turno E foi inspecionado
            nomes_inspecionados_com_turno = nomes_com_turno.intersection(nomes_inspecionados)
            
            total_inspecionadas = len(nomes_inspecionados_com_turno)

            # Garante que o número de não inspecionados nunca seja negativo
            total_nao_inspecionadas = total_pessoas - total_inspecionadas
            
            # Calcula as porcentagens, tratando o caso de divisão por zero
            p_inspecionadas = (total_inspecionadas / total_pessoas) * 100 if total_pessoas > 0 else 0
            p_nao_inspecionadas = (total_nao_inspecionadas / total_pessoas) * 100 if total_pessoas > 0 else 0

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                    <div style="text-align:center">
                        <h4>👥 Pessoas com Turno</h4>
                        <h2 style="color:#00BFFF;">{total_pessoas}</h2>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div style="text-align:center">
                        <h4>✅ Inspecionadas</h4>
                        <h2 style="color:#2E8B57;">{total_inspecionadas}</h2>
                        <p style="color:#2E8B57;font-weight:bold;">{p_inspecionadas:.2f}%</p>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div style="text-align:center">
                        <h4>❌ Não Inspecionadas</h4>
                        <h2 style="color:#FF6347;">{total_nao_inspecionadas}</h2>
                        <p style="color:#FF6347;font-weight:bold;">{p_nao_inspecionadas:.2f}%</p>
                    </div>
                """, unsafe_allow_html=True)

        else:
                st.error("A coluna 'nome' não foi encontrada em um dos DataFrames.")

        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            # Tabela de nomes inspecionados
            df_inspecoes = df_filtrado.groupby('nome').agg(
                QT_INSPEÇÕES=('idtb_turnos', 'nunique'),
                FUNÇÃO=('funcao_geral', 'last'),
                dt_admissao=('dt_admissao', 'last'),
                unidade=('unidade', 'last'),
                ultima_inspecao=('data_turno', 'max'),
                inspetor=('nome_inspetor', 'last')
            ).reset_index()

            df_inspecoes['dt_admissao'] = pd.to_datetime(df_inspecoes['dt_admissao']).dt.strftime('%d/%m/%Y')
            df_inspecoes['ultima_inspecao'] = pd.to_datetime(df_inspecoes['ultima_inspecao']).dt.strftime('%d/%m/%Y')

            df_inspecoes_final = df_inspecoes[["nome", "FUNÇÃO", "unidade", "QT_INSPEÇÕES", "ultima_inspecao", "inspetor", "dt_admissao"]]
            criar_tabela_aggrid(df_inspecoes_final, "NOMES INSPECIONADOS")

            st.download_button(
                label="📥 Baixar Excel - Nomes Inspecionados",
                data=gerar_excel_download(df_inspecoes_final, "Inspecionados"),
                file_name="nomes_inspecionados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            # Tabela de nomes não inspecionados
            df_turnos_filtrado = df_turnos[
                (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
                (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados)) &
                (df_turnos['nom_fant'] == empresa_selecionada) &
                (df_turnos['unidade'].isin(unidades_selecionadas))
            ]
            ids_turnos_filtrados = df_turnos_filtrado['idtb_turnos'].unique()
            df_tp_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(ids_turnos_filtrados)]

            df_pessoas_turnos = df_tp_filtrado.merge(
                df_pessoas, left_on="idtb_pessoas", right_on="idtb_oper_pessoa", how="left"
            ).merge(
                df_turnos[['idtb_turnos', 'unidade']], on='idtb_turnos', how='left'
            ).drop_duplicates("nome")

            df_nao_inspecionadas = df_pessoas_turnos[~df_pessoas_turnos['nome'].isin(df_inspecoes['nome'])]
            df_nao_inspecionadas['dt_admissao'] = pd.to_datetime(df_nao_inspecionadas['dt_admissao']).dt.strftime('%d/%m/%Y')

            df_nao_inspecionadas_final = df_nao_inspecionadas[["nome", "funcao_geral", "unidade", "dt_admissao"]]
            criar_tabela_aggrid(df_nao_inspecionadas_final, "NOMES NÃO INSPECIONADOS")

            st.download_button(
                label="📥 Baixar Excel - Nomes Não Inspecionados",
                data=gerar_excel_download(df_nao_inspecionadas_final, "Nao_Inspecionados"),
                file_name="nomes_nao_inspecionados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )



#---------------------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------GERAL TAXA CONTATO PESSOAS --------------------------------------------------------------#        

 
#--------------------------------------------------------------------------------------------------------------#
#---------------------------------- taxa de contato por unidade -----------------------------------------------# 

       
    with unidade:
        
        import io
        import base64
        import plotly.graph_objects as go

        # Aplica o filtro de situação no df_pessoas antes do merge
        situacoes_disponiveis = df_pessoas['situacao'].dropna().unique().tolist()
        situacoes_disponiveis = sorted(situacoes_disponiveis)

        situacoes_selecionadas = st.sidebar.multiselect(
            "Situação do Eletricista",
            options=situacoes_disponiveis,
            default=["Em Atividade"]
        )

        df_pessoas_filtrado = df_pessoas[df_pessoas['situacao'].isin(situacoes_selecionadas)]

        df_turnos_filtrado = df_turnos[
            (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
            (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados)) &
            (df_turnos['nom_fant'] == empresa_selecionada) &
            (df_turnos['unidade'].isin(unidades_selecionadas))
        ]
        ids_turnos_filtrados = df_turnos_filtrado['idtb_turnos'].unique()
        df_tp_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(ids_turnos_filtrados)]

        df_pessoas_turnos = df_tp_filtrado.merge(
            df_pessoas_filtrado, left_on="idtb_pessoas", right_on="idtb_oper_pessoa", how="left"
        ).merge(
            df_turnos[['idtb_turnos', 'unidade']], on='idtb_turnos', how='left'
        ).drop_duplicates(subset=['idtb_pessoas', 'idtb_turnos'])

        total_por_unidade = df_pessoas_turnos.groupby('unidade')['idtb_pessoas'].nunique().reset_index(name='total_pessoas')
        df_inspecionados = df_filtrado[['nome', 'unidade']].drop_duplicates()
        inspec_por_unidade = df_inspecionados.groupby('unidade')['nome'].nunique().reset_index(name='inspecionadas')

        taxa_unidade = pd.merge(total_por_unidade, inspec_por_unidade, on='unidade', how='left').fillna(0)
        taxa_unidade['nao_inspecionadas'] = taxa_unidade['total_pessoas'] - taxa_unidade['inspecionadas']
        taxa_unidade = taxa_unidade.sort_values('total_pessoas', ascending=False)

        # 🔹 GRÁFICOS POR UNIDADE
        for i in range(0, len(taxa_unidade), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(taxa_unidade):
                    row = taxa_unidade.iloc[i + j]
                    unidade_nome = row['unidade']
                    with cols[j]:
                        # Gráfico de rosca da unidade
                        total = int(row['total_pessoas'])
                        fig = go.Figure(data=[
                            go.Pie(
                                labels=['Inspecionadas', 'Não Inspecionadas'],
                                values=[row['inspecionadas'], row['nao_inspecionadas']],
                                hole=0.5,
                                marker=dict(colors=['#2E8B57', '#dc143c']),
                                textinfo='percent+value',
                                hoverinfo='label+value+percent',
                                textfont=dict(size=18, color="white", family="Arial Black")
                            )
                        ])
                        fig.update_layout(
                            title=unidade_nome,
                            showlegend=True,
                            legend=dict(font=dict(size=16, color='black')),
                            annotations=[dict(
                                text=f"<b>{total}<br>Pessoas</b>",
                                font=dict(size=20, color="black"),
                                showarrow=False,
                                x=0.5,
                                y=0.5
                            )]
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Exportar para Excel
                        df_unit = df_pessoas_turnos[df_pessoas_turnos['unidade'] == unidade_nome]
                        nomes_inspecionados = df_inspecionados[df_inspecionados['unidade'] == unidade_nome]['nome'].unique()

                        df_unit['Status'] = df_unit['nome'].apply(lambda x: 'Inspecionado' if x in nomes_inspecionados else 'Não Inspecionado')
                        df_exportar = df_unit[['nome', 'unidade', 'funcao_geral', 'dt_admissao', 'Status']].drop_duplicates()

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_exportar.to_excel(writer, index=False, sheet_name='Relatório')
                        dados_excel = output.getvalue()

                        st.download_button(
                            label="📥 Baixar Excel da Unidade",
                            data=dados_excel,
                            file_name=f"taxa_contato_{unidade_nome}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )





#----------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------taxa de contato por função- -------------------------------------------------#
        

        df_func_total = df_pessoas_turnos.groupby('funcao_geral')['nome'].nunique().reset_index(name='total_pessoas')
        df_func_inspec = df_inspecoes.groupby('FUNÇÃO')['nome'].nunique().reset_index(name='total_inspecionadas')

        taxa_contato = pd.merge(df_func_total, df_func_inspec, left_on='funcao_geral', right_on='FUNÇÃO', how='left').fillna(0)
        taxa_contato['taxa_contato'] = (taxa_contato['total_inspecionadas'] / taxa_contato['total_pessoas']) * 100
        
        
    #------------------------------------------------------------------------------------------------------------------------------------------
    
    
        
        
        
        
    with funcao:
        
        col1, col2, col3, col4 = st.columns(4)

        def criar_grafico_rosca(funcao, total, inspecionadas):
            inspecionadas, nao = ajustar_valores_grafico(total, inspecionadas)
            fig = go.Figure(data=[
                go.Pie(
                    labels=["Inspecionadas", "Não Inspecionadas"],
                    values=[inspecionadas, nao],
                    hole=0.5,
                    marker=dict(colors=['#2E8B57', '#dc143c']),
                    textinfo='percent+value',
                    textfont=dict(color='white', size=18, family="Arial Black"),
                    hoverinfo='label+value+percent'
                )
            ])
            fig.update_layout(
                title=f"{funcao}",
                showlegend=True,
                legend=dict(
                    font=dict(size=16, color="black")  # ✅ legenda preta e maior
                ),
                annotations=[dict(
                    text=f"<b>{total}<br>Pessoas</b>",
                    x=0.5,
                    y=0.5,
                    font=dict(size=20, color="black"),  # ✅ indicador central preto
                    showarrow=False
                )],
                template="plotly_white"
            )
            return fig





        for i, row in taxa_contato.iterrows():
            col = [col1, col2, col3, col4][i % 4]
            with col:
                st.plotly_chart(
                    criar_grafico_rosca(row['funcao_geral'], row['total_pessoas'], row['total_inspecionadas']),
                    use_container_width=True
                )
#---------------------------------------------------------------------------------------------------------------------#

    with taxa_ont:
        
        import calendar
        import plotly.graph_objects as go
        def grafico_taxa_inspecao_bimestral_com_filtros(
        df_filtrado, df_turnos, df_turnos_pessoas, df_pessoas,
        ano, meses, empresa, unidades, nomes_selecionados, funcoes_selecionadas, situacoes_selecionadas
    ):
     

            df_turnos_filtrado = df_turnos[
                (df_turnos['dt_inicio'].dt.year == ano) &
                (df_turnos['dt_inicio'].dt.month.isin(meses)) &
                (df_turnos['nom_fant'] == empresa) &
                (df_turnos['unidade'].isin(unidades))
            ]

            ids_turnos_filtrados = df_turnos_filtrado['idtb_turnos'].unique()

            df_pessoas_filtrado = df_pessoas[df_pessoas['situacao'].isin(situacoes_selecionadas)]
            if funcoes_selecionadas:
                df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado['funcao_geral'].isin(funcoes_selecionadas)]
            if nomes_selecionados:
                df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado['nome'].isin(nomes_selecionados)]

            df_tp_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(ids_turnos_filtrados)]

            df_pessoas_turnos = df_tp_filtrado.merge(
                df_pessoas_filtrado[['idtb_oper_pessoa', 'nome', 'funcao_geral']],
                left_on='idtb_pessoas',
                right_on='idtb_oper_pessoa',
                how='inner'
            ).merge(
                df_turnos_filtrado[['idtb_turnos', 'dt_inicio', 'unidade', 'nom_fant']],
                on='idtb_turnos',
                how='left'
            )

            bimestres = [(m, m + 1) for m in range(1, 13, 2)]
            nomes_bimestres = []
            taxa_inspecionadas = []
            taxa_nao_inspecionadas = []
            qtd_inspecionadas = []
            qtd_nao_inspecionadas = []

            for m1, m2 in bimestres:
                meses_bimestre = [m1, m2]

                pessoas_bimestre = df_pessoas_turnos[df_pessoas_turnos['dt_inicio'].dt.month.isin(meses_bimestre)]
                total_pessoas = pessoas_bimestre['idtb_pessoas'].nunique()

                # Ignora bimestre sem pessoas
                if total_pessoas == 0:
                    continue

                nomes_bimestres.append(f"{calendar.month_abbr[m1]}/{calendar.month_abbr[m2]}")

                inspec_bimestre = df_filtrado[
                    (df_filtrado['data_turno'].dt.year == ano) &
                    (df_filtrado['data_turno'].dt.month.isin(meses_bimestre)) &
                    (df_filtrado['nom_fant'] == empresa) &
                    (df_filtrado['unidade'].isin(unidades))
                ]
                if nomes_selecionados:
                    inspec_bimestre = inspec_bimestre[inspec_bimestre['nome'].isin(nomes_selecionados)]
                if funcoes_selecionadas:
                    inspec_bimestre = inspec_bimestre[inspec_bimestre['funcao_geral'].isin(funcoes_selecionadas)]

                inspecionadas = inspec_bimestre['nome'].nunique()

                taxa = (inspecionadas / total_pessoas) * 100 if total_pessoas else 0
                taxa = min(taxa, 100)  # limite máximo 100%
                taxa_inspecionadas.append(taxa)

                taxa_nao = 100 - taxa
                taxa_nao = max(min(taxa_nao, 100), 0)  # limite entre 0 e 100
                taxa_nao_inspecionadas.append(taxa_nao)

                qtd_inspecionadas.append(inspecionadas)
                qtd_nao_inspecionadas.append(total_pessoas - inspecionadas)


            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=nomes_bimestres,
                y=taxa_inspecionadas,
                name='Inspecionadas',
                marker_color='#2E8B57',
                text=[str(q) for q in qtd_inspecionadas],
                textposition='inside',
                textfont=dict(color='white', size=18)
            ))

            fig.add_trace(go.Bar(
                x=nomes_bimestres,
                y=taxa_inspecionadas,
                name='',
                marker_color='rgba(0,0,0,0)',
                text=[f"{p:.1f}%" for p in taxa_inspecionadas],
                textposition='outside',
                textfont=dict(color='black', size=18),
                showlegend=False
            ))

            fig.add_trace(go.Bar(
                x=nomes_bimestres,
                y=taxa_nao_inspecionadas,
                name='Não Inspecionadas',
                marker_color='#dc143c',
                text=[str(q) for q in qtd_nao_inspecionadas],
                textposition='inside',
                textfont=dict(color='white', size=18)
            ))

            fig.add_trace(go.Bar(
                x=nomes_bimestres,
                y=taxa_nao_inspecionadas,
                name='',
                marker_color='rgba(0,0,0,0)',
                text=[f"{p:.1f}%" for p in taxa_nao_inspecionadas],
                textposition='outside',
                textfont=dict(color='black', size=18),
                showlegend=False
            ))

            fig.update_layout(
                height=650,  # ⬅️ aumenta a altura para evitar corte
                barmode='group',
                title="",
                yaxis_title="",
                xaxis_title="",
                yaxis=dict(range=[0, 110]),
                legend=dict(font=dict(size=18)),
                template="plotly_white",
                xaxis=dict(
                    tickfont=dict(
                        color='black',
                        size=16
                    )
                )
            )

            st.plotly_chart(fig, use_container_width=True)




        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;'>📊 Evolução Bimestral da Taxa de Inspeção - {ano_selecionado}</h3>", unsafe_allow_html=True)

        grafico_taxa_inspecao_bimestral_com_filtros(
                df_filtrado=df_filtrado,
                df_turnos=df_turnos,
                df_turnos_pessoas=df_turnos_pessoas,
                df_pessoas=df_pessoas,
                ano=ano_selecionado,
                meses=meses_selecionados,
                empresa=empresa_selecionada,
                unidades=unidades_selecionadas,
                nomes_selecionados=nomes_selecionados,
                funcoes_selecionadas=funcoes_selecionadas,
                situacoes_selecionadas=situacoes_selecionadas
            )


#-----------------------------------------------------------------------------taxa 2 teste


        import calendar
        import plotly.graph_objects as go

        def grafico_taxa_inspecao_mensal_com_filtros(
            df_filtrado, df_turnos, df_turnos_pessoas, df_pessoas,
            ano, meses, empresa, unidades, nomes_selecionados, funcoes_selecionadas, situacoes_selecionadas
        ):
            # Filtra turnos segundo filtros da UI
            df_turnos_filtrado = df_turnos[
                (df_turnos['dt_inicio'].dt.year == ano) &
                (df_turnos['dt_inicio'].dt.month.isin(meses)) &
                (df_turnos['nom_fant'] == empresa) &
                (df_turnos['unidade'].isin(unidades))
            ]

            ids_turnos_filtrados = df_turnos_filtrado['idtb_turnos'].unique()

            # Filtra pessoas segundo situação e outras opções
            df_pessoas_filtrado = df_pessoas[df_pessoas['situacao'].isin(situacoes_selecionadas)]
            if funcoes_selecionadas:
                df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado['funcao_geral'].isin(funcoes_selecionadas)]
            if nomes_selecionados:
                df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado['nome'].isin(nomes_selecionados)]

            # Filtra turnos_pessoas com turnos válidos
            df_tp_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(ids_turnos_filtrados)]

            # Merge para juntar informações das pessoas e dos turnos
            df_pessoas_turnos = df_tp_filtrado.merge(
                df_pessoas_filtrado[['idtb_oper_pessoa', 'nome', 'funcao_geral']],
                left_on='idtb_pessoas',
                right_on='idtb_oper_pessoa',
                how='inner'  # inner para respeitar filtros de pessoa
            ).merge(
                df_turnos_filtrado[['idtb_turnos', 'dt_inicio', 'unidade', 'nom_fant']],
                on='idtb_turnos',
                how='left'
            )

            meses_ano = sorted(meses)
            meses_nome = [calendar.month_name[m] for m in meses_ano]

            taxa_inspecionadas = []
            taxa_nao_inspecionadas = []
            qtd_inspecionadas_mes = []
            qtd_nao_inspecionadas_mes = []

            for mes in meses_ano:
                pessoas_mes = df_pessoas_turnos[df_pessoas_turnos['dt_inicio'].dt.month == mes]
                total_pessoas_mes = pessoas_mes['idtb_pessoas'].nunique()

                inspec_mes = df_filtrado[
                    (df_filtrado['data_turno'].dt.year == ano) &
                    (df_filtrado['data_turno'].dt.month == mes) &
                    (df_filtrado['nom_fant'] == empresa) &
                    (df_filtrado['unidade'].isin(unidades))
                ]
                if nomes_selecionados:
                    inspec_mes = inspec_mes[inspec_mes['nome'].isin(nomes_selecionados)]
                if funcoes_selecionadas:
                    inspec_mes = inspec_mes[inspec_mes['funcao_geral'].isin(funcoes_selecionadas)]

                inspecionadas_mes = inspec_mes['nome'].nunique()

                p_inspecionadas = (inspecionadas_mes / total_pessoas_mes) * 100 if total_pessoas_mes else 0
                p_inspecionadas = min(p_inspecionadas, 100)

                p_nao_inspecionadas = 100 - p_inspecionadas
                p_nao_inspecionadas = max(min(p_nao_inspecionadas, 100), 0)

                taxa_inspecionadas.append(p_inspecionadas)
                taxa_nao_inspecionadas.append(p_nao_inspecionadas)
                qtd_inspecionadas_mes.append(inspecionadas_mes)
                qtd_nao_inspecionadas_mes.append(total_pessoas_mes - inspecionadas_mes if total_pessoas_mes else 0)


            fig = go.Figure()

            # INSPECIONADAS – valor dentro da barra
            fig.add_trace(go.Bar(
                x=meses_nome,
                y=taxa_inspecionadas,
                name='Inspecionadas',
                marker_color='#2E8B57',
                text=[str(q) for q in qtd_inspecionadas_mes],
                textposition='inside',
                textfont=dict(color='white', size=18)
            ))

            # INSPECIONADAS – porcentagem acima da barra
            fig.add_trace(go.Bar(
                x=meses_nome,
                y=taxa_inspecionadas,
                name='',
                marker_color='rgba(0,0,0,0)',
                text=[f"{p:.1f}%" for p in taxa_inspecionadas],
                textposition='outside',
                textfont=dict(color='black', size=18),
                showlegend=False
            ))

            # NÃO INSPECIONADAS – valor dentro da barra
            fig.add_trace(go.Bar(
                x=meses_nome,
                y=taxa_nao_inspecionadas,
                name='Não Inspecionadas',
                marker_color='#dc143c',
                text=[str(q) for q in qtd_nao_inspecionadas_mes],
                textposition='inside',
                textfont=dict(color='white', size=18)
            ))

            # NÃO INSPECIONADAS – porcentagem acima da barra
            fig.add_trace(go.Bar(
                x=meses_nome,
                y=taxa_nao_inspecionadas,
                name='',
                marker_color='rgba(0,0,0,0)',
                text=[f"{p:.1f}%" for p in taxa_nao_inspecionadas],
                textposition='outside',
                textfont=dict(color='black', size=18),
                showlegend=False
            ))

            fig.update_layout(
            height=650,
            barmode='group',
            title="",
            yaxis_title="",
            xaxis_title="",
            yaxis=dict(range=[0, 110]),
            legend=dict(font=dict(size=18)),
            template="plotly_white",
            xaxis=dict(
                tickfont=dict(
                    color='black',
                    size=16
                )
            )
        )


            st.plotly_chart(fig, use_container_width=True)


        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;'>📊 Evolução Mensal da Taxa de Inspeção - {ano_selecionado}</h3>", unsafe_allow_html=True)

        grafico_taxa_inspecao_mensal_com_filtros(
            df_filtrado=df_filtrado,
            df_turnos=df_turnos,
            df_turnos_pessoas=df_turnos_pessoas,
            df_pessoas=df_pessoas,
            ano=ano_selecionado,
            meses=meses_selecionados,
            empresa=empresa_selecionada,
            unidades=unidades_selecionadas,
            nomes_selecionados=nomes_selecionados,
            funcoes_selecionadas=funcoes_selecionadas,
            situacoes_selecionadas=situacoes_selecionadas
    )




    with icit:
        
       
        # 1. CARREGAMENTO E FILTRO RIGOROSO
        df_ncs = carregar_dados_ncs()
        
        if not df_ncs.empty:
            # Filtro oficial conforme regras estritas
            df_ncs_validas = df_ncs[
                (df_ncs['resposta_int'] == 2) &          # Somente reprovações
                (df_ncs['idtb_pesoas'] > 0) &            # Descartar registros de equipe (id=0) - COLUNA CORRIGIDA
                (df_ncs['Key'].notna())                  # Key não pode ser nula
            ].copy()
            
            # Remove duplicatas mantendo a primeira ocorrência de cada Key única
            df_ncs_validas = df_ncs_validas.drop_duplicates(subset=['Key'])
            
           
            # 3. JUNÇÃO COM DADOS DE INSPEÇÃO (só pessoas inspecionadas)
            # Primeiro obtemos o mapeamento de idtb_pesoas para nome
            df_pessoas_mapeamento = df_filtrado[['idtb_oper_pessoa', 'nome']].drop_duplicates()
            
            df_ncs_final = df_ncs_validas.merge(
            df_pessoas_mapeamento,
            left_on='idtb_pesoas',
            right_on='idtb_oper_pessoa',
            how='inner'
        ).merge(
            df_filtrado[['idtb_turnos', 'unidade']].drop_duplicates(),
            on='idtb_turnos',
            how='inner'
        )
        

            total_ncs = df_ncs_final['Key'].nunique()
            total_pessoas_com_nc = df_ncs_final['nome'].nunique()
            total_pessoas_inspec = df_filtrado['nome'].nunique()
            
           
            media_nc = total_ncs/total_pessoas_com_nc if total_pessoas_com_nc > 0 else 0
                
#----------------------- cartoes informativos --------------------------------------------------------#

 # CSS para os cartões
            st.markdown(
                """
                <style>
                .card-container {
                    display: flex;
                    justify-content: space-between;
                    gap: 1rem;
                    margin-bottom: 1.5rem;
                }
                .card {
                    background: #fff;
                    padding: 1rem 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
                    flex: 1;
                    min-width: 200px;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                .card-icon {
                    flex-shrink: 0;
                    width: 40px;
                    height: 40px;
                    color: #1a237e;
                }
                .card-content {
                    display: flex;
                    flex-direction: column;
                }
                .card-value {
                    font-size: 1.6rem;
                    font-weight: 700;
                    color: #1a237e;
                }
                .card-label {
                    font-size: 0.85rem;
                    color: #555;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-top: 4px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # Ícones SVG
            icon_nc = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>"""
            icon_people_nc = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 1.34 3 3 3zM8 11c1.66 0 3-1.34 3-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2 0-6 1-6 3v2h12v-2c0-2-4-3-6-3zm8 0c-2 0-6 1-6 3v2h12v-2c0-2-4-3-6-3z"/></svg>"""
            icon_people_ok = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h10.5c-.31-.61-.5-1.29-.5-2 0-1.86 1.28-3.43 3-3.87-1.45-.79-3.26-1.13-5-1.13z"/><path d="M17.59 19.41 21 16l-1.41-1.41L17 17.17l-1.59-1.59L14 17l3.59 3.59z"/></svg>"""
            icon_media = """<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24"><path d="M3 17h18v2H3v-2zm0-7h18v2H3v-2zm0-7v2h18V3H3z"/></svg>"""
                
            # Cálculo auxiliar
            total_pessoas_sem_nc = total_pessoas_inspec - total_pessoas_com_nc

            # Formata valores com porcentagem
            pessoas_com_nc_str = f"{total_pessoas_com_nc} ({total_pessoas_com_nc / total_pessoas_inspec * 100:.1f}%)"
            pessoas_sem_nc_str = f"{total_pessoas_sem_nc} ({total_pessoas_sem_nc / total_pessoas_inspec * 100:.1f}%)"

            cards_html = f"""
            <div class="card-container">
            <div class="card">
                <div class="card-icon">{icon_nc}</div>
                <div class="card-content">
                <div class="card-value">{total_ncs}</div>
                <div class="card-label">NCs Validadas</div>
                </div>
            </div>
            <div class="card">
                <div class="card-icon">{icon_people_nc}</div>
                <div class="card-content">
                <div class="card-value">{pessoas_com_nc_str}</div>
                <div class="card-label">Pessoas com NC</div>
                </div>
            </div>
            <div class="card">
                <div class="card-icon">{icon_people_ok}</div>
                <div class="card-content">
                <div class="card-value">{pessoas_sem_nc_str}</div>
                <div class="card-label">Pessoas sem NC</div>
                </div>
            </div>
            <div class="card">
                <div class="card-icon">{icon_media}</div>
                <div class="card-content">
                <div class="card-value">{media_nc:.1f}</div>
                <div class="card-label">Média NCs/Pessoa</div>
                </div>
            </div>
            </div>
            """
#----------------------------------------------------------------------------------------------------------------
            # ✅ Exibe os cartões no topo
            st.markdown(cards_html, unsafe_allow_html=True)
            col1, col2, col3  = st.columns(3)
            with col1:
                st.markdown(f"<h3 style='text-align:center;'> PESSOAS QUE ABRIRAM TURNO </h3>", unsafe_allow_html=True)
          

                # 1️⃣ VALORES DO SCRIPT 1
                # Total de pessoas inspecionadas com NC (já filtrado no Script1)
                pessoas_com_nc = total_pessoas_com_nc

                # Pessoas inspecionadas sem NC
                pessoas_sem_nc = total_pessoas_inspec - total_pessoas_com_nc

                # 2️⃣ VALORES DO SCRIPT 2
                pessoas_com_turno = df_pessoas_turnos['nome'].nunique()
                pessoas_inspecionadas = df_inspecoes['nome'].nunique()
                pessoas_nao_inspecionadas = pessoas_com_turno - pessoas_inspecionadas

                # Corrige valores se necessário
                if pessoas_com_nc + pessoas_sem_nc != pessoas_inspecionadas:
                    pessoas_sem_nc = pessoas_inspecionadas - pessoas_com_nc

                # VALORES PARA O GRÁFICO
                labels = ['REPROVADAS', 'SEM REPROVAÇÃO', 'NÃO INSPECIONADAS']
                values = [pessoas_com_nc, pessoas_sem_nc, pessoas_nao_inspecionadas]
                colors = ['#d62728', '#1f77b4', '#ffcc00']  # vermelho, verde, amarelo

                # 🎯 GRÁFICO DE ROSCA - Contato
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.55,
                    marker=dict(colors=colors),
                    textinfo='percent+value',
                    textposition='outside',  # coloca os valores fora da fatia
                    textfont=dict(color='black', size=18),
                    hovertemplate='<b>%{label}</b><br>%{value} pessoas<br>%{percent}',
                )])

                fig.update_layout(
                    annotations=[dict(
                        text=f"<b>{pessoas_com_turno}</b><br>Pessoas Turnos",
                        x=0.5, y=0.5,
                        font=dict(size=18, color='black'),
                        showarrow=False
                    )],
                    showlegend=True,
                    legend=dict(
                        orientation='h',
                        y=-0.2,
                        x=0.5,
                        xanchor='center',
                        font=dict(size=18, color='black')  # aumenta fonte da legenda
                    ),
                    margin=dict(t=60, b=40, l=20, r=20),
                    height=450
                )


                # Mostra no Streamlit
                st.plotly_chart(fig, use_container_width=True)




            
            # GRÁFICO 2 - Distribuição por Subgrupo com valor central (total NC)
            with col2:
                st.markdown(f"<h3 style='text-align:center;'> REPROVAÇÕES POR CATEGORIA </h3>", unsafe_allow_html=True)

                dist_subgrupo = df_ncs_final['subgrupo'].value_counts().reset_index()
                dist_subgrupo.columns = ['subgrupo', 'count']
                total_nc = dist_subgrupo['count'].sum()

                # GRÁFICO 2 - Distribuição por Categoria
                fig2 = go.Figure(data=[go.Pie(
                    labels=dist_subgrupo['subgrupo'],
                    values=dist_subgrupo['count'],
                    hole=0.55,
                    textinfo='percent+value',
                    textposition='outside',  # coloca valores e % fora da fatia
                    textfont=dict(color='black', size=18),
                    hovertemplate='<b>%{label}</b><br>%{value} NCs<br>%{percent}',
                )])

                fig2.update_layout(
                    annotations=[dict(
                        text=f"<b>{total_nc}</b><br>Reprovados",
                        x=0.5, y=0.5,
                        font=dict(size=18, color='black'),
                        showarrow=False
                    )],
                    showlegend=True,
                    legend=dict(
                        orientation='h',
                        y=-0.2,
                        x=0.5,
                        xanchor='center',
                        font=dict(size=18)  # aumenta fonte da legenda
                    ),
                    margin=dict(t=60, b=40, l=20, r=20),
                    height=450
                )



                st.plotly_chart(fig2, use_container_width=True)

            # GRÁFICO 3 - Apenas inspecionados (com NC e sem NC) ---
            with col3:
                st.markdown(f"<h3 style='text-align:center;'> TAXA ICIT PESSOAS GERAL </h3>", unsafe_allow_html=True)

                labels_inspec = ['REPROVADAS', 'SEM REPROVAÇÃO']
                values_inspec = [pessoas_com_nc, pessoas_sem_nc]
                colors_inspec = ['#d62728', '#1f77b4']

                # GRÁFICO 3 - Apenas Inspecionados
                fig3 = go.Figure(data=[go.Pie(
                    labels=labels_inspec,
                    values=values_inspec,
                    hole=0.55,
                    marker=dict(colors=colors_inspec),
                    textinfo='percent+value',
                    textposition='outside',  # coloca os valores para fora da fatia
                    textfont=dict(color='black', size=22),
                    hovertemplate='<b>%{label}</b><br>%{value} pessoas<br>%{percent}',
                )])

                fig3.update_layout(
                    annotations=[dict(
                        text=f"<b>{pessoas_inspecionadas}</b><br>Inspecionadas",
                        x=0.5, y=0.5,
                        font=dict(size=18, color='black'),
                        showarrow=False
                    )],
                    showlegend=True,
                    legend=dict(
                        orientation='h',
                        y=-0.2,
                        x=0.5,
                        xanchor='center',
                        font=dict(size=18)  # aumenta a fonte da legenda
                    ),
                    margin=dict(t=60, b=40, l=20, r=20),
                    height=450
                )



                st.plotly_chart(fig3, use_container_width=True)

            
            
                # Título
        

#---------------
        st.markdown(f"<h3 style='text-align:center;'> TAXA ICIT POR UNIDADE </h3>", unsafe_allow_html=True)
        # Carregar pessoas e manter a primeira base por nome
        df_pessoas = pd.read_csv("data/pessoas.csv")

        # Garante que só a primeira base por nome seja mantida
        df_pessoas_unica = df_pessoas.sort_values(by='dt_admissao').drop_duplicates(subset='nome', keep='first')

        # Merge da base com os dataframes de inspeções e NCs
        df_filtrado = df_filtrado.merge(df_pessoas_unica[['nome', 'base']], on='nome', how='left')
        df_ncs_final = df_ncs_final.merge(df_pessoas_unica[['nome', 'base']], on='nome', how='left')

        # ✅ Garante contagem única por pessoa (nome)
        df_filtrado_unico = df_filtrado.drop_duplicates(subset='nome')
        df_ncs_final_unico = df_ncs_final.drop_duplicates(subset='nome')

        # Agrupamento por base
        df_nc_base = df_ncs_final_unico.groupby('base')['nome'].nunique().reset_index()
        df_nc_base.columns = ['Base', 'Qtd_Pessoas_Com_NC']

        df_total_pessoas_base = df_filtrado_unico.groupby('base')['nome'].nunique().reset_index()
        df_total_pessoas_base.columns = ['Base', 'Total_Pessoas_Inspecionadas']

        # Merge final para o gráfico
        df_nc_base = df_nc_base.merge(df_total_pessoas_base, on='Base', how='left')
        df_nc_base = df_nc_base.sort_values(by='Qtd_Pessoas_Com_NC', ascending=False)

        # Derretimento para gráfico
        df_plot = pd.melt(
            df_nc_base,
            id_vars='Base',
            value_vars=['Total_Pessoas_Inspecionadas', 'Qtd_Pessoas_Com_NC'],
            var_name='Tipo',
            value_name='Quantidade'
        )

        # Renomeia tipo
        df_plot['Tipo'] = df_plot['Tipo'].replace({
            'Total_Pessoas_Inspecionadas': 'Inspecionadas',
            'Qtd_Pessoas_Com_NC': 'Com NC'
        })

        # Porcentagem e rótulos
        df_plot['Total_Base'] = df_plot.groupby('Base')['Quantidade'].transform('sum')
        df_plot['Porcentagem'] = (df_plot['Quantidade'] / df_plot['Total_Base'] * 100).round(1)
        df_plot['TextoFormatado'] = df_plot.apply(lambda row: f"{row['Quantidade']} ({row['Porcentagem']}%)", axis=1)

        # Cores
        cores = {'Inspecionadas': '#1f77b4', 'Com NC': '#d62728'}

        # Gráfico
        fig = px.bar(
            df_plot,
            x='Base',
            y='Quantidade',
            color='Tipo',
            barmode='group',
            text='TextoFormatado',
            color_discrete_map=cores,
            labels={
                "Quantidade": "Número de Pessoas",
                "Base": "Base",
                "Tipo": "Categoria"
            }
        )

        fig.update_traces(
            textposition='outside',
            textfont=dict(color='black', size=18),
            marker_line_width=1.5
        )

        fig.update_layout(
            yaxis=dict(title=""),
            xaxis=dict(title="", tickfont=dict(color='black', size=18)),
            height=600,
            legend_title_text="",
            uniformtext_minsize=12,
            uniformtext_mode='hide',
            margin=dict(t=60, b=80, l=20, r=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        
        

#----------------- testew 3

        
    with detanhe_nc:                   
     
    # [...] (mantenha o código anterior até a seção de tabelas)

        # 5. TABELA DETALHADA DAS NCs (PARA AUDITORIA)
        st.markdown("### 📋 Lista Completa de NCs Válidas")
        df_detalhe_nc = df_ncs_final[[
                'nome', 'Key', 'pergunta', 'subgrupo', 'pontuacao', 
                'nome_inspetor', 'idtb_pesoas', 'idtb_turnos'
            ]].rename(columns={
                'nome': 'Pessoa',
                'Key': 'ID_NC',
                'pergunta': 'Descrição',
                'subgrupo': 'Categoria',
                'pontuacao': 'Gravidade',
                'nome_inspetor': 'Inspetor',
                'idtb_pesoas': 'ID_Pessoa',
                'idtb_turnos': 'ID_Turno'
            })
            
        criar_tabela_aggrid(df_detalhe_nc, "Registros Oficiais de NCs")
        
#------------------------------------------------- teste -----------------------------------------------------------------------------#

# TABELA PESSOAS x INSPEÇÕES x NCs
        st.markdown("### 👥 Relação Pessoa x Inspeções x NCs")
                
                # 1. Calcula quantidade de inspeções por pessoa
        inspecoes_por_pessoa = df_filtrado.groupby(['nome', 'idtb_oper_pessoa'])['idtb_turnos'] \
                                                .nunique() \
                                                .reset_index() \
                                                .rename(columns={'idtb_turnos': 'Qtd_Inspeções', 
                                                                'idtb_oper_pessoa': 'ID_Pessoa'})
                
                # 2. Calcula quantidade de NCs por pessoa (usando idtb_pesoas)
        if 'df_ncs_final' in locals():
                    ncs_por_pessoa = df_ncs_final.groupby(['nome', 'idtb_pesoas'])['Key'] \
                                                .nunique() \
                                                .reset_index() \
                                                .rename(columns={'Key': 'Qtd_NCs', 
                                                            'idtb_pesoas': 'ID_Pessoa'})
        else:
                    ncs_por_pessoa = pd.DataFrame(columns=['nome', 'ID_Pessoa', 'Qtd_NCs'])
                
                # 3. Merge dos dados
        df_relacao = inspecoes_por_pessoa.merge(
                    ncs_por_pessoa,
                    on=['nome', 'ID_Pessoa'],
                    how='left'
                ).fillna(0)  # Preenche com 0 onde não há NCs
                
                # 4. Formatação final
        df_relacao = df_relacao[['nome', 'ID_Pessoa', 'Qtd_Inspeções', 'Qtd_NCs']] \
                                    .rename(columns={'nome': 'Pessoa'}) \
                                    .sort_values('Qtd_NCs', ascending=False)
                
                # 5. Adiciona coluna de razão NCs/Inspeção
        df_relacao['NCs/Inspeção'] = df_relacao.apply(
                    lambda x: f"{x['Qtd_NCs']/x['Qtd_Inspeções']:.2f}" if x['Qtd_Inspeções'] > 0 else "0",
                    axis=1
                )
                
                # 6. Exibe a tabela
        criar_tabela_aggrid(df_relacao, "Relação Completa por Pessoa")
                
                # 7. Opção para download
        csv = df_relacao.to_csv(index=False).encode('utf-8')
        st.download_button(
                    label="📥 Baixar tabela como CSV",
                    data=csv,
                    file_name='relacao_inspecoes_ncs.csv',
                    mime='text/csv'
                )


  
        
if __name__ == "__main__":
    app()