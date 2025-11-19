import discord
from discord.ext import commands
from flask import Flask, request
from supabase import create_client, Client
import threading
import os
import asyncio

# =====================================================
# CONFIGURAÇÕES - Lê das variáveis de ambiente
# =====================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ROLE_ID_ALUNO = int(os.getenv("ROLE_ID_ALUNO", "0"))
GURU_API_TOKEN = os.getenv("GURU_API_TOKEN")
PORT = int(os.getenv("PORT", 5000))  # Railway define a porta automaticamente

# =====================================================
# INICIALIZAÇÃO
# =====================================================
# Bot Discord
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Flask (Webhook)
app = Flask(__name__)

# =====================================================
# FUNÇÕES DO BOT DISCORD
# =====================================================

def email_ja_registrado(email: str) -> bool:
    """
    Verifica se o email já está registrado no banco de dados
    
    Args:
        email: Email a ser verificado
    
    Returns:
        bool: True se já existe, False se não existe
    """
    try:
        response = supabase.table("alunos_verificados").select("email").eq("email", email).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"❌ Erro ao verificar email no banco: {e}")
        return False


@bot.command(name="verificar")
async def verificar(ctx, email: str):
    """
    Comando:/verificar email@exemplo.com
    Verifica o email na sua API e dá o cargo de aluno
    """
    await ctx.send(f"🔍 Verificando email: {email}...")
    
    # Verifica se o email já está registrado
    if email_ja_registrado(email):
        await ctx.send("⚠️ Este email já está vinculado a outra conta do Discord!")
        return
    
    # === SUBSTITUA AQUI pela sua chamada de API ===
    # Exemplo:
    # tem_conta = verificar_email_na_api(email)
    tem_conta = True  # Simulação - substitua pela sua lógica real
    
    if tem_conta:
        # Dá o cargo de aluno
        role = ctx.guild.get_role(ROLE_ID_ALUNO)
        await ctx.author.add_roles(role)
        
        # Salva no Supabase
        try:
            discord_id = str(ctx.author.id)
            supabase.table("alunos_verificados").insert({
                "email": email,
                "discord_id": discord_id
            }).execute()
            
            await ctx.send(f"✅ Verificado! Cargo de aluno adicionado.")
        except Exception as e:
            await ctx.send(f"⚠️ Cargo dado, mas erro ao salvar no banco: {e}")
    else:
        await ctx.send("❌ Email não encontrado na base de alunos.")


async def remover_cargo_aluno(discord_id: str):
    """
    Remove o cargo de aluno de um usuário pelo Discord ID
    """
    try:
        # Procura em todos os servidores onde o bot está
        for guild in bot.guilds:
            try:
                member = await guild.fetch_member(int(discord_id))
                role = guild.get_role(ROLE_ID_ALUNO)
                
                if role and role in member.roles:
                    await member.remove_roles(role)
                    print(f"✅ Cargo removido de {member.name} (ID: {discord_id}) no servidor {guild.name}")
                    
                    # Remove do banco de dados
                    supabase.table("alunos_verificados").delete().eq("discord_id", discord_id).execute()
                    return True
            except discord.NotFound:
                continue  # Membro não está neste servidor, tenta o próximo
            except Exception as e:
                print(f"⚠️ Erro ao processar no servidor {guild.name}: {e}")
                continue
                
        print(f"⚠️ Membro {discord_id} não encontrado em nenhum servidor")
        return False
    except Exception as e:
        print(f"❌ Erro ao remover cargo: {e}")
        return False


# =====================================================
# WEBHOOK FLASK
# =====================================================

@app.route("/", methods=["GET"])
def health_check():
    """
    Health check para Railway saber que o serviço está rodando
    """
    return {"status": "online", "bot": "discord-supabase-webhook"}, 200


@app.route("/webhook/guru", methods=["POST"])
def webhook_guru():
    """
    Recebe webhook quando aluno cancela/expira assinatura
    ⚠️ VALIDAÇÃO DE SEGURANÇA: Verifica se é realmente a Guru enviando
    """
    data = request.get_json()
    
    # 🔒 VALIDAÇÃO: Verifica se o api_token é o seu
    api_token_recebido = data.get("api_token")
    if api_token_recebido != GURU_API_TOKEN:
        print(f"⚠️ Tentativa de acesso não autorizado! Token inválido.")
        return {"error": "Unauthorized"}, 401
    
    evento = data.get("last_status")  # Guru usa "last_status" não "event"
    email = data.get("subscriber", {}).get("email")
    
    print(f"📩 Webhook recebido: {evento} - {email}")
    
    # Eventos que indicam que o aluno perdeu acesso
    if evento in ["canceled", "expired", "inactive"]:
        # Busca no Supabase se existe Discord ID vinculado
        try:
            response = supabase.table("alunos_verificados").select("discord_id").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                discord_id = response.data[0]["discord_id"]
                print(f"🔍 Encontrado Discord ID: {discord_id}")
                
                # Remove o cargo (executa de forma assíncrona)
                asyncio.run_coroutine_threadsafe(
                    remover_cargo_aluno(discord_id), 
                    bot.loop
                )
            else:
                print(f"⚠️ Email {email} não encontrado no banco")
                
        except Exception as e:
            print(f"❌ Erro ao processar webhook: {e}")
    
    return {"status": "received"}, 200


# =====================================================
# INICIALIZAÇÃO DOS SERVIÇOS
# =====================================================

def run_flask():
    """Roda o servidor Flask em thread separada"""
    app.run(host="0.0.0.0", port=PORT)


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print(f"✅ Conectado a {len(bot.guilds)} servidor(es)")
    print(f"🌐 Webhook rodando na porta {PORT}")
    print(f"📍 URL: /webhook/guru")


@bot.event
async def on_command_error(ctx, error):
    """Tratamento de erros de comandos"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Uso correto: `/verificar email@exemplo.com`")
    else:
        print(f"❌ Erro no comando: {error}")


if __name__ == "__main__":
    # Inicia Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Inicia o bot Discord
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")