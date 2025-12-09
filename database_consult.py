from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY

# Configuração do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def consultar_aluno_por_email(email):
    """
    Consulta se um email existe na base e verifica o status da inscrição
    
    Returns:
        dict: Informações do aluno com status verificado ou None se não encontrado
    """
    try:
        print(f"🔍 Buscando email: {email}")
        
        # Busca o email no Supabase
        response = supabase.table('subscriptions')\
            .select('*')\
            .eq('contact_email', email)\
            .execute()
        
        # Verifica se encontrou algum resultado
        if not response.data or len(response.data) == 0:
            print(f"✗ Email não encontrado na base de dados\n")
            return None
        
        # Pega o primeiro resultado
        aluno = response.data[0]
        
        print(f"✓ Email encontrado!")
        print(f"  Nome: {aluno.get('contact_name')}")
        print(f"  Produto: {aluno.get('product_name')}")
        
        # Verifica o status
        status = aluno.get('last_status')
        
        if status == 'active':
            print(f"  ✅ Status: ACTIVE (Inscrição ativa)")
            aluno['esta_ativo'] = True
            aluno['status_simplificado'] = 'active'
        elif status == 'canceled':
            print(f"  ❌ Status: CANCELED (Inscrição cancelada)")
            aluno['esta_ativo'] = False
            aluno['status_simplificado'] = 'canceled'
        else:
            print(f"  ⚠️  Status: {status.upper()} (Outro status)")
            aluno['esta_ativo'] = False
            aluno['status_simplificado'] = status
        
        print()
        return aluno
        
    except Exception as e:
        print(f"✗ Erro ao consultar: {str(e)}\n")
        return None

def verificar_se_ativo(email):
    """
    Verifica se o email existe E se o status é 'active'
    
    Returns:
        bool: True se ativo, False se cancelado ou não encontrado
    """
    aluno = consultar_aluno_por_email(email)
    
    if aluno is None:
        return False
    
    return aluno.get('last_status') == 'active'

def verificar_se_cancelado(email):
    """
    Verifica se o email existe E se o status é 'canceled'
    
    Returns:
        bool: True se cancelado, False caso contrário
    """
    aluno = consultar_aluno_por_email(email)
    
    if aluno is None:
        return False
    
    return aluno.get('last_status') == 'canceled'

def verificar_status(email):
    """
    Retorna o status do aluno de forma simplificada
    
    Returns:
        str: 'active', 'canceled', 'not_found', ou outro status
    """
    aluno = consultar_aluno_por_email(email)
    
    if aluno is None:
        return 'not_found'
    
    return aluno.get('last_status')
