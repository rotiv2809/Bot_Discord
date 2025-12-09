import discord
from discord.ext import commands
from supabase import create_client, Client
from dados import DISCORD_TOKEN, SUPABASE_KEY, SUPABASE_URL, ROLE_ID_ALUNO, GURU_API_TOKEN
from database_consult import *
import sys
import os
import random


ID_DO_CANAL_VERIFICACOES = 1447893793113247836
INSTANCE_ID = random.randint(1000, 9999)
print(f"🆔 Instância iniciada: {INSTANCE_ID}")


print("=" * 50)
print("🔧 Verificando variáveis...")
print("=" * 50)

print(f"DISCORD_TOKEN: {'✅ Definido' if DISCORD_TOKEN else '❌ None/Vazio'}")
print(f"SUPABASE_URL: {'✅ Definido' if SUPABASE_URL else '❌ None/Vazio'}")
print(f"SUPABASE_KEY: {'✅ Definido' if SUPABASE_KEY else '❌ None/Vazio'}")
print(f"GURU_API_TOKEN: {'✅ Definido' if GURU_API_TOKEN else '❌ None/Vazio'}")
print(f"ROLE_ID_ALUNO: {ROLE_ID_ALUNO if ROLE_ID_ALUNO != 0 else '❌ Não definido'}")
print("=" * 50)


# INICIALIZAÇÃO BOT

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


# FUNÇÕES DO BOT DISCORD

def email_ja_registrado(email: str) -> bool:
    try:
        response = supabase.table("verificacoes").select("email").eq("email", email).execute()
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
    try:
        synced = await bot.tree.sync()
        print(f"🌿 Slash commands sincronizados ({len(synced)} comandos).")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")


@bot.command(name="verificar")
async def verificar(ctx:commands.Context, email: str):
    
    print(f"📧 [INSTÂNCIA {INSTANCE_ID}] Verificação solicitada por {ctx.author} - Email: {email}")
    
    await ctx.send(f"🔍 Verificando email: {email}...")
    
    if email_ja_registrado(email):
        await ctx.send("⚠️ Este email já está vinculado a outra conta do Discord! Caso seja um erro, por favor abra um ticket.")
        return
    
    aluno = consultar_aluno_por_email(email)
    
    if aluno:
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
            username = str(ctx.author.display_name)
            guild_id = ctx.guild.id
            await salvar_verificacao(discord_id=discord_id, email=email, username=username, guild_id=guild_id)
            
            await ctx.send(f"✅ Verificado! Cargo de aluno adicionado.")
            print(f"✅ {ctx.author} verificado e salvo no banco")
        except Exception as e:
            await ctx.send(f"⚠️ Cargo dado, mas erro ao salvar no banco: {e}")
            print(f"❌ Erro ao salvar no Supabase: {e}")
    else:
        await ctx.send("❌ Email não encontrado na base de alunos.")
        print(f"❌ Email {email} não encontrado na API")
        
async def salvar_verificacao(discord_id: str, email: str, username: str, guild_id: str) -> dict:
    """Salva a verificação no Supabase com os parâmetros corretos da sua base"""
    try:
        data = {
            'discord_id': discord_id,
            'email': email,
            'username': username,
            'guild_id': guild_id,
            'verificado_em': discord.datetime.now().isoformat()
        }
        
        response = supabase.table('verificacoes').insert(data).execute()
        
        print(f"✅ Verificação salva: {username} ({email})")
        return {'success': True, 'data': response.data}

    
    except Exception as e:
        print(f"❌ Erro ao salvar no Supabase: {e}")
        return {'success': False, 'error': str(e)}





if __name__ == "__main__":
    print("🚀 Iniciando serviços...\n")

    # Inicia bot Discord
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Token do Discord inválido!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")
        sys.exit(1)
        
