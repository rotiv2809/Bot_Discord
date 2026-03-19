from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY

# Único cliente Supabase — contém tabelas da Guru e da MemberKit
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────
# GURU — tabela: subscriptions
# ─────────────────────────────────────────────

def _consultar_guru(email: str):
    """
    Retorna (existe: bool, ativo: bool)
    Tabela: subscriptions | campo email: contact_email | status: last_status
    """
    try:
        response = supabase.table("subscriptions") \
            .select("last_status") \
            .eq("contact_email", email) \
            .execute()

        if not response.data:
            return False, False

        statuses = [row.get("last_status") for row in response.data]
        return True, "active" in statuses

    except Exception as e:
        print(f"❌ Erro ao consultar Guru: {e}")
        return False, False


# ─────────────────────────────────────────────
# MEMBERKIT — tabela: memberkit_members
# ─────────────────────────────────────────────

def _consultar_memberkit(email: str):
    """
    Retorna (existe: bool, ativo: bool)
    Tabela: memberkit_members | campo email: email | status: status
    """
    try:
        response = supabase.table("memberkit_members") \
            .select("status") \
            .eq("email", email) \
            .execute()

        if not response.data:
            return False, False

        statuses = [row.get("status") for row in response.data]
        return True, "active" in statuses

    except Exception as e:
        print(f"❌ Erro ao consultar MemberKit: {e}")
        return False, False


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def consultar_aluno_por_email(email: str):
    """
    Consulta Guru (subscriptions) e MemberKit (memberkit_members) no mesmo Supabase.

    Retorna:
        'active'   -> ativo em QUALQUER das duas plataformas → dá o cargo
        'inactive' -> email existe mas inativo nas duas       → sem cargo
        None       -> não encontrado em nenhuma              → verificação manual
    """
    existe_guru,      ativo_guru      = _consultar_guru(email)
    existe_memberkit, ativo_memberkit = _consultar_memberkit(email)

    if ativo_guru or ativo_memberkit:
        origem = []
        if ativo_guru:      origem.append("Guru")
        if ativo_memberkit: origem.append("MemberKit")
        print(f"✅ Aluno ATIVO em: {', '.join(origem)} — {email}")
        return "active"

    if existe_guru or existe_memberkit:
        print(f"⚠️  Email {email} existe mas INATIVO (Guru={existe_guru}, MemberKit={existe_memberkit})")
        return "inactive"

    print(f"❌ Email {email} não encontrado em nenhuma base → verificação manual")
    return None


# ─────────────────────────────────────────────
# VERIFICAÇÃO DE EXPIRAÇÃO EM 7 DIAS
# ─────────────────────────────────────────────

def consultar_expiracao_em_dias(email: str):
    """
    Verifica se a assinatura do aluno expira nos próximos N dias.

    Retorna o número de dias até expirar, ou None se não encontrar data.
    Prioriza MemberKit (expires_at), depois Guru (cycle_end_date).
    """
    from datetime import date, datetime, timezone

    hoje = date.today()
    menor_dias = None

    # MemberKit — expires_at (timestamp with time zone)
    try:
        response = supabase.table("memberkit_members") \
            .select("expires_at, status, unlimited") \
            .eq("email", email) \
            .eq("status", "active") \
            .execute()

        for row in (response.data or []):
            if row.get("unlimited"):
                continue  # ilimitado, não avisa
            expires_raw = row.get("expires_at")
            if not expires_raw:
                continue
            # Parse ISO timestamp
            if isinstance(expires_raw, str):
                expires_dt = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
                expires_date = expires_dt.astimezone(timezone.utc).date()
            else:
                continue
            dias = (expires_date - hoje).days
            if menor_dias is None or dias < menor_dias:
                menor_dias = dias

    except Exception as e:
        print(f"❌ Erro ao consultar expiração MemberKit: {e}")

    # Guru — cycle_end_date (date)
    try:
        response = supabase.table("subscriptions") \
            .select("cycle_end_date, last_status") \
            .eq("contact_email", email) \
            .eq("last_status", "active") \
            .execute()

        for row in (response.data or []):
            end_raw = row.get("cycle_end_date")
            if not end_raw:
                continue
            if isinstance(end_raw, str):
                end_date = date.fromisoformat(end_raw)
            else:
                continue
            dias = (end_date - hoje).days
            if menor_dias is None or dias < menor_dias:
                menor_dias = dias

    except Exception as e:
        print(f"❌ Erro ao consultar expiração Guru: {e}")

    return menor_dias


# ─────────────────────────────────────────────
# Funções auxiliares (compatibilidade)
# ─────────────────────────────────────────────

def verificar_se_ativo(email: str) -> bool:
    return consultar_aluno_por_email(email) == "active"

def verificar_se_cancelado(email: str) -> bool:
    return consultar_aluno_por_email(email) == "inactive"

def verificar_status(email: str) -> str:
    resultado = consultar_aluno_por_email(email)
    return "not_found" if resultado is None else resultado