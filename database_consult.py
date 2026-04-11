from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY, SUPABASE_URL_2, SUPABASE_KEY_2

# Supabase antigo — subscriptions + memberkit_members
supabase_old: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supabase novo — assinantes + assinaturas
supabase: Client = create_client(SUPABASE_URL_2, SUPABASE_KEY_2)


# ─────────────────────────────────────────────
# MAPEAMENTO DE CURSOS → CARGOS DO DISCORD
# ─────────────────────────────────────────────

CURSOS_PRINCIPAIS = {
    "espcex":   1492491226237239356,
    "efomm":    1492491305022914721,
    "esa":      1492494369553514658,
    "eear":     1492494507294326864,
    "epcar":    1492494568032174150,
    "afa":      1492494609366913024,
}

CURSOS_SECUNDARIOS = {
    "nivelamento":  1492494698705719387,
    "mentoria":     1492494738610196520,
    "live":         1492494788866347248,
}


def _identificar_cargos(nomes_cursos: list) -> list:
    cargos_principais = []
    cargos_secundarios = []

    for nome in nomes_cursos:
        nome_lower = nome.lower()
        eh_principal = False

        for keyword, cargo_id in CURSOS_PRINCIPAIS.items():
            if keyword in nome_lower:
                eh_principal = True
                if cargo_id and cargo_id not in cargos_principais:
                    cargos_principais.append(cargo_id)
                break

        if not eh_principal:
            for keyword, cargo_id in CURSOS_SECUNDARIOS.items():
                if keyword in nome_lower:
                    if cargo_id and cargo_id not in cargos_secundarios:
                        cargos_secundarios.append(cargo_id)
                    break

    return cargos_principais if cargos_principais else cargos_secundarios


# ─────────────────────────────────────────────
# CONSULTA — NOVO SUPABASE (assinantes)
# ─────────────────────────────────────────────

def _buscar_assinantes(email: str) -> list:
    emails_busca = list({email, email.lower()})
    registros = []

    for em in emails_busca:
        try:
            response = supabase.table("assinantes") \
                .select("status, membership_level_id, expire_date") \
                .eq("email", em) \
                .execute()
            if response.data:
                registros.extend(response.data)
        except Exception as e:
            print(f"❌ Erro ao buscar assinantes ({em}): {e}")

    return registros


# ─────────────────────────────────────────────
# CONSULTA — SUPABASE ANTIGO (subscriptions + memberkit_members)
# ─────────────────────────────────────────────

def _buscar_legado(email: str) -> tuple:
    """
    Retorna (existe: bool, ativo: bool) consultando as tabelas antigas.
    """
    emails_busca = list({email, email.lower()})
    existe = False
    ativo = False

    for em in emails_busca:
        # Guru — subscriptions
        try:
            r = supabase_old.table("subscriptions") \
                .select("last_status") \
                .eq("contact_email", em) \
                .execute()
            if r.data:
                existe = True
                if any(row.get("last_status") == "active" for row in r.data):
                    ativo = True
        except Exception as e:
            print(f"❌ Erro ao buscar subscriptions ({em}): {e}")

        # MemberKit — memberkit_members
        try:
            r = supabase_old.table("memberkit_members") \
                .select("status") \
                .eq("email", em) \
                .execute()
            if r.data:
                existe = True
                if any(row.get("status") == "active" for row in r.data):
                    ativo = True
        except Exception as e:
            print(f"❌ Erro ao buscar memberkit_members ({em}): {e}")

    return existe, ativo


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def consultar_aluno_por_email(email: str):
    """
    Consulta as 3 tabelas: assinantes (novo), subscriptions e memberkit_members (antigo).

    Retorna:
        'active'   -> ativo em qualquer das fontes
        'inactive' -> existe em alguma mas inativo em todas
        None       -> não encontrado em nenhuma → verificação manual
    """
    # 1. Novo Supabase
    registros = _buscar_assinantes(email)
    if registros:
        statuses = [r.get("status") for r in registros]
        if "active" in statuses:
            print(f"✅ Aluno ATIVO (assinantes) — {email}")
            return "active"
        # existe mas inativo no novo — ainda verifica legado antes de retornar inactive
        existe_novo = True
    else:
        existe_novo = False

    # 2. Supabase antigo
    existe_legado, ativo_legado = _buscar_legado(email)
    if ativo_legado:
        print(f"✅ Aluno ATIVO (legado) — {email}")
        return "active"

    if existe_novo or existe_legado:
        print(f"⚠️  Email {email} existe mas INATIVO em todas as bases")
        return "inactive"

    print(f"❌ Email {email} não encontrado em nenhuma base → verificação manual")
    return None


def consultar_cargos_por_email(email: str) -> list:
    """
    Retorna lista de IDs de cargos baseado nos cursos ativos na tabela assinantes.
    """
    emails_busca = list({email, email.lower()})
    nomes_cursos = []

    for em in emails_busca:
        try:
            response = supabase.table("assinantes") \
                .select("membership_level_id") \
                .eq("email", em) \
                .eq("status", "active") \
                .execute()

            if not response.data:
                continue

            level_ids = list({r["membership_level_id"] for r in response.data if r.get("membership_level_id")})
            if not level_ids:
                continue

            levels = supabase.table("assinaturas") \
                .select("id, name") \
                .in_("id", level_ids) \
                .execute()

            for row in (levels.data or []):
                nome = row.get("name")
                if nome and nome not in nomes_cursos:
                    nomes_cursos.append(nome)

        except Exception as e:
            print(f"❌ Erro ao consultar cursos ({em}): {e}")

    if not nomes_cursos:
        print(f"ℹ️  Nenhum curso ativo para {email}")
        return []

    print(f"📚 Cursos ativos de {email}: {nomes_cursos}")
    cargos = _identificar_cargos(nomes_cursos)
    print(f"🎖️  Cargos a atribuir: {cargos}")
    return cargos


# ─────────────────────────────────────────────
# VERIFICAÇÃO DE EXPIRAÇÃO — ÚLTIMA ASSINATURA
# ─────────────────────────────────────────────

def consultar_expiracao_em_dias(email: str):
    """
    Retorna quantos dias faltam para a ÚLTIMA assinatura ativa vencer.
    Consulta assinantes (novo) e subscriptions/memberkit (antigo).
    """
    from datetime import date, datetime, timezone

    hoje = date.today()
    todas_datas = []

    # Novo — assinantes.expire_date
    for r in _buscar_assinantes(email):
        if r.get("status") != "active":
            continue
        end_raw = r.get("expire_date")
        if end_raw and isinstance(end_raw, str):
            try:
                todas_datas.append(date.fromisoformat(end_raw))
            except ValueError:
                pass

    # Antigo — subscriptions.cycle_end_date
    emails_busca = list({email, email.lower()})
    for em in emails_busca:
        try:
            r = supabase_old.table("subscriptions") \
                .select("cycle_end_date, last_status") \
                .eq("contact_email", em) \
                .eq("last_status", "active") \
                .execute()
            for row in (r.data or []):
                end_raw = row.get("cycle_end_date")
                if end_raw and isinstance(end_raw, str):
                    try:
                        todas_datas.append(date.fromisoformat(end_raw))
                    except ValueError:
                        pass
        except Exception as e:
            print(f"❌ Erro ao buscar expiração subscriptions ({em}): {e}")

        # Antigo — memberkit_members.expires_at
        try:
            r = supabase_old.table("memberkit_members") \
                .select("expires_at, status") \
                .eq("email", em) \
                .eq("status", "active") \
                .execute()
            for row in (r.data or []):
                end_raw = row.get("expires_at")
                if end_raw and isinstance(end_raw, str):
                    try:
                        dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                        todas_datas.append(dt.astimezone(timezone.utc).date())
                    except ValueError:
                        pass
        except Exception as e:
            print(f"❌ Erro ao buscar expiração memberkit ({em}): {e}")

    if not todas_datas:
        return None

    return (max(todas_datas) - hoje).days


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