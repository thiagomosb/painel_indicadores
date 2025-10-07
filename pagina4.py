import mysql.connector
from mysql.connector import Error
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import plotly.express as px
import os
import subprocess
from datetime import datetime, timedelta
import time
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import numpy as np
import colorsys


def app():
    # 🛠️ Função para obter as datas de início e fim de uma semana
    def get_datas_semana(ano, num_semana):
        """
        Calcula as datas de início (segunda) e fim (domingo) para um determinado número de semana e ano.
        """
        try:
            # Usando o formato ISO (%G-W%V-%u) para obter a segunda-feira da semana
            inicio_semana = datetime.strptime(f'{ano}-W{num_semana:02d}-1', "%G-W%V-%u").date()
            fim_semana = inicio_semana + timedelta(days=6)
            return inicio_semana.strftime("%d/%m/%Y"), fim_semana.strftime("%d/%m/%Y")
        except ValueError:
            # Retorna um valor padrão caso a semana não seja válida para o ano
            return "Data inválida", "Data inválida"

    # 🛠️ Função para verificar data de modificação do arquivo
    def get_data_mod_time(file_path):
        if os.path.exists(file_path):
            mod_time = os.path.getmtime(file_path)
            return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(mod_time))
        return "Arquivo não encontrado"

    # Sidebar com botão de atualização
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center;">
            🕒 Última atualização: <strong>{get_data_mod_time('data/turnos_monitoria.csv')}</strong>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔁 Atualizar Dados Agora"):
            with st.spinner("Atualizando arquivos CSV a partir do banco..."):
                subprocess.run(["python", "exporta_dados_monitoria_csv.py"], check=True)
                st.cache_data.clear()
                st.success("✅ CSVs atualizados com sucesso!")
                st.rerun()

    # Função para carregar e processar dados
    @st.cache_data
    def conectar_csv():
        try:
            df_turnos = pd.read_csv("data/turnos_monitoria.csv")
            df_avulsa = pd.read_csv("data/avulsa.csv")
            df_pessoas = pd.read_csv("data/pessoas_monitoria.csv")
            df_turnos_pessoas = pd.read_csv("data/turnos_pessoas_monitoria.csv")
            
            # --- INÍCIO DA MODIFICAÇÃO 1 ---
            # Função para extrair o nome de exibição da equipe (remove os 6 primeiros caracteres)
            def obter_nome_exibicao(equipe):
                equipe_str = str(equipe).strip()
                if len(equipe_str) > 6:
                    return equipe_str[6:]
                return equipe_str

            # Cria a nova coluna para exibição ANTES de qualquer outra modificação
            df_turnos['equipe_display'] = df_turnos['num_operacional'].apply(obter_nome_exibicao)
            df_avulsa['equipe_display'] = df_avulsa['equipe_real'].apply(obter_nome_exibicao)
            # --- FIM DA MODIFICAÇÃO 1 ---

            # Processamento dos dados (Lógica original mantida)
            df_turnos['dt_inicio'] = pd.to_datetime(df_turnos['dt_inicio'], errors='coerce')
            df_turnos['dt_fim'] = pd.to_datetime(df_turnos['dt_fim'], errors='coerce')
            df_avulsa['dt_inicio_serv'] = pd.to_datetime(df_avulsa['dt_inicio_serv'], errors='coerce')

            def classificar_tipo_equipe(equipe):
                equipe = str(equipe).strip()
                if equipe.startswith('9'):
                    return 'Linha Leve'
                elif equipe.startswith('8'):
                    return 'Equipe Pesada'
                elif equipe.startswith('7'):
                    return 'Linha Viva'
                elif equipe.startswith('4'):
                    return 'Moto'
                else:
                    return 'Outros'
            
            df_turnos['tipo_equipe'] = df_turnos['num_operacional'].astype(str).apply(classificar_tipo_equipe)
            df_avulsa['tipo_equipe'] = df_avulsa['equipe_real'].astype(str).apply(classificar_tipo_equipe)

            # Lógica de vínculo original (truncando a chave em df_avulsa) é mantida
            df_avulsa['equipe_real'] = df_avulsa['equipe_real'].astype(str).str[:6].str.strip()
            df_turnos['tipo_prefixo'] = df_turnos['prefixo'].astype(str).apply(lambda x: 'Âncora' if len(x) > 1 else 'Satélite')
            df_avulsa['tipo_contrato'] = df_avulsa['equipe_real'].apply(lambda x: 'Âncora' if len(x) > 7 else 'Satélite')

            df_turnos['relacionamento'] = df_turnos['num_operacional'].astype(str)
            df_avulsa['relacionamento'] = df_avulsa['equipe_real'].astype(str)
            
            df_turnos['semana'] = df_turnos['dt_inicio'].dt.isocalendar().week
            df_avulsa['semana'] = df_avulsa['dt_inicio_serv'].dt.isocalendar().week

            df_turnos = df_turnos.merge(df_turnos_pessoas, on='idtb_turnos', how='left')
            df_turnos = df_turnos[df_turnos['dt_inicio'].dt.year >= 2024]
            df_avulsa = df_avulsa[df_avulsa['dt_inicio_serv'].dt.year >= 2024]

            return df_turnos, df_avulsa, df_pessoas, df_turnos_pessoas
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            return None, None, None, None

    # Carrega os dados
    df_turnos, df_avulsa, df_pessoas, df_turnos_pessoas = conectar_csv()
    
    # Verifica se os dados foram carregados corretamente
    if df_turnos is None or df_avulsa is None:
        st.error("Não foi possível carregar os dados. Verifique os arquivos CSV.")
        return

    # 🔧 Função para aplicar filtros
    def aplicar_filtros(df_turnos, df_avulsa, ano_selecionado, meses_selecionados, empresa_selecionada,
                        unidades_selecionadas, tipo_prefixo_selecionado, equipe_desejada,
                        supervisor_selecionado, monitor_selecionado, semanas_selecionadas,
                        tipos_equipe_selecionados):

        df_turnos_filtrado = df_turnos[
            (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
            (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados)) &
            (df_turnos['semana'].isin(semanas_selecionadas)) &
            (df_turnos['unidade'].isin(unidades_selecionadas)) &
            (df_turnos['nom_fant'] == empresa_selecionada) &
            (df_turnos['tipo_equipe'].isin(tipos_equipe_selecionados))
        ]

        if tipo_prefixo_selecionado != "Todas":
            df_turnos_filtrado = df_turnos_filtrado[df_turnos_filtrado['tipo_prefixo'] == tipo_prefixo_selecionado]

        if equipe_desejada:
            # Filtra pelo nome de exibição ou pelo nome completo/prefixo
            df_turnos_filtrado = df_turnos_filtrado[
                df_turnos_filtrado['num_operacional'].astype(str).str.contains(equipe_desejada, case=False) |
                df_turnos_filtrado['equipe_display'].astype(str).str.contains(equipe_desejada, case=False)
            ]

        # A lógica de vínculo continua usando a chave (prefixo)
        equipes_filtradas = df_turnos_filtrado['num_operacional'].unique()

        df_avulsa_filtrado = df_avulsa[
            (df_avulsa['dt_inicio_serv'].dt.year == ano_selecionado) &
            (df_avulsa['dt_inicio_serv'].dt.month.isin(meses_selecionados)) &
            (df_avulsa['semana'].isin(semanas_selecionadas)) &
            (df_avulsa['unidade'].isin(unidades_selecionadas)) &
            (df_avulsa['equipe_real'].isin(equipes_filtradas)) &
            (df_avulsa['tipo_equipe'].isin(tipos_equipe_selecionados))
        ]

        if supervisor_selecionado != "Todos":
            df_avulsa_filtrado = df_avulsa_filtrado[df_avulsa_filtrado['supervisor'] == supervisor_selecionado]

        if monitor_selecionado != "Todos":
            df_avulsa_filtrado = df_avulsa_filtrado[df_avulsa_filtrado['monitor'] == monitor_selecionado]

        return df_turnos_filtrado.copy(), df_avulsa_filtrado.copy()

    # Logo da empresa
    st.logo('https://www.dolpengenharia.com.br/wp-content/uploads/2021/01/logotipo-definitivo-250614.png')

    # Filtros na barra lateral
    with st.sidebar:
        # Filtro de Ano
        anos = df_turnos['dt_inicio'].dt.year.unique()
        anos_avulsa = df_avulsa['dt_inicio_serv'].dt.year.unique()
        anos_combined = sorted(set(anos) | set(anos_avulsa), reverse=True)
        anos_combined = [ano for ano in anos_combined if ano >= 2024]
        
        ano_atual = pd.Timestamp.now().year
        indice_ano_atual = anos_combined.index(ano_atual) if ano_atual in anos_combined else 0
        ano_selecionado = st.selectbox("Selecione o Ano:", options=anos_combined, index=indice_ano_atual)

        # Filtro de Meses
        meses_com_dados_turnos = df_turnos[df_turnos['dt_inicio'].dt.year == ano_selecionado]['dt_inicio'].dt.month.unique()
        meses_com_dados_avulsa = df_avulsa[df_avulsa['dt_inicio_serv'].dt.year == ano_selecionado]['dt_inicio_serv'].dt.month.unique()
        meses_com_dados = sorted(set(meses_com_dados_turnos) | set(meses_com_dados_avulsa))
        
        mes_mais_recente = max(meses_com_dados) if meses_com_dados else None
        meses_selecionados = st.multiselect(
            "Selecione os Meses:",
            meses_com_dados,
            default=[mes_mais_recente] if mes_mais_recente else []
        )

        # Filtro de Semanas
        semanas_turnos = df_turnos[
            (df_turnos['dt_inicio'].dt.year == ano_selecionado) &
            (df_turnos['dt_inicio'].dt.month.isin(meses_selecionados))
        ]['semana'].unique()

        semanas_avulsa = df_avulsa[
            (df_avulsa['dt_inicio_serv'].dt.year == ano_selecionado) &
            (df_avulsa['dt_inicio_serv'].dt.month.isin(meses_selecionados))
        ]['semana'].unique()

        semanas_disponiveis = sorted(set(semanas_turnos) | set(semanas_avulsa))
        semanas_selecionadas = st.multiselect("Semanas do Ano (1-52)", semanas_disponiveis, default=semanas_disponiveis)

        # Expansor para mostrar as datas correspondentes às semanas selecionadas
        if semanas_selecionadas:
            with st.expander("Ver datas das semanas selecionadas", expanded=False):
                limite_exibicao = 10 
                for semana in sorted(semanas_selecionadas)[:limite_exibicao]:
                    data_inicio, data_fim = get_datas_semana(ano_selecionado, semana)
                    if data_inicio != "Data inválida":
                        st.info(f"**Semana {semana}:** {data_inicio} a {data_fim}")
                
                if len(semanas_selecionadas) > limite_exibicao:
                    st.markdown(f"_(... e mais {len(semanas_selecionadas) - limite_exibicao})_")

        # Filtro de Empresa
        empresas = df_turnos['nom_fant'].unique()
        empresa_selecionada = st.selectbox("Selecione a Empresa:", empresas)

        # Filtro de Unidade
        unidades_filtradas = df_turnos[df_turnos['nom_fant'] == empresa_selecionada]['unidade'].unique()
        unidades_selecionadas = st.multiselect("Selecione as Unidades:", unidades_filtradas, default=unidades_filtradas)

        # Filtro de Tipo de Prefixo
        tipos_prefixo = ['Todas'] + list(df_turnos['tipo_prefixo'].unique())
        tipo_prefixo_selecionado = st.selectbox("Selecione o Tipo de Contrato:", tipos_prefixo)
        
        tipos_de_equipe_disponiveis = sorted(df_turnos['tipo_equipe'].unique())
        tipos_equipe_selecionados = st.multiselect(
            "Selecione o Tipo de Equipe:",
            options=tipos_de_equipe_disponiveis,
            default=tipos_de_equipe_disponiveis
        )

        # Filtro de Equipe
        equipe_desejada = st.text_input("Digite o nome ou prefixo da equipe:")

        # Filtro de Supervisor
        supervisores = ['Todos'] + list(df_avulsa['supervisor'].dropna().unique())
        supervisor_selecionado = st.selectbox("Selecione o Supervisor:", supervisores)

        # Filtro de Monitor
        monitores = ['Todos'] + list(df_avulsa['monitor'].dropna().unique())
        monitor_selecionado = st.selectbox("Selecione o Monitor:", monitores)

    # Aplicando os filtros
    df_turnos_filtrado, df_avulsa_filtrado = aplicar_filtros(
        df_turnos, df_avulsa, ano_selecionado, meses_selecionados, empresa_selecionada,
        unidades_selecionadas, tipo_prefixo_selecionado, equipe_desejada,
        supervisor_selecionado, monitor_selecionado, semanas_selecionadas,
        tipos_equipe_selecionados
    )

    # Conteúdo principal da página
    st.markdown("""
    <div style="text-align: center;">
        <h3>📊 <strong>INDICADORES DE ANALISES DE MONITORAMENTO DAS FILMAGENS</strong></h3>
    </div>
    """, unsafe_allow_html=True)

    # Criando abas para organização
    EQUIPES, EVOLUCAO, EQUIPE_MONITORADAS, PESSOAS = st.tabs([
        "MONITORAMENTO EQUIPE", 
        "EVOLUÇÃO EQUIPES MONITORADAS MÊS", 
        "EQUIPES MONITORADAS", 
        "MONITORAMENTO PESSOAS"
    ])

    with EQUIPES:
        # Dividindo as equipes com base em 'gravou_atividade'
        gravou_atividade_sim = df_avulsa_filtrado[df_avulsa_filtrado['gravou_atividade'] == 'SIM']
        gravou_atividade_nao = df_avulsa_filtrado[df_avulsa_filtrado['gravou_atividade'] == 'NÃO']

        # Removendo duplicação de equipes (contagem por prefixo)
        gravou_atividade_sim_distinct = gravou_atividade_sim.drop_duplicates(subset='equipe_real')
        gravou_atividade_nao_distinct = gravou_atividade_nao.drop_duplicates(subset='equipe_real')

        # Contagem das equipes
        total_gravou_sim = len(gravou_atividade_sim_distinct)
        total_gravou_nao = len(gravou_atividade_nao_distinct)

        # Contando todas as equipes para garantir que o valor de "equipes totais" esteja correto
        total_gravou_sim_total = len(gravou_atividade_sim)
        total_gravou_nao_total = len(gravou_atividade_nao)

        # Concatenando os dois DataFrames e removendo duplicatas
        todas_equipes_distintas = pd.concat([gravou_atividade_sim_distinct, gravou_atividade_nao_distinct])
        todas_equipes_distintas = todas_equipes_distintas.drop_duplicates(subset='equipe_real')

        # Contagem total de equipes distintas
        total_equipes_distintas = len(todas_equipes_distintas)

        # Calculando o total de equipes
        total_equipes = total_gravou_sim_total + total_gravou_nao_total

        # Calculando as porcentagens
        porcentagem_gravou_sim = (total_gravou_sim_total / total_equipes) * 100 if total_equipes > 0 else 0
        porcentagem_gravou_nao = (total_gravou_nao_total / total_equipes) * 100 if total_equipes > 0 else 0

        # Calculando as equipes distintas de num_operacional com base nos filtros de data
        total_equipes_distintas_turnos = df_turnos_filtrado['num_operacional'].nunique() # colocar o prefixo em vez da equipe aqui 

        # Calculando os turnos distintos de 'idtb_turnos' com base nos filtros de data
        total_turnos_distintos = df_turnos_filtrado['idtb_turnos'].nunique()

        # Calculando a porcentagem de equipes que abriram turnos em relação às equipes vistas
        porcentagem_abertura_turnos_equipes = (
                (total_equipes_distintas / total_equipes_distintas_turnos) * 100) if total_equipes_distintas_turnos else 0

        # Calculando a porcentagem de turnos analisados em relação aos turnos abertos
        porcentagem_abertura_turnos = (
                (total_equipes / total_turnos_distintos) * 100) if total_turnos_distintos else 0


        # Criando quatro colunas no Streamlit
        col1, col2, col3, col4 = st.columns(4)

        # Gráfico 1: Aderência Filmagens
        with col1:
            fig1 = go.Figure(data=[go.Pie(
                labels=['Atividades Filmadas', 'Atividades Não Filmadas'],
                values=[total_gravou_sim_total, total_gravou_nao_total],
                hole=0.6,
                marker=dict(colors=['#27AE60', '#E74C3C']),
                textinfo='value',
                textfont=dict(size=18, color="white")
            )])

            fig1.update_layout(
            title='ADERÊNCIA FILMAGENS',
            title_x=0.5,
            annotations=[dict(
                text=f"<b>{porcentagem_gravou_sim:.2f}%</b><br><span style='font-size:16px'>Total: {total_equipes}</span>",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=22, color='black', family='Arial Black')
            )],
            template="plotly_dark",
        )


            st.plotly_chart(fig1, use_container_width=True, key="fig1")
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)

        # Gráfico 2: Aderência Equipes
        with col2:
            equipes_nao_monitoradas = total_equipes_distintas_turnos - total_equipes_distintas

            fig2 = go.Figure(data=[go.Pie(
                labels=['Equipes Analisadas', 'Equipes Não Analisadas'],
                values=[total_equipes_distintas, equipes_nao_monitoradas],
                hole=0.6,
                marker=dict(colors=['#27AE60', '#E74C3C']),
                textinfo='value',
                textfont=dict(size=18, color="white")
            )])

            fig2.update_layout(
            title='ADERÊNCIA EQUIPES',
            title_x=0.5,
            annotations=[dict(
                text=f"<b>{porcentagem_abertura_turnos_equipes:.2f}%</b><br><span style='font-size:16px'>Total: {total_equipes_distintas_turnos}</span>",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=22, color='black', family='Arial Black')
            )],
            template="plotly_dark",
        )


            st.plotly_chart(fig2, use_container_width=True, key="fig2")
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)

        # Gráfico 3: Aderência Turnos
        with col3:
            turnos_não_analisados = total_turnos_distintos - total_equipes

            fig3 = go.Figure(data=[go.Pie(
                labels=['Turnos Analisados', 'Turnos Não Analisados'],
                values=[total_equipes, turnos_não_analisados],
                hole=0.6,
                marker=dict(colors=['#27AE60', '#E74C3C']),
                textinfo='value',
                textfont=dict(size=18, color="white")
            )])

            fig3.update_layout(
            title='ADERÊNCIA TURNOS',
            title_x=0.5,
            annotations=[dict(
                text=f"<b>{porcentagem_abertura_turnos:.2f}%</b><br><span style='font-size:16px'>Total: {total_turnos_distintos}</span>",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=22, color='black', family='Arial Black')
            )],
            template="plotly_dark",
        )

            st.plotly_chart(fig3, use_container_width=True, key="fig3")
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)

        # Gráfico 4: Aderência Pessoas
        with col4:
            # 🎯 ADERÊNCIA DE FILMAGEM POR PESSOAS

            # Turnos filtrados (já aplicados todos os filtros)
            turnos_filtrados_ids = df_turnos_filtrado['idtb_turnos'].unique()

            # Pessoas esperadas: idtb_pessoas vinculados aos turnos filtrados
            pessoas_esperadas = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(turnos_filtrados_ids)]
            todas_pessoas_turnos = pessoas_esperadas['idtb_pessoas'].dropna().unique()

            # Pessoas analisadas: idtb_pessoas vinculados aos turnos que aparecem em df_avulsa_filtrado['idturnos']
            turnos_filmados_ids = df_avulsa_filtrado['idturnos'].unique()
            pessoas_analisadas = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(turnos_filmados_ids)]
            pessoas_analisadas_ids = pessoas_analisadas['idtb_pessoas'].dropna().unique()

            # Pessoas não analisadas
            pessoas_pendentes_ids = [p for p in todas_pessoas_turnos if p not in pessoas_analisadas_ids]

            # Métricas
            total_analisados = len(pessoas_analisadas_ids)
            total_pendentes = len(pessoas_pendentes_ids)
            total_pessoas = len(todas_pessoas_turnos)

            # Validação
            if (total_analisados + total_pendentes) != total_pessoas:
                st.warning("⚠️ Atenção: Divergência na contagem de pessoas. Verifique os dados.")

            # Porcentagem
            porcentagem_analisadas = (total_analisados / total_pessoas) * 100 if total_pessoas > 0 else 0

            # Gráfico tipo Rosca
            fig_aderencia_pessoas = go.Figure(data=[go.Pie(
                labels=['Pessoas Analisadas', 'Pessoas Não Analisadas'],
                values=[total_analisados, total_pendentes],
                hole=0.6,
                marker=dict(colors=['#27AE60', '#E74C3C']),
                textinfo='value',
                textfont=dict(size=18, color="white")
            )])

            fig_aderencia_pessoas.update_layout(
                title='🎥 ADERÊNCIA PESSOAS',
                title_x=0.5,
                annotations=[dict(
                    text=f"<b>{porcentagem_analisadas:.2f}%</b><br><span style='font-size:16px'>Total: {total_pessoas}</span>",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=22, color='black', family='Arial Black')
                )],
                template="plotly_dark",
                height=450
            )

            # Exibir o gráfico
            st.plotly_chart(fig_aderencia_pessoas, use_container_width=True, key="fig_aderencia_pessoas")
            
            # --- INÍCIO DA MODIFICAÇÃO PARA MOSTRAR AMBAS AS LISTAS ---

            # Define o nome da coluna de ID e as colunas a serem exibidas
            coluna_id_pessoa = 'idtb_oper_pessoa'
            colunas_para_mostrar = ['nome', 'funcao_geral', 'dt_admissao']

            # Verifica se a coluna de ID existe no dataframe
            if coluna_id_pessoa in df_pessoas.columns:
                
                # Expansor para Pessoas Analisadas
                if any(pessoas_analisadas_ids):
                    nomes_analisados = df_pessoas[df_pessoas[coluna_id_pessoa].isin(pessoas_analisadas_ids)]
                    if not nomes_analisados.empty:
                        nomes_analisados_display = nomes_analisados[colunas_para_mostrar].reset_index(drop=True)
                        with st.expander(f"✅ Ver as {len(nomes_analisados_display)} Pessoas Analisadas"):
                            st.dataframe(nomes_analisados_display, use_container_width=True)

                # Expansor para Pessoas Não Analisadas
                if any(pessoas_pendentes_ids):
                    nomes_pendentes = df_pessoas[df_pessoas[coluna_id_pessoa].isin(pessoas_pendentes_ids)]
                    if not nomes_pendentes.empty:
                        nomes_pendentes_display = nomes_pendentes[colunas_para_mostrar].reset_index(drop=True)
                        with st.expander(f"❌ Ver as {len(nomes_pendentes_display)} Pessoas Não Analisadas"):
                            st.dataframe(nomes_pendentes_display, use_container_width=True)
            else:
                 st.error(f"Erro: A coluna de ID '{coluna_id_pessoa}' não foi encontrada. Verifique o script 'exporta_dados_monitoria_csv.py'.")

            # --- FIM DA MODIFICAÇÃO ---

            

        col1,col2 = st.columns(2)


        
        # --- Supondo que 'df_avulsa_filtrado' já foi carregado e as colunas 'col1' e 'col2' existem ---

        # 1. DEFINA A FUNÇÃO DE COR APENAS UMA VEZ, FORA DAS COLUNAS
        def cor_gradiente_refinada(valor, meta=80):
            # Garante que o valor esteja no intervalo 0-100 para evitar erros
            valor = max(0, min(100, valor))
            
            # Normaliza entre 0 (ruim) e 1 (ótimo)
            if valor >= meta:
                # Escala verde entre a meta e 100
                ratio = (valor - meta) / (100 - meta) if (100 - meta) > 0 else 1
                h = 0.33  # Verde
                s = 0.8 - (0.3 * ratio)
                v = 0.6 + (0.2 * ratio)
            else:
                # Escala vermelho-amarelado entre 0 e a meta
                ratio = valor / meta if meta > 0 else 0
                h = 0.0 + (0.12 * ratio) # Vai de Vermelho (0) para Amarelo/Laranja (0.12)
                s = 0.9
                v = 0.7 - (0.2 * (1 - ratio))
                
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f'rgb({int(r*255)}, {int(g*255)}, {int(b*255)})' # Opacidade não é necessária aqui

#----------------------------------------------------------------------------------------------------------------#
#-------------------------------------- GRÁFICO 1: ADERÊNCIA POR UNIDADE ----------------------------------------#
        #----------------------------------------------------------------------------------------------------------------#
        
        with col1:
            st.markdown(
                """
                <div style="text-align: center;">
                    <h3><strong>ADERÊNCIA FILMAGENS POR UNIDADE</strong></h3>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Agrupando por unidade
            contato_por_unidade = df_avulsa_filtrado.groupby(['unidade', 'gravou_atividade']).size().unstack(fill_value=0)

            # Garantindo colunas 'SIM' e 'NÃO'
            for col in ['SIM', 'NÃO']:
                if col not in contato_por_unidade.columns:
                    contato_por_unidade[col] = 0

            # Calculando taxa de contato
            contato_por_unidade['Total'] = contato_por_unidade['SIM'] + contato_por_unidade['NÃO']
            contato_por_unidade['TaxaContato'] = (contato_por_unidade['SIM'] / contato_por_unidade['Total']) * 100
            contato_por_unidade = contato_por_unidade.reset_index().sort_values('TaxaContato', ascending=False) # Ordena para melhor visualização

            # Aplicar coloração
            contato_por_unidade['Cor'] = contato_por_unidade['TaxaContato'].apply(cor_gradiente_refinada)

            # Gráfico de barras verticais
            fig_taxa = go.Figure()

            fig_taxa.add_trace(go.Bar(
                x=contato_por_unidade['unidade'],
                y=contato_por_unidade['TaxaContato'],
                marker_color=contato_por_unidade['Cor'],
                text=[f"{v:.1f}%" for v in contato_por_unidade['TaxaContato']],
                textposition='outside',
                textfont=dict(color='black', size=12), # Garante que o texto seja preto
                name='Taxa de Contato'
            ))

            # Linha de meta
            fig_taxa.add_trace(go.Scatter(
                x=contato_por_unidade['unidade'],
                y=[80] * len(contato_por_unidade),
                mode='lines',
                name='Meta 80%',
                line=dict(color='black', width=2, dash='dash')
            ))

            fig_taxa.update_layout(
                xaxis_title='',
                yaxis_title='',
                template='plotly_white', # 2. MUDANÇA PARA TEMA CLARO
                showlegend=True,
                height=500,
                margin=dict(t=60, l=50, r=50, b=100),
                font_color="black", # Agora isso combina com o template
                yaxis_range=[0, 110] # Garante espaço para o texto 'outside'
            )
            
            fig_taxa.update_xaxes(tickfont=dict(color='black'))
            fig_taxa.update_yaxes(showticklabels=False) # Esconde os valores do eixo Y para um visual mais limpo

            st.plotly_chart(fig_taxa, use_container_width=True, key="unidade_chart")
            st.markdown("<hr>", unsafe_allow_html=True)

#----------------------------------------------------------------------------------------------------------------#
#-------------------------------------- GRÁFICO 2: ADERÊNCIA POR SUPERVISOR -------------------------------------#
#----------------------------------------------------------------------------------------------------------------#
        with col2:
            st.markdown(
                """
                <div style="text-align: center;">
                    <h3><strong>ADERÊNCIA FILMAGENS POR SUPERVISOR</strong></h3>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Agrupando por supervisor
            contato_por_supervisor = df_avulsa_filtrado.groupby(['supervisor', 'gravou_atividade']).size().unstack(fill_value=0)

            # Garantindo colunas 'SIM' e 'NÃO'
            for col in ['SIM', 'NÃO']:
                if col not in contato_por_supervisor.columns:
                    contato_por_supervisor[col] = 0

            # Calculando taxa de contato
            contato_por_supervisor['Total'] = contato_por_supervisor['SIM'] + contato_por_supervisor['NÃO']
            contato_por_supervisor['TaxaContato'] = (contato_por_supervisor['SIM'] / contato_por_supervisor['Total']) * 100
            contato_por_supervisor = contato_por_supervisor.reset_index().sort_values('TaxaContato', ascending=False)

            # Aplicar coloração
            contato_por_supervisor['Cor'] = contato_por_supervisor['TaxaContato'].apply(cor_gradiente_refinada)

            # Gráfico de barras verticais
            fig_supervisor = go.Figure()

            fig_supervisor.add_trace(go.Bar(
                x=contato_por_supervisor['supervisor'],
                y=contato_por_supervisor['TaxaContato'],
                marker_color=contato_por_supervisor['Cor'],
                text=[f"{v:.1f}%" for v in contato_por_supervisor['TaxaContato']],
                textposition='outside',
                textfont=dict(color='black', size=12), # Garante que o texto seja preto
                name='Taxa de Contato'
            ))

            # Linha de meta
            fig_supervisor.add_trace(go.Scatter(
                x=contato_por_supervisor['supervisor'],
                y=[80] * len(contato_por_supervisor),
                mode='lines',
                name='Meta 80%',
                line=dict(color='black', width=2, dash='dash')
            ))

            fig_supervisor.update_layout(
                xaxis_title='',
                yaxis_title='',
                template='plotly_white', # 2. MUDANÇA PARA TEMA CLARO
                showlegend=True,
                height=500,
                margin=dict(t=60, l=50, r=50, b=100),
                font_color="black", # Agora isso combina com o template
                yaxis_range=[0, 110] # Garante espaço para o texto 'outside'
            )
            
            fig_supervisor.update_xaxes(tickfont=dict(color='black'))
            fig_supervisor.update_yaxes(showticklabels=False) # Esconde os valores do eixo Y

            st.plotly_chart(fig_supervisor, use_container_width=True, key="supervisor_chart")
            st.markdown("<hr>", unsafe_allow_html=True)
            
    with EVOLUCAO:  

        # 1. Contagem de equipes com turno por unidade
        equipes_turnos_por_unidade = df_turnos_filtrado.groupby('unidade')['num_operacional'].nunique().reset_index()
        equipes_turnos_por_unidade.columns = ['unidade', 'total_equipes_turno']

        # 2. Contagem de equipes analisadas (com filmagem) por unidade
        equipes_analisadas_por_unidade = df_avulsa_filtrado.drop_duplicates('equipe_real')
        equipes_analisadas_por_unidade = equipes_analisadas_por_unidade.groupby('unidade')['equipe_real'].nunique().reset_index()
        equipes_analisadas_por_unidade.columns = ['unidade', 'equipes_analisadas']

        # 3. Merge e cálculo da aderência
        aderencia_unidade = pd.merge(equipes_turnos_por_unidade, equipes_analisadas_por_unidade, on='unidade', how='left').fillna(0)
        aderencia_unidade['aderencia'] = (aderencia_unidade['equipes_analisadas'] / aderencia_unidade['total_equipes_turno']) * 100
        aderencia_unidade['aderencia'] = aderencia_unidade['aderencia'].clip(upper=100)  # Limite de 100%

        # 4. Criação dos velocímetros
        num_unidades = len(aderencia_unidade)
        fig = make_subplots(
            rows=1,
            cols=num_unidades,
            specs=[[{'type': 'indicator'}] * num_unidades],
            horizontal_spacing=0.05
        )

        for i, row in aderencia_unidade.iterrows():
            unidade = row['unidade']
            taxa = row['aderencia']

            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=taxa,
                title={
                    'text': f"{unidade}",
                    'font': {'size': 14, 'color': 'black'}
                },
                number={
                    'suffix': "%",
                    'font': {'size': 22, 'color': 'black'}
                },
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {
                        'color': "#2ECC71" if taxa >= 80 else "#E74C3C",
                        'thickness': 0.4
                    },
                    'steps': [
                        {'range': [0, 100], 'color': "#1f2c38"}  # Fundo neutro escuro
                    ],
                    'threshold': {
                        'line': {'color': "orange", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                },
                domain={'row': 0, 'column': i}
            ), row=1, col=i+1)

        # 5. Layout final do gráfico
        fig.update_layout(
            height=400,
            margin=dict(t=40, b=40),
            template='plotly_dark'
        )

        
        st.plotly_chart(fig, use_container_width=True)
        
#------------------------ grafico mensal ----------------------------------#        
        
        col1, col2, = st.columns(2)
        with col1:
            st.markdown("<hr>", unsafe_allow_html=True)
            
            # Garantindo que a coluna 'mes' seja criada e dados nulos sejam tratados
            gravou_atividade_sim['mes'] = gravou_atividade_sim['dt_inicio_serv'].dt.month
            gravou_atividade_nao['mes'] = gravou_atividade_nao['dt_inicio_serv'].dt.month
            gravou_atividade_sim = gravou_atividade_sim.dropna(subset=['mes'])
            gravou_atividade_nao = gravou_atividade_nao.dropna(subset=['mes'])

            # Sempre mostrar todos os meses (1 a 12) para o ano selecionado
            meses_do_ano = list(range(1, 13))

                    # Criando a coluna do mês
            gravou_atividade_sim['mes'] = gravou_atividade_sim['dt_inicio_serv'].dt.month
            gravou_atividade_nao['mes'] = gravou_atividade_nao['dt_inicio_serv'].dt.month

            # Garantindo que os valores sejam do ano filtrado
            gravou_atividade_sim_ano = gravou_atividade_sim[gravou_atividade_sim['dt_inicio_serv'].dt.year == ano_selecionado]
            gravou_atividade_nao_ano = gravou_atividade_nao[gravou_atividade_nao['dt_inicio_serv'].dt.year == ano_selecionado]

            # Agrupando os dados por mês
            sim_por_mes = gravou_atividade_sim_ano.groupby('mes').size()
            nao_por_mes = gravou_atividade_nao_ano.groupby('mes').size()

            # Somando os totais
            total_por_mes = sim_por_mes.add(nao_por_mes, fill_value=0)

            # Mantendo apenas os meses com dados
            meses_com_dados = total_por_mes[total_por_mes > 0].index.tolist()

            # Reindexando somente os meses com dados
            sim_por_mes = sim_por_mes.reindex(meses_com_dados, fill_value=0)
            nao_por_mes = nao_por_mes.reindex(meses_com_dados, fill_value=0)

            # Calculando percentuais
            porcentagem_sim = (sim_por_mes / (sim_por_mes + nao_por_mes).replace(0, 1)) * 100
            porcentagem_nao = (nao_por_mes / (sim_por_mes + nao_por_mes).replace(0, 1)) * 100

            # Criando o gráfico
            st.markdown(
                """
                <div style="text-align: center;">
                    <h4 style="font-size:18px;"><strong>GRAFICO DE EVOLUÇÃO MENSAL</strong></h4>
                </div>
                """,
                unsafe_allow_html=True
            )

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=meses_com_dados,
                y=sim_por_mes,
                name='Gravaram Atividade',
                marker_color='#27AE60',
                text=[f'{int(v)}\n({p:.1f}%)' for v, p in zip(sim_por_mes, porcentagem_sim)],
                textposition='outside',
                textfont=dict(color='black', size=14)
            ))

            fig.add_trace(go.Bar(
                x=meses_com_dados,
                y=nao_por_mes,
                name='Não Gravaram Atividade',
                marker_color='#E74C3C',
                text=[f'{int(v)}\n({p:.1f}%)' for v, p in zip(nao_por_mes, porcentagem_nao)],
                textposition='outside',
                textfont=dict(color='black', size=14)
            ))

            fig.update_layout(
                xaxis=dict(
                    tickmode='array',
                    tickvals=meses_com_dados,
                    ticktext=[f"Mês {m}" for m in meses_com_dados],
                    tickfont=dict(color='black', size=14)
                ),
                yaxis=dict(
                    tickfont=dict(color='black', size=14)
                ),
                barmode='group',
                template='plotly_white',  # Usa fundo claro
                title_x=0.5,
                legend_title='Status da Atividade',
                legend=dict(
                    font=dict(size=14, color='black'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                uniformtext_minsize=10,
                uniformtext_mode='hide',
                margin=dict(t=100, b=100, l=50, r=50)
            )

            st.plotly_chart(fig, use_container_width=True)


            # --- INÍCIO DA MODIFICAÇÃO 2 ---
            # Separadores e expansores agora usam a coluna 'equipe_display'
            st.markdown("<hr>", unsafe_allow_html=True)

            with st.expander("Ver Detalhes das Equipes que Não Gravaram"):
                st.write(gravou_atividade_nao_distinct[['unidade', 'equipe_display', 'dt_inicio_serv']])

            with st.expander("Ver Detalhes das Equipes que Gravaram"):
                st.write(gravou_atividade_sim_distinct[['unidade', 'equipe_display', 'dt_inicio_serv', 'monitor', 'supervisor']])

            st.markdown("<hr>", unsafe_allow_html=True)
            # --- FIM DA MODIFICAÇÃO 2 ---
            
#------------------------- 
        with col2:
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)
            # Agrupamento por mês (SIM)
            gravou_atividade_sim['mes'] = gravou_atividade_sim['dt_inicio_serv'].dt.month
            gravou_atividade_sim_monthly = gravou_atividade_sim.groupby('mes').size()
            gravou_atividade_sim_monthly = gravou_atividade_sim_monthly.reindex(sorted(meses_com_dados), fill_value=0)

            # Porcentagem SIM no mês
            total_equipes_mensal = gravou_atividade_sim_monthly + gravou_atividade_nao.groupby('mes').size().reindex(sorted(meses_com_dados), fill_value=0)
            porcentagem_sim = (gravou_atividade_sim_monthly / total_equipes_mensal.replace(0, 1)) * 100

            # Variações
            percentual_crescimento_total = gravou_atividade_sim_monthly.pct_change().fillna(0) * 100
            percentual_aderencia_sim = porcentagem_sim.diff().fillna(0)

            # Formatando os textos
            texto_qtd = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_crescimento_total)]
            texto_aderencia = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_aderencia_sim)]

            # --- Gráfico combinado ---

            
            # Cabeçalho
            st.markdown(
                """
                <div style="text-align: center; margin-top: 50px;">
                    <h4 style="font-size:18px;"><strong>EVOLUÇÃO DE QUANTIDADE E ADERÊNCIA MENSAL</strong></h4>
                    <p style="font-size:13px;color:#BDC3C7">Comparativo de análises absolutas e variação de % SIM mês a mês</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 🔹 Definição das variáveis (substitua pelas suas reais)
            meses = gravou_atividade_sim_monthly.index.tolist()
            valores_sim = gravou_atividade_sim_monthly.values
            valores_aderencia = percentual_aderencia_sim.values
            valores_total = total_equipes_mensal.values
            percentual_total = total_equipes_mensal.pct_change().fillna(0) * 100

            texto_qtd = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_crescimento_total)]
            texto_aderencia = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_aderencia_sim)]
            texto_total = [
                f"Total: {v} ({p:+.1f}%)" if i > 0 else f"Total: {v} (0%)"
                for i, (v, p) in enumerate(zip(valores_total, percentual_total))
            ]

            # 🔸 Criação da figura
            fig = go.Figure()

            # Linha 1 — Qtd SIM (Azul)
            fig.add_trace(go.Scatter(
                x=meses,
                y=valores_sim,
                mode='lines+markers+text',
                line=dict(color='blue', width=3),
                marker=dict(size=10),
                text=texto_qtd,
                textfont=dict(color='black'),
                textposition='top center',
                name='Qtd SIM',
                hoverinfo='x+y+text',
                showlegend=True
            ))
            for i in range(1, len(meses)):
                fig.add_trace(go.Scatter(
                    x=[meses[i-1], meses[i]],
                    y=[valores_sim[i-1], valores_sim[i]],
                    mode='lines',
                    line=dict(color='blue', width=3),
                    showlegend=False
                ))

            # Linha 2 — % Aderência SIM (Vermelha)
            fig.add_trace(go.Scatter(
                x=meses,
                y=valores_aderencia,
                mode='lines+markers+text',
                line=dict(color='red', width=3, dash='dash'),
                marker=dict(size=10),
                text=texto_aderencia,
                textfont=dict(color='black'),
                textposition='bottom center',
                yaxis='y2',
                name='% Aderência SIM',
                hoverinfo='x+y+text',
                showlegend=True
            ))
            for i in range(1, len(meses)):
                fig.add_trace(go.Scatter(
                    x=[meses[i-1], meses[i]],
                    y=[valores_aderencia[i-1], valores_aderencia[i]],
                    mode='lines',
                    line=dict(color='red', width=3, dash='dash'),
                    yaxis='y2',
                    showlegend=False
                ))

            # Linha 3 — Total Análises (Preto)
            fig.add_trace(go.Scatter(
                x=meses,
                y=valores_total,
                mode='lines+markers+text',
                line=dict(color='black', width=3, dash='dot'),
                marker=dict(size=10, symbol='circle'),
                text=texto_total,
                textfont=dict(color='black'),
                textposition='top center',
                name='Total Análises',
                hoverinfo='x+y+text',
                showlegend=True
            ))
            for i in range(1, len(meses)):
                fig.add_trace(go.Scatter(
                    x=[meses[i-1], meses[i]],
                    y=[valores_total[i-1], valores_total[i]],
                    mode='lines',
                    line=dict(color='black', width=3, dash='dot'),
                    showlegend=False
                ))

            # 🔸 Layout final
            fig.update_layout(
                template='plotly_white',
                height=500,
                xaxis=dict(
                    title='',
                    tickmode='array',
                    tickvals=meses,
                    ticktext=[f"Mês {m}" for m in meses]
                ),
                yaxis=dict(
                    title='',
                    showgrid=True
                ),
                yaxis2=dict(
                    title='',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                legend=dict(
                    title='Indicadores',
                    font=dict(size=12),
                    bordercolor='black',
                    borderwidth=1,
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode="x unified",
                margin=dict(t=60, b=40)
            )

            # Exibe o gráfico
            st.plotly_chart(fig, use_container_width=True)
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)

#-----------------------------------------------------------------------------
        
        # <<< NOVO TRECHO INICIA AQUI: Gráfico de Evolução Semanal >>>
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-top: 50px;">
                <h4 style="font-size:18px;"><strong>EVOLUÇÃO DE QUANTIDADE E ADERÊNCIA SEMANAL</strong></h4>
                <p style="font-size:13px;color:#BDC3C7">Comparativo de análises absolutas e variação de % SIM semana a semana</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Prepara os dados para o gráfico semanal
        gravou_atividade_sim_semanal = df_avulsa_filtrado[df_avulsa_filtrado['gravou_atividade'] == 'SIM']
        gravou_atividade_nao_semanal = df_avulsa_filtrado[df_avulsa_filtrado['gravou_atividade'] == 'NÃO']

        # Agrupamento por semana
        sim_por_semana = gravou_atividade_sim_semanal.groupby('semana').size()
        nao_por_semana = gravou_atividade_nao_semanal.groupby('semana').size()
        
        semanas_com_dados = sorted(list(set(sim_por_semana.index) | set(nao_por_semana.index)))
        sim_por_semana = sim_por_semana.reindex(semanas_com_dados, fill_value=0)
        nao_por_semana = nao_por_semana.reindex(semanas_com_dados, fill_value=0)

        # Cálculos para o gráfico
        total_equipes_semanal = sim_por_semana + nao_por_semana
        porcentagem_sim_semanal = (sim_por_semana / total_equipes_semanal.replace(0, 1)) * 100
        percentual_crescimento_sim_semanal = sim_por_semana.pct_change().fillna(0) * 100
        percentual_variacao_aderencia_semanal = porcentagem_sim_semanal.diff().fillna(0)
        percentual_total_semanal = total_equipes_semanal.pct_change().fillna(0) * 100

        # Variáveis para plotagem
        semanas = sim_por_semana.index.tolist()
        texto_qtd_semanal = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_crescimento_sim_semanal)]
        texto_aderencia_semanal = [f"{v:+.1f}%" if i > 0 else "0%" for i, v in enumerate(percentual_variacao_aderencia_semanal)]
        texto_total_semanal = [f"Total: {v} ({p:+.1f}%)" if i > 0 else f"Total: {v} (0%)" for i, (v, p) in enumerate(zip(total_equipes_semanal, percentual_total_semanal))]

        if semanas:
            fig_semanal = go.Figure()
            fig_semanal.add_trace(go.Scatter(x=semanas, y=sim_por_semana, mode='lines+markers+text', line=dict(color='blue', width=3), name='Qtd SIM', text=texto_qtd_semanal, textposition='top center', textfont=dict(color='black')))
            fig_semanal.add_trace(go.Scatter(x=semanas, y=percentual_variacao_aderencia_semanal, mode='lines+markers+text', line=dict(color='red', width=3, dash='dash'), name='% Aderência SIM', yaxis='y2', text=texto_aderencia_semanal, textposition='bottom center', textfont=dict(color='black')))
            fig_semanal.add_trace(go.Scatter(x=semanas, y=total_equipes_semanal, mode='lines+markers+text', line=dict(color='black', width=3, dash='dot'), name='Total Análises', text=texto_total_semanal, textposition='top center', textfont=dict(color='black')))
            
            fig_semanal.update_layout(
                template='plotly_white', height=500,
                xaxis=dict(title='Semana do Ano', tickmode='array', tickvals=semanas, ticktext=[f"Sem {s}" for s in semanas]),
                yaxis=dict(title='Quantidade', showgrid=True),
                yaxis2=dict(title='Variação % Aderência', overlaying='y', side='right', showgrid=False),
                legend=dict(title='Indicadores', orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified", margin=dict(t=80, b=40)
            )
            st.plotly_chart(fig_semanal, use_container_width=True)
        else:
            st.info("Não há dados semanais suficientes para exibir o gráfico de evolução.")
        # <<< NOVO TRECHO TERMINA AQUI >>>
    
    with EQUIPE_MONITORADAS:    
        
    
        # Dicionário de tipos de equipe
        # Dicionário de tipos de equipe
        tipos_equipe = {
            'Linha Viva': '7',
            'Linha Leve': '9',
            'Equipe Pesada': '8',
            'Moto': '4'
        }

        # Função para classificar as equipes
        def classificar_tipo_equipe(equipe):
            equipe = str(equipe).strip()
            if equipe.startswith('9'): return 'Linha Leve'
            elif equipe.startswith('8'): return 'Equipe Pesada'
            elif equipe.startswith('7'): return 'Linha Viva'
            elif equipe.startswith('4'): return 'Moto'
            else: return 'Outros'

        # Inicializa o dataframe vazio
        df_comparativo = pd.DataFrame()

        # Verifica se há dados para processar
        if not df_turnos_filtrado.empty:
            # 1. Pega todos os PREFIXOS distintos que abriram turno
            equipes_com_turno = df_turnos_filtrado[
                ['prefixo', 'num_operacional', 'equipe_display']
            ].drop_duplicates(subset=['prefixo'])

            # 2. Lista de identificadores das equipes que foram efetivamente analisadas
            prefixos_analisados = df_avulsa_filtrado['equipe_real'].unique()

            # 3. Classifica o status de cada equipe
            equipes_com_turno['Status'] = equipes_com_turno['num_operacional'].apply(
                lambda x: 'Analisada' if x in prefixos_analisados else 'Pendente de Análise'
            )
            
            # 4. Cria a coluna de exibição final com base na condição
            equipes_com_turno['Equipe'] = np.where(
                equipes_com_turno['Status'] == 'Analisada',
                equipes_com_turno['equipe_display'],
                equipes_com_turno['prefixo']
            )

            # 5. Classifica o tipo de equipe usando o prefixo (num_operacional)
            equipes_com_turno['TipoEquipe'] = equipes_com_turno['num_operacional'].apply(classificar_tipo_equipe)
            
            df_comparativo = equipes_com_turno

        # --- GERAÇÃO DOS GRÁFICOS ---

        # Criação das 4 colunas lado a lado
        col1, col2, col3, col4 = st.columns(4)
        colunas = [col1, col2, col3, col4]

        for idx, (tipo_nome, _) in enumerate(tipos_equipe.items()):
            with colunas[idx]:
                df_tipo = df_comparativo[df_comparativo['TipoEquipe'] == tipo_nome]

                labels = []
                parents = []
                values = []

                if not df_tipo.empty:
                    labels.append(tipo_nome)
                    parents.append("")
                    values.append(len(df_tipo))

                    status_unicos = sorted(df_tipo['Status'].unique())
                    
                    for status in status_unicos:
                        labels.append(status)
                        parents.append(tipo_nome)
                        df_status = df_tipo[df_tipo['Status'] == status]
                        values.append(len(df_status))
                        
                        # Adiciona as folhas (equipes individuais)
                        for equipe in df_status['Equipe']:
                            # CORREÇÃO APLICADA AQUI:
                            # Adiciona a equipe ao gráfico apenas se o nome não for nulo ou vazio.
                            # Isso remove as "fatias em branco".
                            if pd.notna(equipe) and str(equipe).strip():
                                labels.append(str(equipe))
                                parents.append(status)
                                values.append(1)

                    # --- LÓGICA DE CORES ---
                    status_color_map = {
                        'Analisada': '#27AE60',
                        'Pendente de Análise': '#91949e'
                    }
                    root_color = '#F08080'
                    leaf_color = '#c0c0c0'

                    marker_colors = []
                    for label in labels:
                        if label in status_color_map:
                            marker_colors.append(status_color_map[label])
                        elif label == tipo_nome:
                            marker_colors.append(root_color)
                        else:
                            marker_colors.append(leaf_color)

                    fig = go.Figure(go.Sunburst(
                        labels=labels,
                        parents=parents,
                        values=values,
                        branchvalues='total',
                        marker=dict(colors=marker_colors),
                        textfont=dict(color='black', size=16)
                    ))

                    fig.update_layout(
                        title=tipo_nome,
                        template="plotly_dark",
                        width=400,
                        height=400,
                        margin=dict(t=40, l=10, r=10, b=10),
                        font_color="black"
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Lógica para Download do Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Seleciona colunas relevantes para o download
                        df_tipo_download = df_tipo[['Equipe', 'Status', 'num_operacional']]
                        df_tipo_download.to_excel(writer, index=False, sheet_name=tipo_nome)
                    output.seek(0)

                    st.download_button(
                        label=f"📥 Baixar {tipo_nome}",
                        data=output,
                        file_name=f"equipes_{tipo_nome.lower().replace(' ', '_')}.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key=f"download_{tipo_nome}"
                    )
                    
                    # Separador visual entre os gráficos
                    st.markdown("<hr>", unsafe_allow_html=True)
                else:
                    # Caso não haja equipes daquele tipo, mostra uma mensagem
                    st.markdown(f"**{tipo_nome}**")
                    st.info(f"Nenhuma equipe do tipo '{tipo_nome}' encontrada nos filtros selecionados.")


        
#--------------------------------------------------------------------------------
        # Organizando os gráficos em duas colunas
        col1, col2 = st.columns(2)

        # --- INÍCIO DA MODIFICAÇÃO 4 ---
        # Agrupamento e cálculo geral usando 'equipe_display'
        df_equipe = df_avulsa_filtrado.groupby(['equipe_display', 'gravou_atividade']).size().unstack(fill_value=0)
        # --- FIM DA MODIFICAÇÃO 4 ---

        # Garantindo colunas sempre presentes
        for col in ['SIM', 'NÃO']:
            if col not in df_equipe.columns:
                df_equipe[col] = 0

        df_equipe = df_equipe.rename(columns={'SIM': 'Gravaram', 'NÃO': 'Não Gravaram'})
        df_equipe['Total'] = df_equipe['Gravaram'] + df_equipe['Não Gravaram']
        df_equipe['Taxa %'] = (df_equipe['Gravaram'] / df_equipe['Total']) * 100
                          
#------------------------------------------------------------------------------------------
        with col1:
            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:18px;"><strong>🔝 10 MELHORES EQUIPES POR TAXA DE FILMAGEM</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            melhores = df_equipe[df_equipe['Total'] >= 3].sort_values(by='Taxa %', ascending=False).head(10)
            altura_melhores = max(400, len(melhores) * 50)

            fig_melhores = go.Figure()

            fig_melhores.add_trace(go.Bar(
            x=melhores.index,
            y=melhores['Gravaram'],
            name='Gravaram',
            marker_color='#27AE60',
            text=[f"{v}<br>({p:.1f}%)" for v, p in zip(melhores['Gravaram'], melhores['Taxa %'])],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12),
            width=0.6
        ))


            fig_melhores.add_trace(go.Bar(
            x=melhores.index,
            y=melhores['Não Gravaram'],
            name='Não Gravaram',
            marker_color='#E74C3C',
            text=[str(v) if v > 0 else "" for v in melhores['Não Gravaram']],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12),
            width=0.6
        ))



            fig_melhores.update_layout(
            barmode='stack',
            template='plotly_white',
            height=altura_melhores,
            margin=dict(t=80, b=120, l=50, r=50),
            xaxis_title='Equipe',
            yaxis_title=None,  # <-- 1. TÍTULO REMOVIDO
            title="", 
            title_x=0.5,
            legend_title='Status da Atividade',
            legend=dict(font=dict(size=12), bordercolor='black', borderwidth=2),
            xaxis=dict(
                tickfont=dict(color='black', size=12)
            ),
            yaxis=dict(
                tickfont=dict(color='black', size=12),
                showticklabels=False  # <-- 2. VALORES DO EIXO REMOVIDOS
            )
        )


            st.plotly_chart(fig_melhores, use_container_width=True)
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)



    # ------------------- 10 PIORES -------------------
        with col2:
            st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:18px;"><strong>🔻 10 PIORES EQUIPES POR TAXA DE FILMAGEM</strong></h4>
                </div>
            """, unsafe_allow_html=True)

            piores = df_equipe[df_equipe['Total'] >= 3].sort_values(by='Taxa %', ascending=True).head(10)
            altura_piores = max(400, len(piores) * 50)

            fig_piores = go.Figure()

            # GRAVARAM
            fig_piores.add_trace(go.Bar(
            x=piores.index,
            y=piores['Gravaram'],
            name='Gravaram',
            marker_color='#27AE60',
            text=[f"{v}<br>({p:.1f}%)" for v, p in zip(piores['Gravaram'], piores['Taxa %'])],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12),  # branco para melhor contraste
            width=0.6
        ))


            # NÃO GRAVARAM
            fig_piores.add_trace(go.Bar(
                x=piores.index,
                y=piores['Não Gravaram'],
                name='Não Gravaram',
                marker_color='#E74C3C',
                text=[str(v) if v > 0 else "" for v in piores['Não Gravaram']],
                textposition='outside',
                textfont=dict(color='black', size=12),
                width=0.6
            ))

            # LAYOUT
            fig_piores.update_layout(
            barmode='stack',
            template='plotly_white',
            height=altura_piores,
            margin=dict(t=80, b=120, l=50, r=50),
            xaxis_title='Equipe',
            yaxis_title=None,  # <-- 1. TÍTULO REMOVIDO
            title="",
            title_x=0.5,
            legend_title='Status da Atividade',
            legend=dict(font=dict(size=12), bordercolor='black', borderwidth=2),
            xaxis=dict(
                tickfont=dict(color='black', size=12)
            ),
            yaxis=dict(
                tickfont=dict(color='black', size=12),
                showticklabels=False  # <-- 2. VALORES DO EIXO REMOVIDOS
            )
        )

            st.plotly_chart(fig_piores, use_container_width=True)
            # SEPARADOR
            st.markdown("<hr>", unsafe_allow_html=True)        
            
        # --- INÍCIO DA MODIFICAÇÃO 5 ---
        # Modificação na criação da tabela AgGrid
        
        # --- INÍCIO DA MODIFICAÇÃO 5 ---
        # Modificação na criação da tabela AgGrid
        
        # Criar colunas de semana (se ainda não existirem)
        if 'semana' not in df_avulsa_filtrado.columns:
            df_avulsa_filtrado['semana'] = df_avulsa_filtrado['dt_inicio_serv'].dt.isocalendar().week
        if 'semana' not in df_turnos_filtrado.columns:
            df_turnos_filtrado['semana'] = df_turnos_filtrado['dt_inicio'].dt.isocalendar().week

        # Pegando todas as semanas únicas
        semanas_unicas = sorted(
            set(df_avulsa_filtrado['semana'].unique()).union(set(df_turnos_filtrado['semana'].unique())))

        # --- INÍCIO DA NOVA LÓGICA DE EXIBIÇÃO ---
        # 1. Cria um DataFrame de mapeamento com todas as informações necessárias por equipe
        mapa_equipes_df = df_turnos_filtrado[
            ['num_operacional', 'equipe_display', 'prefixo']
        ].drop_duplicates(subset=['num_operacional']).set_index('num_operacional')

        # 2. Cria um conjunto de equipes que foram analisadas (têm dados em avulsa) para consulta rápida
        prefixos_analisados = set(df_avulsa_filtrado['equipe_real'].unique())
        # --- FIM DA NOVA LÓGICA DE EXIBIÇÃO ---

        # Pegando TODAS as equipes pelo prefixo
        todas_equipes_prefixo = df_turnos_filtrado['num_operacional'].unique()

        # Criando lista para armazenar os dados
        dados_tabela = []

        for equipe_prefixo in todas_equipes_prefixo:
            # 3. LÓGICA CONDICIONAL PARA O NOME DA EQUIPE
            nome_final_display = ""
            try:
                # Verifica se a equipe foi analisada em algum momento no período filtrado
                if equipe_prefixo in prefixos_analisados:
                    # Se foi analisada (avulsa), usa o nome sem o prefixo numérico (ex: MORO008M)
                    nome_final_display = mapa_equipes_df.loc[equipe_prefixo, 'equipe_display']
                else:
                    # Se só abriu turno (num_operacional), usa o prefixo da câmera
                    nome_final_display = mapa_equipes_df.loc[equipe_prefixo, 'prefixo']

                # Caso o prefixo ou nome seja nulo/vazio, usa o código da equipe como garantia
                if pd.isna(nome_final_display) or str(nome_final_display).strip() == "":
                    nome_final_display = equipe_prefixo
            except KeyError:
                # Fallback caso o prefixo não seja encontrado no mapa
                nome_final_display = equipe_prefixo
            
            linha = {'Equipe': nome_final_display}
            total_sim = 0
            total_nao = 0
            total_turnos_equipe = 0

            for semana in semanas_unicas:
                # Contar turnos distintos usando o prefixo
                turnos_distintos = df_turnos_filtrado[
                    (df_turnos_filtrado['num_operacional'] == equipe_prefixo) &
                    (df_turnos_filtrado['semana'] == semana)
                ]['idtb_turnos'].nunique()

                # Filtrar dados de filmagem usando o prefixo
                df_semana = df_avulsa_filtrado[
                    (df_avulsa_filtrado['equipe_real'] == str(equipe_prefixo)) &
                    (df_avulsa_filtrado['semana'] == semana)
                ]

                # Contar SIM e NÃO
                sim = len(df_semana[df_semana['gravou_atividade'] == 'SIM'])
                nao = len(df_semana[df_semana['gravou_atividade'] == 'NÃO'])

                # Formatar célula
                if turnos_distintos > 0:
                    if sim + nao > 0:
                        linha[f'Semana {semana}'] = f"SIM({sim}) NÃO({nao}) TURNOS({turnos_distintos})"
                    else:
                        linha[f'Semana {semana}'] = f"SEM FILMAGEM | TURNOS({turnos_distintos})"
                else:
                    linha[f'Semana {semana}'] = "SEM TURNOS"

                total_sim += sim
                total_nao += nao
                total_turnos_equipe += turnos_distintos

            # Calcular os indicadores
            total_monitorado = total_sim + total_nao
            pct_sim_monitorado = total_sim / total_monitorado if total_monitorado > 0 else 0
            pct_turnos_analisados = total_monitorado / total_turnos_equipe if total_turnos_equipe > 0 else 0

            # Adicionar colunas
            linha['Total SIM'] = total_sim
            linha['Total NÃO'] = total_nao
            linha['% SIM/NÃO'] = f"{pct_sim_monitorado:.0%}"
            linha['Total Turnos'] = total_turnos_equipe
            linha['% Turnos Analisados'] = f"{pct_turnos_analisados:.0%}"

            dados_tabela.append(linha)

        # Criar DataFrame final e ordenar colunas
        tabela_final = pd.DataFrame(dados_tabela)
        if not tabela_final.empty:
            colunas_ordenadas = (
                ['Equipe'] +
                [f'Semana {semana}' for semana in semanas_unicas] +
                ['Total SIM', 'Total NÃO', '% SIM/NÃO', 'Total Turnos', '% Turnos Analisados']
            )
            # Garante que todas as colunas existam antes de tentar reordenar
            colunas_existentes = [col for col in colunas_ordenadas if col in tabela_final.columns]
            tabela_final = tabela_final[colunas_existentes]

        # --- FIM DA MODIFICAÇÃO 5 ---

        # Configuração do AgGrid (sem alterações)
        gb = GridOptionsBuilder.from_dataframe(tabela_final)
        cellstyle_jscode = JsCode("""
            function(params) {
                if (params.value.includes('SEM TURNOS')) {
                    return {backgroundColor: '#7F8C8D', color: 'white'};
                }
                else if (params.value.includes('SEM FILMAGEM')) {
                    return {backgroundColor: '#F39C12', color: 'white'};
                }
                else if (params.value.includes('SIM(') && params.value.includes('TURNOS(')) {
                    try {
                        const parts = params.value.split(')');
                        const sim = parseInt(parts[0].split('(')[1]);
                        const turnos = parseInt(parts[2].split('(')[1]);
                        const pct = sim/turnos;
                        const red = Math.floor(255 * (1 - pct));
                        const green = Math.floor(255 * pct);
                        return {backgroundColor: `rgb(${red}, ${green}, 0)`, color: 'black'};
                    } catch {
                        return null;
                    }
                }
                return null;
            }
            """)

        for semana in semanas_unicas:
                gb.configure_column(f'Semana {semana}', cellStyle=cellstyle_jscode)

        gb.configure_default_column(
            resizable=True,
            filterable=True,
            sortable=True,
            editable=False,
            wrapText=True,
            autoHeight=True
        )
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_selection(selection_mode='single', use_checkbox=True)
        grid_options = gb.build()

        grid_response = AgGrid(
            tabela_final,
            gridOptions=grid_options,
            height=800,
            width='100%',
            theme='streamlit',
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}}
        )

        # Legenda e download (sem alterações)
        st.markdown(
            """
            <div style="margin-top: 20px;">
                <p><strong>Legenda:</strong></p>
                <p><span style="background: linear-gradient(to right, red, green); color: black; padding: 2px 5px;">Gradiente</span> - % Filmado/Turnos (vermelho=0%, verde=100%)</p>
                <p><span style="background-color: #F39C12; color: white; padding: 2px 5px;">Laranja</span> - Turnos abertos mas sem filmagem</p>
                <p><span style="background-color: #7F8C8D; color: white; padding: 2px 5px;">Cinza</span> - Sem turnos abertos</p>
                <p><strong>% SIM/NÃO</strong>: Percentual de SIM em relação aos monitorados (SIM+NÃO)</p>
                <p><strong>% Turnos Analisados</strong>: Percentual de turnos que foram monitorados</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        @st.cache_data
        def convert_df_to_excel(df):
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Dados')
                    workbook = writer.book
                    worksheet = writer.sheets['Dados']

                    format_laranja = workbook.add_format({'bg_color': '#F39C12', 'font_color': 'white'})
                    format_cinza = workbook.add_format({'bg_color': '#7F8C8D', 'font_color': 'white'})

                    for col in range(1, len(semanas_unicas) + 1):
                        worksheet.conditional_format(1, col, len(df), col, {
                            'type': 'text', 'criteria': 'containing',
                            'value': 'SEM TURNOS', 'format': format_cinza
                        })
                        worksheet.conditional_format(1, col, len(df), col, {
                            'type': 'text', 'criteria': 'containing',
                            'value': 'SEM FILMAGEM', 'format': format_laranja
                        })
                output.seek(0)
                return output.getvalue()

        excel_data = convert_df_to_excel(tabela_final)
        st.download_button(
            label="📥 Baixar em Excel (.xlsx)",
            data=excel_data,
            file_name='evolucao_semanal_indicadores.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    with PESSOAS:
        # Criar coluna de semana no df_turnos e df_avulsa
        # Filtrar df_turnos_pessoas para manter só os turnos filtrados (em df_turnos_filtrado)
        # Filtrar turnos_pessoas com base nos turnos filtrados
        df_turnos_filtrados_ids = df_turnos_filtrado['idtb_turnos'].unique()
        df_turnos_pessoas_filtrado = df_turnos_pessoas[df_turnos_pessoas['idtb_turnos'].isin(df_turnos_filtrados_ids)]

        # Renomear idturnos para idtb_turnos, se necessário
        if 'idturnos' in df_avulsa_filtrado.columns:
            df_avulsa_filtrado.rename(columns={'idturnos': 'idtb_turnos'}, inplace=True)

        # Merge para trazer gravou_atividade e dt_inicio_serv
        df_merged = df_turnos_pessoas_filtrado.merge(
            df_avulsa_filtrado[['idtb_turnos', 'gravou_atividade', 'dt_inicio_serv']],
            on='idtb_turnos',
            how='left'
        )

        # Adiciona unidade (do turno)
        df_merged = df_merged.merge(
            df_turnos_filtrado[['idtb_turnos', 'unidade']],
            on='idtb_turnos',
            how='left'
        )

        # Adiciona função da pessoa
        df_merged = df_merged.merge(
            df_pessoas[['nome', 'funcao_geral']],
            on='nome',
            how='left'
        )

        # Limpeza final
        df_merged = df_merged[['nome', 'funcao_geral', 'unidade', 'gravou_atividade', 'dt_inicio_serv']].drop_duplicates()
        df_merged = df_merged.sort_values(by=['nome', 'dt_inicio_serv'])
        
        # Mostrar os dados
        st.write("### Pessoas que abriram turno e status de gravação (com filtros aplicados)")
        st.dataframe(df_merged)
        
    #-----------------------------------------------------------------------------------------------------------------------------
        #-----------------------------------------------------------------------------------------------------------------------------
        # Resumo por pessoa
        st.markdown("""
                <div style="text-align: center;">
                    <h4 style="font-size:22px;"><strong> ADERÊNCIA POR PESSOAS QUE GRAVARAM A ATIVIDADE</strong></h4>
                </div>
            """, unsafe_allow_html=True)

        # VERIFICAÇÃO: Checa se há dados de filmagem para calcular o resumo
        if df_merged.empty or df_merged['gravou_atividade'].dropna().empty:
            st.info("Sem informação de filmagem no banco de dados para os filtros selecionados.")
        else:
            df_resumo = df_merged.groupby(['nome','funcao_geral','unidade', 'gravou_atividade']).size().unstack(fill_value=0)

            # VERIFICAÇÃO: Garante que as colunas SIM e NÃO existam antes de fazer cálculos
            if 'SIM' not in df_resumo.columns:
                df_resumo['SIM'] = 0
            if 'NÃO' not in df_resumo.columns:
                df_resumo['NÃO'] = 0

            # Calcula o total para evitar divisão por zero
            total_atividades = df_resumo['SIM'] + df_resumo['NÃO']
            
            # Calcular a coluna ADERÊNCIA em % com segurança
            # np.where(condição, valor se verdadeiro, valor se falso)
            df_resumo['% ADERÊNCIA'] = np.where(
                total_atividades > 0, 
                (df_resumo['SIM'] / total_atividades) * 100, 
                0
            )

            # Arredondar para 2 casas decimais
            df_resumo['% ADERÊNCIA'] = df_resumo['% ADERÊNCIA'].round(2)

            # Formatar com o símbolo de porcentagem
            df_resumo['% ADERÊNCIA'] = df_resumo['% ADERÊNCIA'].astype(str) + '%'

            # Mostrar o resultado
            st.dataframe(df_resumo)  
        
        

# Chamada principal
if __name__ == "__main__":
    app()