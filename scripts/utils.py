import json
import os
from datetime import datetime, date
from pathlib import Path

# Cria as pastas necessárias
Path("uploads").mkdir(exist_ok=True)
Path("questoes_data").mkdir(exist_ok=True)

QUESTOES_DIR = "questoes_data"

def usuario_ja_perguntou_hoje(usuario_id: int) -> bool:
    """
    Verifica se o usuário já criou uma questão hoje
    """
    hoje = date.today()

    if not os.path.exists(QUESTOES_DIR):
        return False

    for arquivo in os.listdir(QUESTOES_DIR):
        if not arquivo.endswith(".json"):
            continue

        caminho = os.path.join(QUESTOES_DIR, arquivo)

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if int(dados.get("usuario_id")) != int(usuario_id):
                continue

            data_criacao = datetime.fromisoformat(dados.get("data_criacao")).date()

            if data_criacao == hoje:
                return True

        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")

    return False


def salvar_questao_local(usuario_id, usuario_nome, descricao, materia, imagem_path=None):
    """
    Salva os dados da questão localmente em JSON
    
    Args:
        usuario_id: ID do usuário do Discord
        usuario_nome: Nome do usuário
        descricao: Descrição da questão
        materia: Matéria selecionada
        imagem_path: Caminho da imagem salva (opcional)
    
    Returns:
        str: Caminho do arquivo JSON criado
    """
    dados_questao = {
        "usuario_id": usuario_id,
        "usuario_nome": usuario_nome,
        "descricao": descricao,
        "materia": materia,
        "imagem": imagem_path,
        "data_criacao": datetime.now().isoformat()
    }
    
    # Nome do arquivo baseado no timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo = f"questoes_data/questao_{usuario_id}_{timestamp}.json"
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_questao, f, ensure_ascii=False, indent=2)
    
    return arquivo