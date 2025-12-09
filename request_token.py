import requests
import json
from dados import GURU_API_TOKEN


base_url = "https://digitalmanager.guru/api/v2/subscriptions"


def get_info(email):
    url = f"{base_url}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {GURU_API_TOKEN}"
    }
    
    params = {
        "email": email
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print(data)

        if(check_mail(data=data,email=email)):
            print("Achou!")
        else:
            print("Deu ruim")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar aluno: {e}")
        return False
    
def check_mail(data, email):
    email = email.strip().lower()
    
    for pessoa in data.get("data", []):
        email_json = pessoa.get("contact", {}).get("email", "").strip().lower()
        
        if email_json == email:
            return True
    
    return False

    
get_info("kawehenri@gmail.com")