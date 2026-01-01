import json
import os
from datetime import datetime
from pathlib import Path

# Cria as pastas necessárias
Path("uploads").mkdir(exist_ok=True)
Path("questoes_data").mkdir(exist_ok=True)

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