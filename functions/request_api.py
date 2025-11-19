import requests



def verificar_aluno(email: str) -> bool:
    """
    Verifica se o e-mail informado pertence a um aluno cadastrado na Digital Manager Guru.
    Retorna True se for aluno, False caso contrário.
    """
    ACCOUNT_TOKEN = "dpOBx40TwVOBfxtyime6Oaha1dynOu07XTZnebAT"  # substitua pelo seu token real
    
    url = f"https://digitalmanager.guru/api/v2/customers?email={email}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCOUNT_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Dependendo da resposta da API, pode vir lista ou dict. 
        # Vamos supor que, se o e-mail existe, a API retorna uma lista não vazia.
        if isinstance(data, list) and len(data) > 0:
            return True
        elif isinstance(data, dict) and "email" in data:
            return True
        else:
            return False

    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar aluno: {e}")
        return False
