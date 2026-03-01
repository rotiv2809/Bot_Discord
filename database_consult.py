import requests
from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY, MEMBERKIT_API_KEY

# Configuração do Supabase (Guru)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────
# GURU — consulta via Supabase
# ─────────────────────────────────────────────

def _consultar_guru(email: str) -> bool:
    """
    Consulta o banco do Supabase (Guru).
    Retorna True se o email tiver alguma assinatura com status 'active'.
    """
    try:
        response = supabase.table("subscriptions") \
            .select("last_status") \
            .eq("contact_email", email) \
            .execute()

        if not response.data:
            return False

        statuses = [row.get("last_status") for row in response.data]
        return "active" in statuses

    except Exception as e:
        print(f"❌ Erro ao consultar Guru (Supabase): {e}")
        return False


# ─────────────────────────────────────────────
# MEMBERKIT — consulta via API REST
# ─────────────────────────────────────────────

def _consultar_memberkit(email: str) -> bool:
    """
    Consulta a API da MemberKit pelo email.
    Retorna True se encontrar o membro com status ativo.

    Endpoint: GET https://app.memberkit.com.br/api/v1/members?email=<email>
    Header:   Authorization: <MEMBERKIT_API_KEY>

    Ajuste STATUSES_ATIVOS conforme os status reais retornados pela MemberKit.
    """
    if not MEMBERKIT_API_KEY:
        print("⚠️  MEMBERKIT_API_KEY não configurada, pulando consulta MemberKit.")
        return False

    # Status considerados como "aluno ativo" na MemberKit
    STATUSES_ATIVOS = {"active", "paying"}

    url = "https://app.memberkit.com.br/api/v1/members"
    headers = {"Authorization": MEMBERKIT_API_KEY}
    params = {"email": email}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 404:
            return False  # email não existe na MemberKit

        if resp.status_code != 200:
            print(f"⚠️  MemberKit retornou status {resp.status_code} para {email}")
            return False

        data = resp.json()

        # A resposta pode ser lista ou dict com chave "members"
        if isinstance(data, list):
            members = data
        elif isinstance(data, dict):
            members = data.get("members", [data])
        else:
            return False

        for member in members:
            status = str(member.get("status", "")).lower()
            if status in STATUSES_ATIVOS:
                return True

        return False

    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout ao consultar MemberKit para {email}")
        return False
    except Exception as e:
        print(f"❌ Erro ao consultar MemberKit: {e}")
        return False


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — verifica em ambas as bases
# ─────────────────────────────────────────────

def consultar_aluno_por_email(email: str):
    """
    Consulta o email no Supabase da Guru E na MemberKit.

    Retorna:
        'active'   -> email encontrado com status ativo em QUALQUER das plataformas
        'inactive' -> email existe mas não está ativo em nenhuma das plataformas
        None       -> email não encontrado em nenhuma plataforma
                      (aciona verificação manual)
    """
    ativo_guru      = _consultar_guru(email)
    ativo_memberkit = _consultar_memberkit(email)

    if ativo_guru or ativo_memberkit:
        origem = []
        if ativo_guru:      origem.append("Guru")
        if ativo_memberkit: origem.append("MemberKit")
        print(f"✅ Aluno ativo encontrado em: {', '.join(origem)} — {email}")
        return "active"

    # Verifica se o email ao menos existe (status inativo) na Guru
    try:
        response = supabase.table("subscriptions") \
            .select("last_status") \
            .eq("contact_email", email) \
            .execute()
        existe_guru = bool(response.data)
    except Exception:
        existe_guru = False

    # Verifica existência na MemberKit (qualquer status)
    existe_memberkit = False
    if MEMBERKIT_API_KEY:
        try:
            resp = requests.get(
                "https://app.memberkit.com.br/api/v1/members",
                headers={"Authorization": MEMBERKIT_API_KEY},
                params={"email": email},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                existe_memberkit = bool(data) and data != []
        except Exception:
            pass

    if existe_guru or existe_memberkit:
        print(f"⚠️  Email {email} existe mas está inativo (Guru={existe_guru}, MemberKit={existe_memberkit})")
        return "inactive"

    print(f"❌ Email {email} não encontrado em nenhuma base — encaminhando para verificação manual")
    return None


# ─────────────────────────────────────────────
# Funções auxiliares (mantidas por compatibilidade)
# ─────────────────────────────────────────────

def verificar_se_ativo(email: str) -> bool:
    """Retorna True se o aluno estiver ativo em qualquer plataforma."""
    return consultar_aluno_por_email(email) == "active"


def verificar_se_cancelado(email: str) -> bool:
    """Retorna True se o email existir mas não estiver ativo em nenhuma plataforma."""
    return consultar_aluno_por_email(email) == "inactive"


def verificar_status(email: str) -> str:
    """
    Retorna:
        'active'    -> ativo na Guru ou MemberKit
        'inactive'  -> existe mas inativo
        'not_found' -> não encontrado em nenhuma base
    """
    resultado = consultar_aluno_por_email(email)
    if resultado is None:
        return "not_found"
    return resultado
