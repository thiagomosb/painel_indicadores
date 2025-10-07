import streamlit as st
import os
import json
from datetime import datetime
import pandas as pd

# --- Importa o MÓDULO da sua API ---
import loginsgd 

# --- Importação das suas páginas ---
import pagina1, pagina2, pagina3, pagina4, pagina7, pagina8, pagina_admin, pagina10, pagina11, pagina12, pagina13

# --- Dicionário de Páginas ---
PAGES = {
    "pagina1": pagina1.app, "pagina2": pagina2.app, "pagina3": pagina3.app,
    "pagina4": pagina4.app, "pagina7": pagina7.app, "pagina8": pagina8.app,
    "pagina_admin": pagina_admin.app, "pagina10": pagina10.app, "pagina11": pagina11.app,
    "pagina12": pagina12.app, "pagina13": pagina13.app,
}

# --- Constantes dos arquivos de dados ---
DATA_DIR = 'data'
LOG_FILE = os.path.join(DATA_DIR, 'log_acessos.csv')
PERMISSIONS_FILE = os.path.join(DATA_DIR, 'permissoes.json')
RULES_FILE = os.path.join(DATA_DIR, 'regras.json')

# --- Classe da API de Login com Logging ---
class LoginAPI:
    def __init__(self):
        self._inicializar_log()

    def _inicializar_log(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(LOG_FILE):
            pd.DataFrame(columns=['timestamp', 'usuario', 'status', 'ip']).to_csv(LOG_FILE, index=False)

    def _log_acesso(self, usuario, status):
        try:
            novo_log = pd.DataFrame([{'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'usuario': usuario, 'status': status, 'ip': "N/A"}])
            novo_log.to_csv(LOG_FILE, mode='a', header=False, index=False)
        except Exception as e:
            print(f"Erro ao registrar log: {e}")

    def autenticar(self, usuario, senha):
        dados_api = loginsgd.autenticar(usuario, senha)
        if dados_api and dados_api.get('status') == 200:
            self._log_acesso(usuario, "SUCESSO")
            return dados_api
        else:
            self._log_acesso(usuario, "FALHA")
            return dados_api if dados_api and "erro" in dados_api else None

loginsgd_api_handler = LoginAPI()

# --- Função de Permissões Dinâmica ---
def obter_permissoes(dados_usuario):
    usuario = dados_usuario.get('login')
    metadados = dados_usuario.get('metadados', {})
    funcao_usuario = str(metadados.get('funcao_geral', '')).upper().strip()
    unidade_usuario = metadados.get('unid_lot')

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(PERMISSIONS_FILE):
            with open(PERMISSIONS_FILE, 'r', encoding='utf-8') as f:
                permissoes_manuais = json.load(f)
            if usuario in permissoes_manuais:
                return permissoes_manuais[usuario]
    except Exception as e:
        print(f"Erro ao ler permissões manuais: {e}")

    try:
        if os.path.exists(RULES_FILE):
            with open(RULES_FILE, 'r', encoding='utf-8') as f:
                regras_por_grupo = json.load(f)
            for nome_grupo, valores_regra in regras_por_grupo.items():
                funcoes_do_grupo = [f.upper().strip() for f in valores_regra.get('funcoes', [])]
                unidades_do_grupo = valores_regra.get('unidades', [])
                if funcao_usuario in funcoes_do_grupo and unidade_usuario in unidades_do_grupo:
                    return valores_regra.get('paginas', [])
    except Exception as e:
        print(f"Erro ao ler regras automáticas: {e}")

    return []

# --- Funções de Interface ---
def aplicar_css_global():
    """Aplica o CSS do projeto original."""
    st.markdown("""
    <style>
        /* Cabeçalho principal */
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(90deg, #3E4095 0%, #ED3237 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 3rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        /* Botões */
        .stButton > button {
            background: linear-gradient(90deg, #3E4095, #ED3237) !important;
            color: white !important;
            border: none !important;
            padding: 1rem 2rem !important;
            border-radius: 8px !important;
            font-size: 1.1rem !important;
            font-weight: bold !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
            width: 100% !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5) !important;
        }
        /* Abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            padding: 6px;
            background: #FFFFFF;
            border-radius: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
            border-radius: 6px;
            color: white;
            background-color: #3E4095;
            transition: all 0.3s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #ED3237;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ED3237 !important;
            color: white !important;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)



def tela_login():
    st.markdown(
        """
        <style>
           
            .stTextInput > div > div > input {
                border-radius: 8px;
                padding: 0.5rem;
            }
            .stPasswordInput > div > div > input {
                border-radius: 8px;
                padding: 0.5rem;
            }
            .stButton button {
                width: 100%;
                border-radius: 8px;
                background-color: #2563eb;  /* Azul normal */
                color: white;
                font-weight: bold;
                padding: 0.6rem;
                border: none;
                transition: background-color 0.3s ease-in-out;
            }
            .stButton button:hover {
                background-color: #16a34a !important;  /* Verde ao passar o mouse */
                color: white !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    


    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h2 style='text-align: center; color:#2563eb;'>🔐 Sistema de Gestão de Indicadores</h2>",
            unsafe_allow_html=True
        )

        with st.container():
            with st.form(key="login_form"):
                st.markdown("<div class='login-card'>", unsafe_allow_html=True)

                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")

                if st.form_submit_button(label="Entrar"):
                    dados_usuario = loginsgd_api_handler.autenticar(usuario, senha)
                    if dados_usuario and "erro" in dados_usuario:
                        st.error(dados_usuario["erro"])
                    elif dados_usuario:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_info'] = dados_usuario
                        st.session_state['permissoes'] = obter_permissoes(dados_usuario)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")

                st.markdown("</div>", unsafe_allow_html=True)



def menu_principal():
    nome_usuario = st.session_state.get('usuario_info', {}).get('nome', 'Usuário Desconhecido')
    with st.sidebar:
        st.markdown("---", unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='text-align: center;'>Bem-vindo(a), <b>{nome_usuario}</b>!</h3>", 
            unsafe_allow_html=True
        )

        if st.button("Logout"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.markdown("---")

    st.image("https://www.dolpengenharia.com.br/wp-content/uploads/2021/01/logotipo-definitivo-250614.png", width=200 )
    st.markdown("""
    <div class="main-header">
        <h1> DASHBOARDS DOLP ENGENHARIA LTDA</h1>
        <p>Painel de Controle - Selecione uma área para acessar</p>
    </div>
    """, unsafe_allow_html=True)
    
    permissoes = st.session_state.get('permissoes', [])
    
    tabs_a_mostrar = {}
    if any(p in permissoes for p in ["pagina1", "pagina2", "pagina3", "pagina10", "pagina11", "pagina12", "pagina13"]):
        tabs_a_mostrar["🔧 Operacional"] = aba_operacional
    if any(p in permissoes for p in ["pagina7", "pagina8"]):
        tabs_a_mostrar["🦺 SESMT"] = aba_sesmt
    if any(p in permissoes for p in ["pagina4"]):
        tabs_a_mostrar["📹 Monitoria"] = aba_monitoria
    if "pagina_admin" in permissoes:
        tabs_a_mostrar["⚙️ Administração"] = aba_admin

    if tabs_a_mostrar:
        tabs = st.tabs(list(tabs_a_mostrar.keys()))
        for i, (nome_tab, funcao_tab) in enumerate(tabs_a_mostrar.items()):
            with tabs[i]:
                funcao_tab()
    else:
        st.warning("Login realizado com sucesso! Você não tem permissão para acessar nenhuma página. Contate um administrador.")

def show_page(page_name):
    nome_usuario = st.session_state.get('usuario_info', {}).get('nome', 'Usuário Desconhecido')
    permissoes = st.session_state.get('permissoes', [])
    if page_name not in permissoes:
        st.error("Acesso Negado!"); st.stop()
    with st.sidebar:
        st.markdown(f"<p style='text-align: center;'>Logado como: <b>{nome_usuario}</b></p>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>🏠 Navegação</h3>", unsafe_allow_html=True)

        if st.button("⬅️ Voltar ao Menu", key=f"sidebar_back_{page_name}"):
            st.session_state.current_page = 'menu'; st.rerun()
        st.markdown("---")
    page_function = PAGES.get(page_name)
    if page_function: page_function()
    else: st.error(f"Erro: Página '{page_name}' não encontrada.")

def aba_operacional():
    permissoes = st.session_state.get('permissoes', [])
    if "pagina1" in permissoes and st.button("MONITORAMENTO - ESCALA x TURNOS", key="btn_p1"):
        st.session_state.current_page = 'pagina1'; st.rerun()
    if "pagina2" in permissoes and st.button("MONITORAMENTO - REALIZAÇÃO RDO", key="btn_p2"):
        st.session_state.current_page = 'pagina2'; st.rerun()
    if "pagina3" in permissoes and st.button("CONFIGURAÇÃO - TURNOS CONTRATADOS", key="btn_p3"):
        st.session_state.current_page = 'pagina3'; st.rerun()
    if "pagina10" in permissoes and st.button("MONITORAMENTO ESCALA x TURNOS - REGIONAL MORRINHOS", key="btn_p10"):
        st.session_state.current_page = 'pagina10'; st.rerun()
    if "pagina11" in permissoes and st.button("MONITORAMENTO ESCALA x TURNOS - REGIONAL RIO VERDE", key="btn_p11"):
        st.session_state.current_page = 'pagina11'; st.rerun()
    if "pagina12" in permissoes and st.button("MONITORAMENTO ESCALA x TURNOS - REGIONAL TO", key="btn_p12"):
        st.session_state.current_page = 'pagina12'; st.rerun()
    if "pagina13" in permissoes and st.button("MONITORAMENTO ESCALA x TURNOS - REGIONAL MT", key="btn_p13"):
        st.session_state.current_page = 'pagina13'; st.rerun()

def aba_sesmt():
    permissoes = st.session_state.get('permissoes', [])
    if "pagina7" in permissoes and st.button("INSPEÇÕES - TAXA DE CONTATO - EQUIPES", key="btn_p7"):
        st.session_state.current_page = 'pagina7'; st.rerun()
    if "pagina8" in permissoes and st.button("INSPEÇÕES - TAXA DE CONTATO - PESSOAS", key="btn_p8"):
        st.session_state.current_page = 'pagina8'; st.rerun()

def aba_monitoria():
    permissoes = st.session_state.get('permissoes', [])
    if "pagina4" in permissoes and st.button("INDICADORES DE ANALISES DE MONITORAMENTO", key="btn_p4"):
        st.session_state.current_page = 'pagina4'; st.rerun()

def aba_admin():
    if st.button("Gerenciar Permissões", key="btn_admin_users"):
        st.session_state.current_page = 'pagina_admin'; st.rerun()

def main():
    st.set_page_config(page_title="Sistema de Gestão", layout="wide")
    aplicar_css_global()
    if 'autenticado' not in st.session_state:
        tela_login()
    else:
        st.session_state.setdefault('current_page', 'menu')
        if st.session_state.current_page == 'menu':
            menu_principal()
        else:
            show_page(st.session_state.current_page)

if __name__ == "__main__":
    main()
