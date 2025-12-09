import requests
import json
from dados import GURU_API_TOKEN

base_url = "https://digitalmanager.guru/api/v2/subscriptions"
token = GURU_API_TOKEN

def buscar_pagina(cursor=None):
    """Busca uma página (com ou sem cursor)"""
    url = f"{base_url}?cursor={cursor}" if cursor else base_url
    
    response = requests.get(
        url,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
    )
    
    return response.json()

def buscar_todas_paginas():
    """Busca TODAS as páginas até o final"""
    print("=" * 50)
    print("Buscando TODAS as páginas")
    print("=" * 50 + "\n")
    
    todos_dados = []
    cursor = None
    pagina_atual = 1
    total_registros = None
    
    while True:
        print(f"Buscando página {pagina_atual}...")
        
        # Busca a página
        pagina = buscar_pagina(cursor)
        
        # Guarda o total na primeira vez
        if total_registros is None:
            total_registros = pagina.get('total_rows')
        
        # Adiciona os dados desta página
        dados_pagina = pagina.get('data', [])
        todos_dados.extend(dados_pagina)
        
        print(f"✓ Página {pagina_atual} carregada: {len(dados_pagina)} registros")
        print(f"  Total acumulado: {len(todos_dados)} de {total_registros}")
        
        # Verifica se tem mais páginas
        has_more = pagina.get('has_more_pages') == 1
        
        if not has_more:
            print(f"\n✓ Última página alcançada!")
            break
        
        # Pega o cursor para a próxima página
        cursor = pagina.get('next_cursor')
        pagina_atual += 1
        print()  # Linha em branco
    
    print(f"\n{'=' * 50}")
    print(f"✓ CONCLUÍDO!")
    print(f"✓ Total de páginas processadas: {pagina_atual}")
    print(f"✓ Total de registros coletados: {len(todos_dados)}")
    print(f"{'=' * 50}\n")
    
    return todos_dados

def salvar_json(dados, nome_arquivo='todos_alunos.json'):
    """Salva os dados em um arquivo JSON"""
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Arquivo salvo: {nome_arquivo}")
    print(f"✓ Total de itens salvos: {len(dados)}")
    
    # Mostra exemplo do primeiro item
    if len(dados) > 0:
        print("\n=== EXEMPLO DO PRIMEIRO ITEM ===")
        print(json.dumps(dados[0], indent=2, ensure_ascii=False)[:500])

# EXECUÇÃO
print("Iniciando coleta de dados...\n")
todos_alunos = buscar_todas_paginas()
salvar_json(todos_alunos, 'todos_alunos.json')

print("\n✓ Processo finalizado com sucesso!")