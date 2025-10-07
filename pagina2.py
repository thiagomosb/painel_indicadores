import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np 
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import subprocess
import os
from streamlit_echarts import st_echarts
import numpy as np
import streamlit as st
import pandas as pd
from io import BytesIO


# Filtros na barra lateral (Sidebar)


def app():
    """Função principal da Página 2"""

    # Inicializa no session_state se não existir
    if "ultima_atualizacao" not in st.session_state:
        st.session_state.ultima_atualizacao = None

    # Botão para voltar ao menu na sidebar
    with st.sidebar:
        st.logo('https://www.dolpengenharia.com.br/wp-content/uploads/2021/01/logotipo-definitivo-250614.png')

        # Botão de atualização
        if st.sidebar.button("🔄 Atualizar dados", key="atualizar_pagina2"):
            try:
                subprocess.run(["python", "banco_dados_rdo.py"], check=True)
                st.session_state.ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                st.sidebar.success(f"Dados atualizados em {st.session_state.ultima_atualizacao}")
            except Exception as e:
                st.sidebar.error(f"Erro ao atualizar: {e}")

        # Mostrar a última atualização, mesmo após recarregar
        if st.session_state.ultima_atualizacao:
            st.sidebar.info(f"Última atualização: {st.session_state.ultima_atualizacao}")

            

        # Carrega dados evitando o DtypeWarning
            df = pd.read_csv("turnos_eventos_fim_rdo.csv", low_memory=False)

            # Converte data
            df["data_turno"] = pd.to_datetime(df["data_turno"], errors="coerce").dt.date

   

#--------------------- MONITORAMENTO - TURNO POR RDO ------------#


    df = pd.read_csv("turnos_eventos_fim_rdo.csv")
    df["data_turno"] = pd.to_datetime(df["data_turno"]).dt.date

    # Dicionário de regionais e unidades
    regionais_unidades = {
        "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"],
        "REGIONAL RIO VERDE": ["RIO VERDE - GO"],
        "REGIONAL TO": ["PALMAS - TO"],
        "REGIONAL MT": ["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]
    }

    # Filtros de data
    # Pega datas mínimas e máximas
    min_date = df["data_turno"].min()
    max_date = df["data_turno"].max()  # Último dia disponível

    # Filtro de data unificado (range)
    data_selecionada = st.sidebar.date_input(
        "Período",
        value=(max_date, max_date),  # começa e termina no último dia por padrão
        min_value=min_date,
        max_value=max_date
    )

    # Garante que seja uma tupla (início, fim)
    if isinstance(data_selecionada, tuple):
        data_inicio, data_fim = data_selecionada
    else:
        data_inicio = data_fim = data_selecionada


    # Seleção múltipla de Regionais
    regionais_disponiveis = list(regionais_unidades.keys())
    regionais_selecionadas = st.sidebar.multiselect(
        "Selecione a(s) Regional(is)",
        options=regionais_disponiveis,
        default=regionais_disponiveis
    )

    # Unidades combinadas de todas as regionais selecionadas
    unidades_da_regional = []
    for reg in regionais_selecionadas:
        unidades_da_regional.extend(regionais_unidades.get(reg, []))

    # Seleção múltipla de Unidades dentro das Regionais selecionadas
    unidades_selecionadas = st.sidebar.multiselect(
        "Selecione as unidades (padrão: todas)",
        options=unidades_da_regional,
        default=unidades_da_regional
    )

    # Se nenhuma unidade selecionada, usar todas da regional
    if not unidades_selecionadas:
        unidades_selecionadas = unidades_da_regional
        st.sidebar.warning("Nenhuma unidade selecionada - mostrando todas por padrão")

    # Filtrar somente os dois tipos desejados
    tipos_filtrados = [
        "EPS - EQUIPE PESADA DE SERVIÇOS",
        "EPLV - EQUIPE LINHA VIVA"
    ]

    tipos_selecionados = st.sidebar.multiselect(
        "Selecione tipo",
        options=tipos_filtrados,
        default=tipos_filtrados
    )

    # Agora pegar só prefixos desses tipos
    prefixos_disponiveis = sorted(
        df[df["tipo"].isin(tipos_filtrados)]["descricao_tipo_prefixo"].dropna().unique()
    )

    prefixos_selecionados = st.sidebar.multiselect(
        "Selecione tipos de prefixo",
        options=prefixos_disponiveis,
        default=prefixos_disponiveis
    )


    # Aplicar filtros no dataframe
    df_filtrado = df[
    (df["data_turno"] >= data_inicio) &
    (df["data_turno"] <= data_fim) &
    (df["unidade"].isin(unidades_selecionadas)) &
    (df["descricao_tipo_prefixo"].isin(prefixos_selecionados)) &
    (df["tipo"].isin(tipos_selecionados))
]

    # Resto do seu código aqui ...

    total_equipes_dia = df_filtrado.groupby("data_turno")["idtb_equipes"].nunique().reset_index()
    total_equipes_dia.rename(columns={"idtb_equipes": "Total Equipes"}, inplace=True)

    rdo_dia = (
        df_filtrado[df_filtrado["evento"] == "FIM DO RDO"]
        .groupby("data_turno")
        .size()
        .reset_index(name="Total RDO")
    )
    
    #-------------------------------------- rdo geral -----------------------------------------3
    
    st.markdown(
                    """
                    <h2 style='text-align: center; 
                            font-size: 28px; 
                            font-weight: bold; 
                            color: #2E86C1;'>
                             ADERÊNCIA DIA GERAL - RDO
                    </h2>
                    """,
                    unsafe_allow_html=True
                )

    df_grafico = pd.merge(total_equipes_dia, rdo_dia, on="data_turno", how="left").fillna(0)
    df_grafico["Total RDO"] = df_grafico["Total RDO"].astype(int)

    # Preparar dados para o gráfico echarts
    datas = df_grafico["data_turno"].astype(str).tolist()
    total_equipes = df_grafico["Total Equipes"].tolist()
    total_rdo = df_grafico["Total RDO"].tolist()

    option = option = {
    "title": {"text": ""},
    "tooltip": {"trigger": "axis"},
    "legend": {"data": ["Total Equipes", "Total RDO"]},
    "toolbox": {"show": True, "feature": {"saveAsImage": {}}},
    "dataZoom": [
        {
            "type": "slider",
            "start": 0,
            "end": min(100, (25 / len(datas)) * 100),
            "bottom": 10,
            "height": 20,
            "handleSize": "100%",
            "handleStyle": {"color": "#aaa"}
        },
        {
            "type": "inside",
            "start": 0,
            "end": min(100, (25 / len(datas)) * 100)
        }
    ],
    "xAxis": {
        "type": "category",
        "data": datas,
        "axisLabel": {"rotate": 25, "interval": 0, "color": "black"}
    },
    "yAxis": {"type": "value", "name": ""},
    "series": [
        {
            "name": "Total Equipes",
            "type": "bar",
            "data": total_equipes,
            "itemStyle": {"color": "royalblue"},
            "label": {"show": True, "position": "top", "color": "black"}
        },
        {
            "name": "Total RDO",
            "type": "bar",
            "data": total_rdo,
            "itemStyle": {"color": "firebrick"},
            "label": {"show": True, "position": "top", "color": "black"}
        }
    ]
}




    st_echarts(options=option, height="500px")
    ########################## grafico por regional ##################
    st.markdown(
                    """
                    <h2 style='text-align: center; 
                            font-size: 28px; 
                            font-weight: bold; 
                            color: #2E86C1;'>
                             ADERÊNCIA REGIONAL - RDO
                    </h2>
                    """,
                    unsafe_allow_html=True
                )
    # Dicionário de regionais e unidades (igual ao seu)
    # Mapear unidades para regional (mesma lógica do seu filtro)
    regionais_unidades = {
        "REGIONAL MORRINHOS": ["MORRINHOS - GO", "CALDAS NOVAS - GO", "ITUMBIARA - GO", "PIRES DO RIO - GO", "CATALÃO - GO"],
        "REGIONAL RIO VERDE": ["RIO VERDE - GO"],
        "REGIONAL TO": ["PALMAS - TO"],
        "REGIONAL MT": ["CUIABÁ - MT", "VÁRZEA GRANDE - MT"]
    }
    mapa_unidade_regional = {uni: reg for reg, unidades in regionais_unidades.items() for uni in unidades}
    df_filtrado["regional"] = df_filtrado["unidade"].map(mapa_unidade_regional)

    # Agrupar por regional
    total_equipes_reg = (
        df_filtrado.groupby("regional")["idtb_equipes"]
        .nunique()
        .reset_index(name="Total Equipes")
    )

    total_rdo_reg = (
        df_filtrado[df_filtrado["evento"] == "FIM DO RDO"]
        .groupby("regional")
        .size()
        .reset_index(name="Total RDO")
    )

    # Juntar os dois
    df_regional = pd.merge(total_equipes_reg, total_rdo_reg, on="regional", how="left").fillna(0)
    df_regional["Total RDO"] = df_regional["Total RDO"].astype(int)

    # Preparar dados para gráfico
    regionais = df_regional["regional"].tolist()
    total_equipes = df_regional["Total Equipes"].tolist()
    total_rdo = df_regional["Total RDO"].tolist()

    option = {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Total Equipes", "Total RDO"]},
        "toolbox": {"show": True, "feature": {"saveAsImage": {}}},
        "xAxis": {
            "type": "category",
            "data": regionais,
            "axisLabel": {"rotate": 0, "color": "black"}
        },
        "yAxis": {
            "type": "value",
            "name": ""
        },
        "series": [
            {
                "name": "Total Equipes",
                "type": "bar",
                "data": total_equipes,
                "itemStyle": {"color": "royalblue"},
                "label": {"show": True, "position": "top", "color": "black"}
            },
            {
                "name": "Total RDO",
                "type": "bar",
                "data": total_rdo,
                "itemStyle": {"color": "firebrick"},
                "label": {"show": True, "position": "top", "color": "black"}
            }
        ]
    }

    st_echarts(options=option, height="500px")


######################## grafico por unidade ##########################
    st.markdown(
                        """
                        <h2 style='text-align: center; 
                                font-size: 28px; 
                                font-weight: bold; 
                                color: #2E86C1;'>
                                ADERÊNCIA UNIDADE - RDO
                        </h2>
                        """,
                        unsafe_allow_html=True
                    )
    # Agrupar por unidade
    total_equipes_unid = (
        df_filtrado.groupby("unidade")["idtb_equipes"]
        .nunique()
        .reset_index(name="Total Equipes")
    )

    total_rdo_unid = (
        df_filtrado[df_filtrado["evento"] == "FIM DO RDO"]
        .groupby("unidade")
        .size()
        .reset_index(name="Total RDO")
    )

    # Juntar os dois
    df_unidade = pd.merge(total_equipes_unid, total_rdo_unid, on="unidade", how="left").fillna(0)
    df_unidade["Total RDO"] = df_unidade["Total RDO"].astype(int)

    # Preparar dados para gráfico
    unidades = df_unidade["unidade"].tolist()
    total_equipes = df_unidade["Total Equipes"].tolist()
    total_rdo = df_unidade["Total RDO"].tolist()

    option = {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Total Equipes", "Total RDO"]},
        "toolbox": {"show": True, "feature": {"saveAsImage": {}}},
        "xAxis": {
            "type": "category",
            "data": unidades,
            "axisLabel": {"rotate": 45, "color": "black"}
        },
        "yAxis": {
            "type": "value",
            "name": ""
        },
        "series": [
            {
                "name": "Total Equipes",
                "type": "bar",
                "data": total_equipes,
                "itemStyle": {"color": "royalblue"},
                "label": {"show": True, "position": "top", "color": "black"}
            },
            {
                "name": "Total RDO",
                "type": "bar",
                "data": total_rdo,
                "itemStyle": {"color": "firebrick"},
                "label": {"show": True, "position": "top", "color": "black"}
            }
        ]
    }

    st_echarts(options=option, height="600px")


#################### grafico cidade ###################

    st.markdown(
                        """
                        <h2 style='text-align: center; 
                                font-size: 28px; 
                                font-weight: bold; 
                                color: #2E86C1;'>
                                ADERÊNCIA CIDADE - RDO
                        </h2>
                        """,
                        unsafe_allow_html=True
                    )

    # Agrupar por cidade
    total_equipes_cidade = (
        df_filtrado.groupby("cidade")["idtb_equipes"]
        .nunique()
        .reset_index(name="Total Equipes")
    )

    total_rdo_cidade = (
        df_filtrado[df_filtrado["evento"] == "FIM DO RDO"]
        .groupby("cidade")
        .size()
        .reset_index(name="Total RDO")
    )

    # Juntar os dois
    df_cidade = pd.merge(total_equipes_cidade, total_rdo_cidade, on="cidade", how="left").fillna(0)
    df_cidade["Total RDO"] = df_cidade["Total RDO"].astype(int)

    # Preparar dados para gráfico
    cidades = df_cidade["cidade"].tolist()
    total_equipes = df_cidade["Total Equipes"].tolist()
    total_rdo = df_cidade["Total RDO"].tolist()

    option = {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Total Equipes", "Total RDO"]},
        "toolbox": {"show": True, "feature": {"saveAsImage": {}}},
        "xAxis": {
            "type": "category",
            "data": cidades,
            "axisLabel": {"rotate": 45, "color": "black"}
        },
        "yAxis": {
            "type": "value",
            "name": ""
        },
        "series": [
            {
                "name": "Total Equipes",
                "type": "bar",
                "data": total_equipes,
                "itemStyle": {"color": "royalblue"},
                "label": {"show": True, "position": "top", "color": "black"}
            },
            {
                "name": "Total RDO",
                "type": "bar",
                "data": total_rdo,
                "itemStyle": {"color": "firebrick"},
                "label": {"show": True, "position": "top", "color": "black"}
            }
        ]
    }

    st_echarts(options=option, height="600px")


    
    ##################### tabela ######################
    
    
    
      # Criar coluna Equipe concatenando num_operacional + descricao_tipo_prefixo
    df_filtrado["Equipe"] = df_filtrado["num_operacional"].astype(str) + df_filtrado["prefixo"].astype(str)

    # Criar coluna para saber se fez RDO
    df_filtrado["Fez RDO"] = df_filtrado["evento"] == "FIM DO RDO"

    # Agrupar por Unidade, Equipe, Cidade e Data e identificar se fez RDO
    tabela = (
        df_filtrado.groupby(["unidade", "Equipe", "cidade", "data_turno"])["Fez RDO"]
        .max()
        .reset_index()
    )

    tabela["Fez RDO"] = tabela["Fez RDO"].map({True: "Sim", False: "Não"})

    tabela = tabela.rename(columns={
        "unidade": "Unidade",
        "cidade": "Cidade",
        "data_turno": "Data"
    })

    st.dataframe(tabela.sort_values(by=["Data", "Unidade", "Equipe"]), height=500)


if __name__ == "__main__":
    app()
