from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY

# Configuração do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def consultar_aluno_por_email(email):
    """
    Retorna:
        ('active')    -> se QUALQUER assinatura estiver ativa
        ('inactive')  -> se email existe, mas nenhuma assinatura ativa
        None          -> se email não existe
    """
    try:
        response = supabase.table('subscriptions') \
            .select('last_status') \
            .eq('contact_email', email) \
            .execute()

        if not response.data:
            return None  # email nunca comprou

        statuses = [row.get("last_status") for row in response.data]

        if "active" in statuses:
            return "active"

        return "inactive"  # já foi aluno, mas cancelou/expirou

    except Exception as e:
        print(f"❌ Erro ao consultar subscriptions: {e}")
        return None


        
        
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
