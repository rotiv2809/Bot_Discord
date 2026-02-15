import discord
from datetime import datetime

# ===== CONFIGURAÇÃO DE NÍVEIS E XP =====
XP_POR_RESPOSTA = 10  # XP base por responder
XP_RESPOSTA_CORRETA_MULTIPLIER = 5  # Multiplicador se acertar

# XP necessário para cada nível (progressão exponencial)
def xp_para_nivel(nivel):
    """Calcula XP necessário para atingir um nível"""
    return int(100 * (nivel ** 1.5))

def calcular_nivel(xp_total):
    """Calcula o nível baseado no XP total"""
    nivel = 1
    while xp_total >= xp_para_nivel(nivel):
        xp_total -= xp_para_nivel(nivel)
        nivel += 1
    return nivel, xp_total  # Retorna (nível atual, XP restante para próximo nível)

# ===== CARGOS DE NÍVEL =====
CARGOS_NIVEIS = {
    1: None,  # Nível 1 não tem cargo
    5: 1431785992267759787,  # ID do cargo Nível 5
    10: 1431798272762314853,  # ID do cargo Nível 10
    15: 1431798301279387709,  # ID do cargo Nível 15
    20: 1431798324649791669,  # ID do cargo Nível 20
    25: 1431798349656358923,  # ID do cargo Nível 25
    30: 1431798368522473563,  # ID do cargo Nível 30
    # Adicione mais níveis conforme necessário
}

async def adicionar_xp(supabase, user_id: int, username: str, guild_id: int, xp_ganho: int, guild: discord.Guild):
    """
    Adiciona XP a um usuário e atualiza seu nível
    Retorna: (novo_xp_total, novo_nivel, subiu_nivel, nivel_anterior)
    """
    try:
        # Buscar XP atual do usuário
        response = supabase.table('user_xp').select('*').eq('discord_user_id', user_id).execute()

        if response.data and len(response.data) > 0:
            # Usuário já existe
            dados = response.data[0]
            xp_atual = dados['xp_total']
            nivel_anterior, _ = calcular_nivel(xp_atual)

            # Adicionar XP
            novo_xp = xp_atual + xp_ganho
            novo_nivel, _ = calcular_nivel(novo_xp)

            # Atualizar no banco
            supabase.table('user_xp').update({
                'xp_total': novo_xp,
                'nivel': novo_nivel,
                'discord_username': username
            }).eq('discord_user_id', user_id).execute()

            subiu_nivel = novo_nivel > nivel_anterior

        else:
            # Primeiro XP do usuário
            novo_xp = xp_ganho
            nivel_anterior = 0
            novo_nivel, _ = calcular_nivel(novo_xp)
            subiu_nivel = novo_nivel > nivel_anterior

            # Inserir no banco
            supabase.table('user_xp').insert({
                'discord_user_id': user_id,
                'discord_username': username,
                'guild_id': guild_id,
                'xp_total': novo_xp,
                'nivel': novo_nivel
            }).execute()

        # Se subiu de nível, adicionar cargo
        if subiu_nivel and novo_nivel in CARGOS_NIVEIS:
            cargo_id = CARGOS_NIVEIS[novo_nivel]
            if cargo_id:
                member = guild.get_member(user_id)
                if member:
                    cargo = guild.get_role(cargo_id)
                    if cargo:
                        await member.add_roles(cargo)
                        print(f"🎖️ Cargo de nível {novo_nivel} adicionado a {username}")

                    # Remover cargos de níveis anteriores
                    for nivel_antigo, cargo_antigo_id in CARGOS_NIVEIS.items():
                        if nivel_antigo < novo_nivel and cargo_antigo_id:
                            cargo_antigo = guild.get_role(cargo_antigo_id)
                            if cargo_antigo and cargo_antigo in member.roles:
                                await member.remove_roles(cargo_antigo)

        return novo_xp, novo_nivel, subiu_nivel, nivel_anterior

    except Exception as e:
        print(f"❌ Erro ao adicionar XP: {e}")
        import traceback
        traceback.print_exc()
        return None, None, False, None

async def consultar_xp(supabase, user_id: int):
    """
    Consulta o XP e nível de um usuário
    Retorna: (xp_total, nivel, xp_para_proximo_nivel)
    """
    try:
        response = supabase.table('user_xp').select('*').eq('discord_user_id', user_id).execute()

        if response.data and len(response.data) > 0:
            dados = response.data[0]
            xp_total = dados['xp_total']

            # Recalcular nível pelo XP total para evitar inconsistências no banco
            nivel_calculado, xp_atual_nivel = calcular_nivel(xp_total)
            xp_proximo_nivel = xp_para_nivel(nivel_calculado)

            if dados.get('nivel') != nivel_calculado:
                supabase.table('user_xp').update({
                    'nivel': nivel_calculado
                }).eq('discord_user_id', user_id).execute()

            return xp_total, nivel_calculado, xp_atual_nivel, xp_proximo_nivel
        else:
            return 0, 1, 0, xp_para_nivel(1)

    except Exception as e:
        print(f"❌ Erro ao consultar XP: {e}")
        return None, None, None, None

async def ranking_xp(supabase, guild_id: int, limite: int = 10):
    """
    Retorna o ranking de XP do servidor
    """
    try:
        response = supabase.table('user_xp') \
            .select('*') \
            .eq('guild_id', guild_id) \
            .order('xp_total', desc=True) \
            .limit(limite) \
            .execute()

        return response.data if response.data else []

    except Exception as e:
        print(f"❌ Erro ao buscar ranking: {e}")
        return []
