import discord
from discord.ext import commands
from supabase import create_client, Client
from functions.request_api import verificar_aluno
from dados import DISCORD_TOKEN, SUPABASE_KEY, SUPABASE_URL, ROLE_ID_ALUNO, GURU_API_TOKEN
from flask import Flask
import threading
import sys
import os
import random

# =====================================================
# ID ÚNICO DA INSTÂNCIA (pra debug)
# =====================================================
INSTANCE_ID = random.randint(1000, 9999)
print(f"🆔 Instância iniciada: {INSTANCE_ID}")

# =====================================================
# CARREGAMENTO E VALIDAÇÃO DE VARIÁVEIS
# =====================================================

print("=" * 50)
print("🔧 Verificando variáveis...")
print("=" * 50)

# Debug das variáveis (SEM MOSTRAR OS VALORES!)
print(f"DISCORD_TOKEN: {'✅ Definido' if DISCORD_TOKEN else '❌ None/Vazio'}")
print(f"SUPABASE_URL: {'✅ Definido' if SUPABASE_URL else '❌ None/Vazio'}")
print(f"SUPABASE_KEY: {'✅ Definido' if SUPABASE_KEY else '❌ None/Vazio'}")
print(f"GURU_API_TOKEN: {'✅ Definido' if GURU_API_TOKEN else '❌ None/Vazio'}")
print(f"ROLE_ID_ALUNO: {ROLE_ID_ALUNO if ROLE_ID_ALUNO != 0 else '❌ Não definido'}")
print("=" * 50)

# Valida variáveis críticas
variaveis_faltando = []

if not DISCORD_TOKEN:
    variaveis_faltando.append("DISCORD_TOKEN")
if not SUPABASE_URL:
    variaveis_faltando.append("SUPABASE_URL")
if not SUPABASE_KEY:
    variaveis_faltando.append("SUPABASE_KEY")
if not GURU_API_TOKEN:
    variaveis_faltando.append("GURU_API_TOKEN")
if ROLE_ID_ALUNO == 0:
    variaveis_faltando.append("ROLE_ID_ALUNO")

if variaveis_faltando:
    print("\n❌ ERRO: Variáveis de ambiente não configuradas:")
    for var in variaveis_faltando:
        print(f"   - {var}")
    print("\n📝 Configure no Render ou crie arquivo .env")
    sys.exit(1)

print("✅ Todas as variáveis carregadas!\n")

# =====================================================
# FLASK (só pra Render não reclamar)
# =====================================================
PORT = int(os.getenv("PORT", 10000))
app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "online", "instance": INSTANCE_ID}, 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=True)

# =====================================================
# INICIALIZAÇÃO BOT
# =====================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Cliente Supabase criado com sucesso")
except Exception as e:
    print(f"❌ Erro ao criar cliente Supabase: {e}")
    sys.exit(1)

# =====================================================
# FUNÇÕES DO BOT DISCORD
# =====================================================

def email_ja_registrado(email: str) -> bool:
    try:
        response = supabase.table("alunos_verificados").select("email").eq("email", email).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"❌ Erro ao verificar email no banco: {e}")
        return False


@bot.event
async def on_ready():
    print(f"\n{'=' * 50}")
    print(f"🤖 Bot conectado como: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Servidores: {len(bot.guilds)}")
    print(f"🔢 Instância: {INSTANCE_ID}")
    print(f"{'=' * 50}\n")


@bot.command(name="verificar")
async def verificar(ctx, email: str):
    """
    Comando: /verificar email@exemplo.com
    Verifica o email na sua API e dá o cargo de aluno
    """
    
    print(f"📧 [INSTÂNCIA {INSTANCE_ID}] Verificação solicitada por {ctx.author} - Email: {email}")
    
    await ctx.send(f"🔍 Verificando email: {email}...")
    
    if email_ja_registrado(email):
        await ctx.send("⚠️ Este email já está vinculado a outra conta do Discord! Caso seja um erro, por favor abra um ticket.")
        return
    
    tem_conta = verificar_aluno(email)
    
    if tem_conta:
        role = ctx.guild.get_role(ROLE_ID_ALUNO)
        
        if not role:
            await ctx.send(f"❌ Erro: Cargo com ID {ROLE_ID_ALUNO} não encontrado no servidor!")
            print(f"❌ ROLE_ID_ALUNO {ROLE_ID_ALUNO} não existe no servidor {ctx.guild.name}")
            return
        
        try:
            await ctx.author.add_roles(role)
            print(f"✅ Cargo adicionado para {ctx.author}")
        except discord.Forbidden:
            await ctx.send("❌ Erro: Bot não tem permissão para adicionar cargos!")
            return
        except Exception as e:
            await ctx.send(f"❌ Erro ao adicionar cargo: {e}")
            return
        
        try:
            discord_id = str(ctx.author.id)
            supabase.table("alunos_verificados").insert({
                "email": email,
                "discord_id": discord_id
            }).execute()
            
            await ctx.send(f"✅ Verificado! Cargo de aluno adicionado.")
            print(f"✅ {ctx.author} verificado e salvo no banco")
        except Exception as e:
            await ctx.send(f"⚠️ Cargo dado, mas erro ao salvar no banco: {e}")
            print(f"❌ Erro ao salvar no Supabase: {e}")
    else:
        await ctx.send("❌ Email não encontrado na base de alunos.")
        print(f"❌ Email {email} não encontrado na API")


if __name__ == "__main__":
    print("🚀 Iniciando serviços...\n")
    
    # Inicia Flask (pra Render não reclamar)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Inicia bot Discord
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Token do Discord inválido!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")
        sys.exit(1)