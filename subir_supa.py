import json
from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY  # ou crie essas variáveis

# Configuração do Supabase
supabase_url = SUPABASE_URL  # Ex: "https://seuproject.supabase.co"
supabase_key = SUPABASE_KEY  # Sua API key (anon/public ou service_role)
supabase: Client = create_client(supabase_url, supabase_key)

def ler_json(nome_arquivo='todos_alunos.json'):
    """Lê o arquivo JSON"""
    print(f"Lendo arquivo {nome_arquivo}...")
    with open(nome_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    print(f"✓ {len(dados)} registros carregados\n")
    return dados

def transformar_dados(aluno):
    """Transforma o JSON para o formato da tabela"""
    return {
        # Identificadores
        'id': aluno.get('id'),
        'subscription_code': aluno.get('subscription_code'),
        
        # Cobrança
        'cancel_at_cycle_end': aluno.get('cancel_at_cycle_end'),
        'cancelled_at': aluno.get('cancelled_at'),
        'charged_every_days': aluno.get('charged_every_days'),
        'charged_times': aluno.get('charged_times'),
        'payment_method': aluno.get('payment_method'),
        
        # Ciclo
        'cycle_start_date': aluno.get('cycle_start_date'),
        'cycle_end_date': aluno.get('cycle_end_date'),
        'next_cycle_at': aluno.get('next_cycle_at'),
        'is_cycling': aluno.get('is_cycling'),
        
        # Status
        'last_status': aluno.get('last_status'),
        'last_status_at': aluno.get('last_status_at'),
        
        # Trial
        'trial_started_at': aluno.get('trial_started_at'),
        'trial_finished_at': aluno.get('trial_finished_at'),
        
        # Produto (desnormalizado)
        'product_id': aluno.get('product', {}).get('id'),
        'product_name': aluno.get('product', {}).get('name'),
        'product_marketplace_id': aluno.get('product', {}).get('marketplace_id'),
        'product_marketplace_name': aluno.get('product', {}).get('marketplace_name'),
        'product_group_id': aluno.get('product', {}).get('group', {}).get('id'),
        'product_group_name': aluno.get('product', {}).get('group', {}).get('name'),
        
        # Contato (desnormalizado)
        'contact_id': aluno.get('contact', {}).get('id'),
        'contact_name': aluno.get('contact', {}).get('name'),
        'contact_email': aluno.get('contact', {}).get('email'),
        'contact_doc': aluno.get('contact', {}).get('doc'),
        'contact_phone_local_code': aluno.get('contact', {}).get('phone_local_code'),
        'contact_phone_number': aluno.get('contact', {}).get('phone_number'),
        
        # Metadados
        'own_engine': aluno.get('own_engine'),
        'contracts': aluno.get('contracts'),
        'started_at': aluno.get('started_at'),
        'created_at': aluno.get('created_at'),
        'updated_at': aluno.get('updated_at')
    }

def inserir_em_lotes(dados, tamanho_lote=100):
    """Insere os dados no Supabase em lotes"""
    total = len(dados)
    inseridos = 0
    erros = 0
    
    print(f"Iniciando inserção de {total} registros...")
    print(f"Inserindo em lotes de {tamanho_lote}\n")
    
    for i in range(0, total, tamanho_lote):
        lote = dados[i:i + tamanho_lote]
        lote_transformado = [transformar_dados(aluno) for aluno in lote]
        
        try:
            # Insere o lote
            result = supabase.table('subscriptions').upsert(lote_transformado).execute()
            
            inseridos += len(lote)
            print(f"✓ Lote {i//tamanho_lote + 1}: {inseridos}/{total} registros inseridos")
            
        except Exception as e:
            erros += len(lote)
            print(f"✗ Erro no lote {i//tamanho_lote + 1}: {str(e)}")
    
    print(f"\n{'=' * 50}")
    print(f"✓ CONCLUÍDO!")
    print(f"✓ Total inserido: {inseridos}")
    print(f"✗ Total com erro: {erros}")
    print(f"{'=' * 50}")

# EXECUÇÃO
print("=" * 50)
print("UPLOAD DE DADOS PARA SUPABASE")
print("=" * 50 + "\n")

# Lê o JSON
dados = ler_json('todos_alunos.json')

# Insere no Supabase
inserir_em_lotes(dados, tamanho_lote=100)

print("\n✓ Processo finalizado!")