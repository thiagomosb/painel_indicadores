#!/usr/bin/env python3
"""
Demonstração do Mapa Geográfico da Empresa
Executa uma versão simplificada para mostrar o resultado final
"""

import sys
sys.path.append('/home/ubuntu')

from mapa_geografico import criar_mapa_geografico_empresa, criar_mapa_simples_unidades, criar_dados_unidades
import pandas as pd

def demonstrar_mapas():
    """
    Demonstra os mapas criados para o projeto.
    """
    print("=" * 60)
    print("DEMONSTRAÇÃO - MAPA GEOGRÁFICO DA EMPRESA")
    print("=" * 60)
    
    # Mostrar dados das unidades
    df_unidades = criar_dados_unidades()
    print("\n📍 UNIDADES MAPEADAS:")
    print(f"Total de unidades: {len(df_unidades)}")
    
    print("\nDistribuição por estado:")
    for estado in df_unidades['estado_nome'].unique():
        count = len(df_unidades[df_unidades['estado_nome'] == estado])
        print(f"  • {estado}: {count} unidades")
    
    print("\nDistribuição por regional:")
    for regional in df_unidades['regional'].unique():
        count = len(df_unidades[df_unidades['regional'] == regional])
        regional_nome = regional.replace('REGIONAL ', '')
        print(f"  • {regional_nome}: {count} unidades")
    
    print("\n" + "=" * 60)
    print("CRIANDO MAPAS...")
    print("=" * 60)
    
    # Criar mapa com estados
    print("\n🗺️  Criando mapa com estados em azul e unidades em vermelho...")
    try:
        fig_estados = criar_mapa_geografico_empresa()
        if fig_estados:
            fig_estados.write_html('/home/ubuntu/demo_mapa_estados.html')
            print("✅ Mapa com estados criado: demo_mapa_estados.html")
        else:
            print("❌ Falha ao criar mapa com estados")
    except Exception as e:
        print(f"❌ Erro ao criar mapa com estados: {e}")
    
    # Criar mapa simples
    print("\n🎯 Criando mapa simples por regional...")
    try:
        fig_simples = criar_mapa_simples_unidades()
        if fig_simples:
            fig_simples.write_html('/home/ubuntu/demo_mapa_simples.html')
            print("✅ Mapa simples criado: demo_mapa_simples.html")
        else:
            print("❌ Falha ao criar mapa simples")
    except Exception as e:
        print(f"❌ Erro ao criar mapa simples: {e}")
    
    print("\n" + "=" * 60)
    print("INTEGRAÇÃO COM STREAMLIT")
    print("=" * 60)
    
    print("\n📋 Para usar no Streamlit:")
    print("1. Execute: streamlit run pagina1.py")
    print("2. Navegue para a aba 'MAPA GEOGRÁFICO'")
    print("3. Escolha o tipo de visualização")
    print("4. Use os filtros da barra lateral")
    
    print("\n🎨 Características do mapa:")
    print("• Estados renderizados em azul (conforme modelo da imagem)")
    print("• Unidades mostradas como pontos vermelhos")
    print("• Integração completa com filtros existentes")
    print("• Hover com informações detalhadas")
    print("• Fallback para mapa simples se necessário")
    
    print("\n" + "=" * 60)
    print("DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 60)

if __name__ == "__main__":
    demonstrar_mapas()
