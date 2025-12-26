import discord
from discord.ext import commands
from supabase import create_client, Client
from dados import DISCORD_TOKEN, SUPABASE_KEY, SUPABASE_URL, ROLE_ID_ALUNO
import sys
import random

# Importa os módulos organizados
from scripts.events import setup_events
from scripts.commands import setup_commands

# Variáveis globais
ID_DO_CANAL_VERIFICACOES = 1450481303354081331
CATEGORIA_VERIFICACAO_ID = 1432097231280017519
INSTANCE_ID = random.randint(1000, 9999)

print(f"🆔 Instância iniciada: {INSTANCE_ID}")
print("=" * 50)
print("🔧 Verificando variáveis...")
print("=" * 50)
print(f"DISCORD_TOKEN: {'✅ Definido' if DISCORD_TOKEN else '❌ None/Vazio'}")
print(f"SUPABASE_URL: {'✅ Definido' if SUPABASE_URL else '❌ None/Vazio'}")
print(f"SUPABASE_KEY: {'✅ Definido' if SUPABASE_KEY else '❌ None/Vazio'}")
print(f"ROLE_ID_ALUNO: {ROLE_ID_ALUNO if ROLE_ID_ALUNO != 0 else '❌ Não definido'}")
print("=" * 50)

# Inicialização do bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Inicializa Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dicionários compartilhados
tickets_verificacao_ativa = set()
questoes_em_criacao = {}

# Contexto global para compartilhar com os módulos
bot_context = {
    'bot': bot,
    'supabase': supabase,
    'tickets_verificacao_ativa': tickets_verificacao_ativa,
    'questoes_em_criacao': questoes_em_criacao,
    'ID_DO_CANAL_VERIFICACOES': ID_DO_CANAL_VERIFICACOES,
    'CATEGORIA_VERIFICACAO_ID': CATEGORIA_VERIFICACAO_ID,
    'ROLE_ID_ALUNO': ROLE_ID_ALUNO,
    'INSTANCE_ID': INSTANCE_ID
}

@bot.event
async def on_ready():
    print(f"\n{'=' * 50}")
    print(f"🤖 Bot conectado como: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Servidores: {len(bot.guilds)}")
    print(f"🔢 Instância: {INSTANCE_ID}")
    print(f"{'=' * 50}\n")
    
    # Setup de comandos e eventos
    setup_commands(bot_context)
    setup_events(bot_context)
    
    try:
        synced = await bot.tree.sync()
        print(f"🌿 Slash commands sincronizados ({len(synced)} comandos):")
        for cmd in synced:
            print(f"   - /{cmd.name}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando serviços...\n")
    
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Token do Discord inválido!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")
        sys.exit(1)