import streamlit as st
import pandas as pd
import os
import json
from itertools import product
from datetime import datetime

# --- Constantes ---
DATA_DIR = 'data'
LOG_FILE = 'data/log_acessos.csv'
PERMISSIONS_FILE = os.path.join(DATA_DIR, 'permissoes.json')
RULES_FILE = os.path.join(DATA_DIR, 'regras.json')
UNIDADES_FILE = os.path.join(DATA_DIR, 'unidades.csv')
FUNCOES_FILE = os.path.join(DATA_DIR, 'funcoes.csv')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'log_permissoes.csv') # Novo log de auditoria
ALL_PAGES = ["pagina1", "pagina2", "pagina3", "pagina4", "pagina7", "pagina8", "pagina10", 
             "pagina11", "pagina12", "pagina13", "pagina_admin","pagina14","pagina15","pagina16","pagina17","pagina18","pagina19","pagina21","pagina40", "pagina30"]

# --- Funções de Manipulação de Dados ---
def carregar_json(filepath, default_data={}):
    if not os.path.exists(filepath): return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return default_data

def salvar_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def carregar_csv(filepath, default_df):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0: return default_df
    return pd.read_csv(filepath)

# --- NOVA FUNÇÃO DE LOG DE AUDITORIA ---
def log_auditoria(admin_user, acao, alvo, detalhes=""):
    """Registra uma ação de alteração de permissão."""
    if not os.path.exists(AUDIT_LOG_FILE):
        pd.DataFrame(columns=['timestamp', 'admin', 'acao', 'alvo', 'detalhes']).to_csv(AUDIT_LOG_FILE, index=False)
    
    novo_log = pd.DataFrame([{
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'admin': admin_user,
        'acao': acao,
        'alvo': alvo,
        'detalhes': detalhes
    }])
    novo_log.to_csv(AUDIT_LOG_FILE, mode='a', header=False, index=False)

# --- Funções de Interface da Página de Admin ---

def gerenciar_permissoes_manuais(permissoes, admin_user):
    st.subheader("Definir Acesso Manual por Usuário (Sobrescreve Regras)")
    df_logs = carregar_csv(LOG_FILE, pd.DataFrame(columns=['usuario']))
    if df_logs.empty:
        st.info("Nenhum log de acesso encontrado para listar usuários."); return

    usuarios_com_sucesso = sorted(df_logs[df_logs['status'] == 'SUCESSO']['usuario'].unique().tolist())
    if not usuarios_com_sucesso:
        st.info("Nenhum login bem-sucedido registrado ainda."); return

    usuario_selecionado = st.selectbox("Selecione um usuário para criar/editar uma permissão manual:", usuarios_com_sucesso)
    
    if usuario_selecionado:
        permissoes_atuais = permissoes.get(usuario_selecionado, [])
        st.markdown(f"#### Editando permissões para: **{usuario_selecionado}**")
        novas_permissoes = st.multiselect("Selecione as páginas:", options=ALL_PAGES, default=permissoes_atuais, key=f"ms_{usuario_selecionado}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Salvar Permissão Manual", key=f"save_btn_{usuario_selecionado}"):
                permissoes[usuario_selecionado] = novas_permissoes
                salvar_json(permissoes, PERMISSIONS_FILE)
                log_auditoria(admin_user, "SALVAR PERMISSÃO MANUAL", usuario_selecionado, f"Páginas: {novas_permissoes}")
                st.success(f"Permissão manual para '{usuario_selecionado}' salva!")
        with col2:
            if st.button("Remover Permissão Manual", key=f"del_btn_{usuario_selecionado}", type="primary"):
                if usuario_selecionado in permissoes:
                    del permissoes[usuario_selecionado]
                    salvar_json(permissoes, PERMISSIONS_FILE)
                    log_auditoria(admin_user, "REMOVER PERMISSÃO MANUAL", usuario_selecionado)
                    st.success(f"Permissão manual para '{usuario_selecionado}' removida.")

def gerenciar_regras_automaticas(regras, admin_user):
    st.subheader("Gerenciar Grupos de Permissão Automática")
    st.markdown("Crie ou edite um grupo de permissão nomeado, associando múltiplas funções e unidades a um conjunto de páginas.")

    df_unidades = carregar_csv(UNIDADES_FILE, pd.DataFrame(columns=['idtb_bases', 'unidade']))
    df_funcoes = carregar_csv(FUNCOES_FILE, pd.DataFrame(columns=['funcao_geral']))

    if 'regra_para_editar' in st.session_state:
        nome_regra_default = st.session_state['regra_para_editar']['nome']
        valores = st.session_state['regra_para_editar']['valores']
        funcoes_default, unidades_default, paginas_default = valores.get('funcoes', []), valores.get('unidades', []), valores.get('paginas', [])
        titulo_form = f"Editando Grupo: `{nome_regra_default}`"
    else:
        nome_regra_default, funcoes_default, unidades_default, paginas_default = "", [], [], []
        titulo_form = "Adicionar Novo Grupo de Permissão"

    with st.form("form_regra", clear_on_submit=False):
        st.markdown(f"#### {titulo_form}")
        nome_regra = st.text_input("Nome do Grupo de Permissão", value=nome_regra_default)
        funcoes_selecionadas = st.multiselect("Funções neste Grupo", options=df_funcoes['funcao_geral'].dropna().tolist(), default=funcoes_default)
        unidades_selecionadas = st.multiselect("Unidades neste Grupo", options=df_unidades['idtb_bases'].tolist(), default=unidades_default, format_func=lambda x: f"{x} - {df_unidades[df_unidades['idtb_bases'] == x]['unidade'].iloc[0]}" if not df_unidades[df_unidades['idtb_bases'] == x].empty else x)
        paginas_regra = st.multiselect("Páginas para este Grupo", options=ALL_PAGES, default=paginas_default)
        
        submitted = st.form_submit_button("Salvar Grupo de Permissão")
        if submitted:
            if not all([nome_regra, funcoes_selecionadas, unidades_selecionadas, paginas_regra]):
                st.warning("Todos os campos são obrigatórios para salvar um grupo.")
            else:
                acao_log = "EDITAR GRUPO" if 'regra_para_editar' in st.session_state else "CRIAR GRUPO"
                if 'regra_para_editar' in st.session_state and st.session_state['regra_para_editar']['nome'] != nome_regra:
                    del regras[st.session_state['regra_para_editar']['nome']]

                regras[nome_regra] = {"funcoes": funcoes_selecionadas, "unidades": unidades_selecionadas, "paginas": paginas_regra}
                salvar_json(regras, RULES_FILE)
                log_auditoria(admin_user, acao_log, nome_regra, f"Funções: {funcoes_selecionadas}, Unidades: {unidades_selecionadas}, Páginas: {paginas_regra}")
                
                if 'regra_para_editar' in st.session_state: del st.session_state['regra_para_editar']
                st.success(f"Grupo de permissão '{nome_regra}' salvo com sucesso!"); st.rerun()

    st.markdown("---")
    
    st.subheader("Grupos de Permissão Atuais")
    if not regras:
        st.info("Nenhum grupo de permissão cadastrado.")
    else:
        for nome_regra, valores in list(regras.items()):
            with st.container():
                st.markdown(f"##### Grupo: `{nome_regra}`")
                st.write(f"**Funções:** `{', '.join(valores.get('funcoes', []))}`"); st.write(f"**Unidades:** `{', '.join(map(str, valores.get('unidades', [])))}`"); st.write(f"**Páginas liberadas:** `{', '.join(valores.get('paginas', []))}`")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️ Editar", key=f"edit_rule_{nome_regra}"):
                        st.session_state['regra_para_editar'] = {"nome": nome_regra, "valores": valores}; st.rerun()
                with col2:
                    if st.button("🗑️ Remover", key=f"del_rule_{nome_regra}", type="primary"):
                        del regras[nome_regra]
                        if 'regra_para_editar' in st.session_state and st.session_state['regra_para_editar']['nome'] == nome_regra:
                            del st.session_state['regra_para_editar']
                        salvar_json(regras, RULES_FILE)
                        log_auditoria(admin_user, "REMOVER GRUPO", nome_regra)
                        st.success(f"Grupo '{nome_regra}' removido."); st.rerun()
                st.markdown("---")

def visualizar_logs_auditoria():
    """Nova função para exibir os logs de auditoria."""
    st.subheader("📋 Log de Auditoria de Permissões")
    df_audit = carregar_csv(AUDIT_LOG_FILE, pd.DataFrame(columns=['timestamp', 'admin', 'acao', 'alvo', 'detalhes']))
    if df_audit.empty:
        st.info("Nenhum registro de auditoria encontrado.")
    else:
        # Ordena do mais recente para o mais antigo
        st.dataframe(df_audit.sort_values(by='timestamp', ascending=False), use_container_width=True)

# --- Função Principal da Página ---
def app():
    st.title("⚙️ Painel de Administração")
    
    # Pega o nome do admin logado para registrar na auditoria
    admin_user = st.session_state.get('usuario_info', {}).get('login', 'desconhecido')
    
    os.makedirs(DATA_DIR, exist_ok=True)
    permissoes_manuais = carregar_json(PERMISSIONS_FILE)
    regras_automaticas = carregar_json(RULES_FILE)

    # Adiciona a nova aba de logs
    tab1, tab2, tab3 = st.tabs(["📜 Gerenciar Grupos", "🔑 Gerenciar Permissões Manuais", "🕵️ Visualizar Logs de Auditoria"])

    with tab1:
        gerenciar_regras_automaticas(regras_automaticas, admin_user)
    with tab2:
        gerenciar_permissoes_manuais(permissoes_manuais, admin_user)
    with tab3:
        visualizar_logs_auditoria()
