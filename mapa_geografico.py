import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import streamlit as st

def criar_dados_unidades():
    """
    Cria os dados das unidades (cidades) com coordenadas baseado no projeto.
    """
    unidades_dados = [
        # Goiás - Regional Morrinhos
        {'unidade': 'MORRINHOS - GO', 'cidade': 'MORRINHOS', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -17.7331, 'lon': -49.0978, 'regional': 'REGIONAL MORRINHOS'},
        {'unidade': 'CALDAS NOVAS - GO', 'cidade': 'CALDAS NOVAS', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -17.7747, 'lon': -48.6247, 'regional': 'REGIONAL MORRINHOS'},
        {'unidade': 'ITUMBIARA - GO', 'cidade': 'ITUMBIARA', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -18.4192, 'lon': -49.2150, 'regional': 'REGIONAL MORRINHOS'},
        {'unidade': 'PIRES DO RIO - GO', 'cidade': 'PIRES DO RIO', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -17.2998, 'lon': -48.2798, 'regional': 'REGIONAL MORRINHOS'},
        {'unidade': 'CATALÃO - GO', 'cidade': 'CATALÃO', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -18.1662, 'lon': -47.9469, 'regional': 'REGIONAL MORRINHOS'},
        
        # Goiás - Regional Rio Verde
        {'unidade': 'RIO VERDE - GO', 'cidade': 'RIO VERDE', 'estado': 'GO', 'estado_nome': 'Goiás', 'lat': -17.7944, 'lon': -50.9264, 'regional': 'REGIONAL RIO VERDE'},
        
        # Tocantins
        {'unidade': 'PALMAS - TO', 'cidade': 'PALMAS', 'estado': 'TO', 'estado_nome': 'Tocantins', 'lat': -10.1689, 'lon': -48.3317, 'regional': 'REGIONAL TO'},
        
        # Mato Grosso
        {'unidade': 'CUIABÁ - MT', 'cidade': 'CUIABÁ', 'estado': 'MT', 'estado_nome': 'Mato Grosso', 'lat': -15.6014, 'lon': -56.0979, 'regional': 'REGIONAL MT'},
        {'unidade': 'VÁRZEA GRANDE - MT', 'cidade': 'VÁRZEA GRANDE', 'estado': 'MT', 'estado_nome': 'Mato Grosso', 'lat': -15.6467, 'lon': -56.1326, 'regional': 'REGIONAL MT'}
    ]
    
    return pd.DataFrame(unidades_dados)

def carregar_geojson_estados():
    """
    Carrega os dados GeoJSON dos estados se disponíveis.
    """
    try:
        import os
        geojson_path = '/home/ubuntu/geojson_estados'
        
        if not os.path.exists(geojson_path):
            return None
            
        estados_geojson = {}
        
        # Carregar Goiás
        if os.path.exists(f'{geojson_path}/br_go.json'):
            with open(f'{geojson_path}/br_go.json', 'r', encoding='utf-8') as f:
                estados_geojson['GO'] = json.load(f)
        
        # Carregar Mato Grosso
        if os.path.exists(f'{geojson_path}/br_mt.json'):
            with open(f'{geojson_path}/br_mt.json', 'r', encoding='utf-8') as f:
                estados_geojson['MT'] = json.load(f)
        
        # Carregar Tocantins
        if os.path.exists(f'{geojson_path}/br_to.json'):
            with open(f'{geojson_path}/br_to.json', 'r', encoding='utf-8') as f:
                estados_geojson['TO'] = json.load(f)
        
        return estados_geojson if estados_geojson else None
        
    except Exception as e:
        print(f"Erro ao carregar GeoJSON: {e}")
        return None

def criar_mapa_geografico_empresa(df_filtrado=None):
    """
    Cria o mapa geográfico da empresa mostrando estados e unidades.
    
    Args:
        df_filtrado: DataFrame filtrado do projeto principal (opcional)
    """
    # Usar dados das unidades
    df_unidades = criar_dados_unidades()
    
    # Se há dados filtrados, usar apenas as unidades que aparecem nos dados
    if df_filtrado is not None and not df_filtrado.empty and 'unidade' in df_filtrado.columns:
        unidades_ativas = df_filtrado['unidade'].unique()
        df_unidades = df_unidades[df_unidades['unidade'].isin(unidades_ativas)]
    
    if df_unidades.empty:
        st.warning("Nenhuma unidade encontrada para exibir no mapa.")
        return None
    
    # Tentar carregar dados GeoJSON dos estados
    estados_geojson = carregar_geojson_estados()
    
    # Criar figura
    fig = go.Figure()
    
    # Se temos dados GeoJSON, adicionar os estados como polígonos azuis
    if estados_geojson:
        cores_estados = {'GO': '#4472C4', 'MT': '#4472C4', 'TO': '#4472C4'}  # Azul como na imagem
        
        for estado_sigla, geojson_data in estados_geojson.items():
            if estado_sigla in df_unidades['estado'].values:
                try:
                    # Processar geometria do GeoJSON
                    if geojson_data.get('type') == 'FeatureCollection':
                        for feature in geojson_data.get('features', []):
                            geometry = feature.get('geometry', {})
                            
                            if geometry.get('type') == 'Polygon':
                                coords = geometry['coordinates'][0]
                                lons = [coord[0] for coord in coords]
                                lats = [coord[1] for coord in coords]
                                
                                fig.add_trace(go.Scattergeo(
                                    lon=lons,
                                    lat=lats,
                                    mode='lines',
                                    fill='toself',
                                    fillcolor=cores_estados[estado_sigla],
                                    line=dict(color='white', width=1),
                                    opacity=0.6,
                                    name=df_unidades[df_unidades['estado'] == estado_sigla]['estado_nome'].iloc[0],
                                    hovertemplate=f'<b>{df_unidades[df_unidades["estado"] == estado_sigla]["estado_nome"].iloc[0]}</b><extra></extra>',
                                    showlegend=True
                                ))
                                break  # Usar apenas o primeiro polígono principal
                            
                            elif geometry.get('type') == 'MultiPolygon':
                                # Para MultiPolygon, usar o maior polígono
                                largest_polygon = max(geometry['coordinates'], key=lambda x: len(x[0]))
                                coords = largest_polygon[0]
                                lons = [coord[0] for coord in coords]
                                lats = [coord[1] for coord in coords]
                                
                                fig.add_trace(go.Scattergeo(
                                    lon=lons,
                                    lat=lats,
                                    mode='lines',
                                    fill='toself',
                                    fillcolor=cores_estados[estado_sigla],
                                    line=dict(color='white', width=1),
                                    opacity=0.6,
                                    name=df_unidades[df_unidades['estado'] == estado_sigla]['estado_nome'].iloc[0],
                                    hovertemplate=f'<b>{df_unidades[df_unidades["estado"] == estado_sigla]["estado_nome"].iloc[0]}</b><extra></extra>',
                                    showlegend=True
                                ))
                                break
                except Exception as e:
                    print(f"Erro ao processar estado {estado_sigla}: {e}")
                    continue
    
    # Adicionar pontos das unidades (pontos vermelhos como na imagem)
    fig.add_trace(go.Scattergeo(
        lon=df_unidades['lon'],
        lat=df_unidades['lat'],
        mode='markers',
        marker=dict(
            size=10,
            color='red',  # Vermelho como na imagem
            symbol='circle',
            line=dict(width=1, color='white')
        ),
        text=df_unidades['cidade'],
        hovertemplate='<b>%{text}</b><br>%{customdata}<extra></extra>',
        customdata=df_unidades['unidade'],
        name='Unidades',
        showlegend=True
    ))
    
    # Configurar layout geográfico
    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue",
        showlakes=True,
        lakecolor="lightblue",
        showcountries=True,
        countrycolor="white",
        showsubunits=True,
        subunitcolor="white",
        center=dict(lat=-16.0, lon=-50.0),
        lonaxis_range=[-60, -40],
        lataxis_range=[-25, -5]
    )
    
    # Configurar layout geral
    fig.update_layout(
        title=dict(
            text='<b>Mapa Geográfico da Empresa</b><br><sub>Estados de Atuação e Unidades Operacionais</sub>',
            x=0.5,
            font=dict(size=20, color='#2E86C1')
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="Black",
            borderwidth=1
        ),
        height=600,
        margin=dict(l=0, r=0, t=80, b=0)
    )
    
    return fig

def criar_mapa_simples_unidades(df_filtrado=None):
    """
    Cria um mapa simples mostrando apenas as unidades como pontos.
    Versão de fallback caso o mapa com estados não funcione.
    """
    df_unidades = criar_dados_unidades()
    
    # Filtrar unidades se necessário
    if df_filtrado is not None and not df_filtrado.empty and 'unidade' in df_filtrado.columns:
        unidades_ativas = df_filtrado['unidade'].unique()
        df_unidades = df_unidades[df_unidades['unidade'].isin(unidades_ativas)]
    
    if df_unidades.empty:
        st.warning("Nenhuma unidade encontrada para exibir no mapa.")
        return None
    
    # Criar mapa usando scatter_geo
    fig = go.Figure()
    
    # Adicionar pontos das unidades por regional (cores diferentes)
    cores_regionais = {
        'REGIONAL MORRINHOS': '#E74C3C',  # Vermelho
        'REGIONAL RIO VERDE': '#3498DB',   # Azul
        'REGIONAL TO': '#2ECC71',          # Verde
        'REGIONAL MT': '#F39C12'           # Laranja
    }
    
    for regional in df_unidades['regional'].unique():
        df_regional = df_unidades[df_unidades['regional'] == regional]
        
        fig.add_trace(go.Scattergeo(
            lon=df_regional['lon'],
            lat=df_regional['lat'],
            mode='markers',
            marker=dict(
                size=12,
                color=cores_regionais.get(regional, 'red'),
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            text=df_regional['cidade'],
            hovertemplate='<b>%{text}</b><br>%{customdata}<extra></extra>',
            customdata=df_regional['unidade'],
            name=regional.replace('REGIONAL ', ''),
            showlegend=True
        ))
    
    # Configurar layout
    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue",
        showcountries=True,
        countrycolor="white",
        showsubunits=True,
        subunitcolor="white",
        center=dict(lat=-16.0, lon=-50.0),
        lonaxis_range=[-60, -40],
        lataxis_range=[-25, -5]
    )
    
    fig.update_layout(
        title=dict(
            text='<b>Unidades da Empresa por Regional</b>',
            x=0.5,
            font=dict(size=18, color='#2E86C1')
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="Black",
            borderwidth=1
        ),
        height=600,
        margin=dict(l=0, r=0, t=60, b=0)
    )
    
    return fig

def exibir_estatisticas_geograficas(df_filtrado=None):
    """
    Exibe estatísticas geográficas das unidades.
    """
    df_unidades = criar_dados_unidades()
    
    if df_filtrado is not None and not df_filtrado.empty and 'unidade' in df_filtrado.columns:
        unidades_ativas = df_filtrado['unidade'].unique()
        df_unidades = df_unidades[df_unidades['unidade'].isin(unidades_ativas)]
    
    # Estatísticas por estado
    stats_estado = df_unidades.groupby('estado_nome').size().reset_index(name='quantidade')
    
    # Estatísticas por regional
    stats_regional = df_unidades.groupby('regional').size().reset_index(name='quantidade')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Unidades por Estado:**")
        for _, row in stats_estado.iterrows():
            st.write(f"• {row['estado_nome']}: {row['quantidade']} unidades")
    
    with col2:
        st.markdown("**Unidades por Regional:**")
        for _, row in stats_regional.iterrows():
            regional_nome = row['regional'].replace('REGIONAL ', '')
            st.write(f"• {regional_nome}: {row['quantidade']} unidades")
