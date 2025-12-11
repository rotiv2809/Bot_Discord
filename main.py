import discord
from discord.ext import commands
from supabase import create_client, Client
from dados import DISCORD_TOKEN, SUPABASE_KEY, SUPABASE_URL, ROLE_ID_ALUNO, GURU_API_TOKEN
from database_consult import *
import asyncio
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


import discord
from discord import ui

# ID da categoria onde os tickets serão criados
CATEGORIA_VERIFICACAO_ID = 1432097231280017519  

@bot.tree.command(name="verificar", description="Abrir ticket de verificação")
async def verificar(interaction: discord.Interaction):
    
    guild = interaction.guild
    user = interaction.user
    
    # Verifica se já tem um ticket aberto
    ticket_existente = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
    if ticket_existente:
        await interaction.response.send_message(f"❌ Você já tem um ticket aberto: {ticket_existente.mention}", ephemeral=True)
        return
    
    # Busca a categoria
    categoria = guild.get_channel(CATEGORIA_VERIFICACAO_ID)
    if not categoria:
        await interaction.response.send_message("❌ Categoria de tickets não configurada!", ephemeral=True)
        return
    
    # Cria o canal do ticket
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    canal_ticket = await categoria.create_text_channel(
        name=f"ticket-{user.name}",
        overwrites=overwrites
    )
    
    await interaction.response.send_message(f"✅ Ticket criado: {canal_ticket.mention}", ephemeral=True)
    
    await canal_ticket.send(
        f"🎫 **Ticket de Verificação - {user.mention}**\n\n"
        f"Digite seu email para verificação:\n"
        f"`seu@email.com`\n\n"
        f"Use `/fechar` para fechar este ticket."
    )

@bot.tree.command(name="fechar", description="Fechar seu ticket de verificação")
async def fechar(interaction: discord.Interaction):
    
    # Verifica se está em um canal de ticket
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ Este comando só funciona em tickets!", ephemeral=True)
        return
    
    await interaction.response.send_message("🗑️ Fechando ticket em 3 segundos...")
    await asyncio.sleep(3)
    await interaction.channel.delete()

@bot.event
async def on_message(message):
    
    # Ignora mensagens do bot
    if message.author.bot:
        return
    
    # Verifica se é um canal de ticket
    if not message.channel.name.startswith("ticket-"):
        return
    
    email = message.content.strip()
    
    # Valida se parece com email
    if "@" not in email or "." not in email:
        await message.channel.send("⚠️ Por favor, envie um email válido!")
        return
    
    await message.channel.send(f"🔍 Verificando email: {email}...")
    
    if email_ja_registrado(email):
        await message.channel.send("⚠️ Este email já está vinculado a outra conta do Discord!")
        return
    
    aluno = consultar_aluno_por_email(email)
    
    if aluno:
        role = message.guild.get_role(ROLE_ID_ALUNO)
        
        if not role:
            await message.channel.send(f"❌ Erro: Cargo não encontrado!")
            return
        
        try:
            await message.author.add_roles(role)
            
            discord_id = str(message.author.id)
            username = str(message.author.display_name)
            guild_id = message.guild.id
            await salvar_verificacao(discord_id=discord_id, email=email, username=username, guild_id=guild_id)
            
            await message.channel.send(
                f"✅ **Verificado com sucesso!**\n"
                f"Cargo de aluno adicionado.\n\n"
                f"Este ticket será fechado em 5 segundos..."
            )
            
            print(f"✅ {message.author} verificado - Email: {email}")
            
            await asyncio.sleep(5)
            await message.channel.delete()
            
        except Exception as e:
            await message.channel.send(f"❌ Erro: {e}")
            print(f"❌ Erro na verificação: {e}")
    else:
        await message.channel.send("❌ Email não encontrado na base de alunos.")
        print(f"❌ Email {email} não encontrado")
        
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
        
