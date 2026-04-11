from supabase import create_client, Client
from dados import SUPABASE_URL_2, SUPABASE_KEY_2

supabase: Client = create_client(SUPABASE_URL_2, SUPABASE_KEY_2)


# ─────────────────────────────────────────────
# MAPEAMENTO DE CURSOS → CARGOS DO DISCORD
# ─────────────────────────────────────────────
# Preencha os IDs dos cargos conforme necessário.
# A chave é uma palavra-chave que aparece no nome do curso (case-insensitive).

CURSOS_PRINCIPAIS = {
    "espcex":   1492491226237239356,  # ← ID do cargo EsPCEx
    "efomm":    1492491305022914721,  # ← ID do cargo EFOMM
    "esa":      1492494369553514658,  # ← ID do cargo ESA
    "eear":     1492494507294326864,  # ← ID do cargo EEAR
    "epcar":    1492494568032174150,  # ← ID do cargo EPCAR
    "afa":      1492494609366913024,  # ← ID do cargo AFA
}

CURSOS_SECUNDARIOS = {
    "nivelamento":  1492494698705719387,  # ← ID do cargo Nivelamento
    "mentoria":     1492494738610196520,  # ← ID do cargo Mentoria
    "live":         1492494788866347248,  # ← ID do cargo Live
}


def _identificar_cargos(nomes_cursos: list) -> list:
    """
    Dado uma lista de nomes de cursos ativos, retorna os IDs de cargo
    que devem ser atribuídos ao aluno.

    Regra:
    - Se tiver qualquer curso principal → retorna só os cargos principais
    - Se tiver apenas cursos secundários → retorna os cargos secundários
    """
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
# CONSULTAS NA TABELA assinantes
# ─────────────────────────────────────────────

def _buscar_assinantes(email: str) -> list:
    """
    Busca todos os registros do email na tabela assinantes.
    Tenta o email original e em minúsculo.
    """
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
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def consultar_aluno_por_email(email: str):
    """
    Consulta a tabela assinantes.

    Retorna:
        'active'   -> tem ao menos uma assinatura ativa
        'inactive' -> email existe mas sem assinatura ativa
        None       -> não encontrado → verificação manual
    """
    registros = _buscar_assinantes(email)

    if not registros:
        print(f"❌ Email {email} não encontrado → verificação manual")
        return None

    statuses = [r.get("status") for r in registros]

    if "active" in statuses:
        print(f"✅ Aluno ATIVO — {email}")
        return "active"

    print(f"⚠️  Email {email} existe mas INATIVO")
    return "inactive"


def consultar_cargos_por_email(email: str) -> list:
    """
    Retorna lista de IDs de cargos do Discord que o aluno deve receber,
    baseado nos cursos ativos na tabela assinantes.
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
    Só avisa quando não vai sobrar nenhuma assinatura ativa depois.
    """
    from datetime import date

    hoje = date.today()
    registros = _buscar_assinantes(email)

    datas = []
    for r in registros:
        if r.get("status") != "active":
            continue
        end_raw = r.get("expire_date")
        if end_raw and isinstance(end_raw, str):
            try:
                datas.append(date.fromisoformat(end_raw))
            except ValueError:
                pass

    if not datas:
        return None

    return (max(datas) - hoje).days


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