import requests
import getpass

def acessar_api_terminal():
    login = input("Digite seu login: ")
    password = getpass.getpass("Digite sua senha: ")  # senha oculta
    version = "999"
    source = "SGI"
    
    url = "https://www.sgddolp.com.br/api_mars/index.php?login"
    
    payload = {
        "login": login,
        "password": password,
        "version": version,
        "SGI": source
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        try:
            dados = response.json()
            if "souser" in dados:
                souser = dados["souser"]
                print("✅ Login realizado com sucesso!")
                print("Souser retornado pela API:", souser)
                return souser
            else:
                print("⚠️ O campo 'souser' não foi encontrado na resposta:")
                print(dados)
                return None
        except ValueError:
            print("⚠️ Resposta não está em formato JSON:")
            print(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print("❌ Erro na conexão com a API:", e)
        return None
            

if __name__ == "__main__":
    souser = acessar_api_terminal()
