# Arquivo: loginsgd.py
import requests

def autenticar(usuario, senha):
    """
    Esta função se conecta à API REAL para validar o usuário.
    """
     
    source = "SGI"
    version = "999"  # Conforme seu script
    url = "https://www.sgddolp.com.br/api_mars/index.php?login"
    payload = {
        "login": usuario,
        "password": senha,
        "version": version,
        "source":source
    }
    headers = {"Content-Type": "application/json"}

    try:
        # Faz a chamada para a API com um timeout de 10 segundos
        response = requests.post(url, json=payload, headers=headers, timeout=10 )
        
        # Verifica se a resposta da API foi bem-sucedida (código 2xx)
        response.raise_for_status()
        
        dados = response.json()
        
        # Verifica se o login foi bem-sucedido de acordo com a lógica da sua API
        if dados.get('status') == 200 and dados.get('retorno') is True:
            print(f"API REAL: Autenticação bem-sucedida para {usuario}")
            # Adiciona os campos que o app Streamlit precisa
            dados['nome'] = dados.get('login') # Usa o próprio login como nome padrão
            dados['perfil'] = 'API User' # Perfil padrão para usuários da API
            return dados
        else:
            print(f"API REAL: Falha na autenticação (resposta da API: {dados})")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com a API: {e}")
        # Retorna um dicionário de erro para ser exibido no Streamlit
        return {"erro": "Não foi possível conectar à API de autenticação."}
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return {"erro": "Ocorreu um erro inesperado."}


def obter_permissoes_por_perfil(perfil):
    """
    Retorna permissões baseadas no perfil.
    """
    permissoes = {
        "Administrador": ["pagina1", "pagina2", "pagina_admin"],
        "Operacional": ["pagina1"],
        # 'API User' não tem permissões por padrão
    }
    return permissoes.get(perfil, [])