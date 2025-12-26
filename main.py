import discord
from discord.ext import commands
from supabase import create_client, Client
from dados import DISCORD_TOKEN, SUPABASE_KEY, SUPABASE_URL, ROLE_ID_ALUNO, GURU_API_TOKEN
from database_consult import *
from discord import ui
import asyncio
import sys
import os
import random


ID_DO_CANAL_VERIFICACOES = 1450481303354081331
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

# Dicionário para controlar tickets em modo de verificação
tickets_verificacao_ativa = set()


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


# ID da categoria onde os tickets serão criados
CATEGORIA_VERIFICACAO_ID = 1432097231280017519  

@bot.tree.command(name="verificar", description="Abrir ticket de verificação")
async def verificar(interaction: discord.Interaction):
    
    guild = interaction.guild
    user = interaction.user
    
    # Verifica se já tem o cargo de aluno
    role_aluno = guild.get_role(ROLE_ID_ALUNO)
    if role_aluno and role_aluno in user.roles:
        await interaction.response.send_message("❌ Você já está verificado como aluno!", ephemeral=True)
        return
    
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
    
    # Marca este ticket como ativo para verificação
    tickets_verificacao_ativa.add(canal_ticket.id)
    
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
    
    # Remove o ticket da lista de verificação ativa
    tickets_verificacao_ativa.discard(interaction.channel.id)
    
    await interaction.response.send_message("🗑️ Fechando ticket em 3 segundos...")
    await asyncio.sleep(3)
    await interaction.channel.delete()

@bot.event
async def on_message(message):
    
    # Ignora mensagens do bot
    if message.author.bot:
        return
    
    # Limpa mensagens no canal de verificações (exceto o comando /verificar)
    if message.channel.id == ID_DO_CANAL_VERIFICACOES:
        # Deleta qualquer mensagem que não seja o comando /verificar
        await message.delete()
        try:
            await message.author.send("⚠️ Use apenas o comando `/verificar` neste canal!")
        except:
            pass  # Caso o usuário tenha DM desabilitada
        return
    
    # Verifica se é um canal de ticket E se está marcado para verificação
    if not message.channel.name.startswith("ticket-"):
        return
    
    # MUDANÇA PRINCIPAL: só processa se o ticket estiver na lista de verificação
    if message.channel.id not in tickets_verificacao_ativa:
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

    # 🔧 CORREÇÃO: Verifica se aluno não é None antes de acessar índices
    if aluno is None or not aluno[0]:
        await message.channel.send("❌ Email não encontrado na base de alunos.")
        print(f"❌ Email {email} não encontrado")
        return  # Mantém o ticket ativo para nova tentativa

    # Se chegou aqui, aluno foi encontrado
    role = message.guild.get_role(ROLE_ID_ALUNO)

    if not role:
        await message.channel.send(f"❌ Erro: Cargo não encontrado!")
        return

    try:
        if aluno[1] == 'active':
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
        
            # Remove da lista antes de fechar
            tickets_verificacao_ativa.discard(message.channel.id)
            
            await asyncio.sleep(5)
            await message.channel.delete()
        else:
            await message.channel.send(
                "❌ Aluno encontrado, mas inscrição não ativa, por que não voltar a ser aluno?"
            )
            # Não remove o ticket da lista, permitindo nova tentativa
        
    except Exception as e:
        await message.channel.send(f"❌ Erro: {e}")
        print(f"❌ Erro na verificação: {e}")
        
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
    
# Dicionário para armazenar os dados das questões em criação
questoes_em_criacao = {}

class DescricaoModal(ui.Modal, title="Descrição da Questão"):
    """Modal para inserir a descrição da questão"""
    
    descricao = ui.TextInput(
        label="Descrição",
        placeholder="Digite a descrição da questão aqui...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        # Salva a descrição no dicionário
        if self.user_id not in questoes_em_criacao:
            questoes_em_criacao[self.user_id] = {}
        
        questoes_em_criacao[self.user_id]['descricao'] = self.descricao.value
        
        await interaction.response.send_message(
            f"✅ Descrição salva com sucesso!\n\n**Preview:**\n{self.descricao.value[:100]}...",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id)


class BotoesQuestaoView(ui.View):
    """View com os botões para preencher os campos da questão"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="📝 Descrição", style=discord.ButtonStyle.primary, custom_id="btn_descricao")
    async def button_descricao(self, interaction: discord.Interaction, button: ui.Button):
        # Abre o modal de descrição
        modal = DescricaoModal(self.user_id)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🖼️ Imagem", style=discord.ButtonStyle.secondary, custom_id="btn_imagem")
    async def button_imagem(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "📷 Envie a URL da imagem ou faça upload no próximo canal de mensagens.",
            ephemeral=True
        )
        # TODO: Implementar lógica de upload de imagem
    
    @ui.button(label="📚 Matéria", style=discord.ButtonStyle.secondary, custom_id="btn_materia")
    async def button_materia(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "📚 Selecione a matéria (dropdown a ser implementado)",
            ephemeral=True
        )
        # TODO: Implementar dropdown de matérias
    
    @ui.button(label="⭐ Nível", style=discord.ButtonStyle.secondary, custom_id="btn_nivel")
    async def button_nivel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "⭐ Selecione o nível (dropdown a ser implementado)",
            ephemeral=True
        )
        # TODO: Implementar dropdown de níveis
    
    @ui.button(label="🏷️ Etiqueta", style=discord.ButtonStyle.secondary, custom_id="btn_etiqueta")
    async def button_etiqueta(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "🏷️ Digite as etiquetas separadas por vírgula",
            ephemeral=True
        )
        # TODO: Implementar input de etiquetas
    
    @ui.button(label="✅ Finalizar", style=discord.ButtonStyle.success, custom_id="btn_finalizar", row=2)
    async def button_finalizar(self, interaction: discord.Interaction, button: ui.Button):
        dados = questoes_em_criacao.get(self.user_id, {})
        
        # Validação básica
        if not dados.get('descricao'):
            await interaction.response.send_message(
                "❌ A descrição é obrigatória!",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "✅ Questão criada com sucesso!\n\n"
            f"**Dados salvos:**\n"
            f"Descrição: {dados.get('descricao', 'N/A')[:50]}...",
            ephemeral=True
        )
        
        # Limpa os dados
        questoes_em_criacao.pop(self.user_id, None)
    
    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="btn_cancelar", row=2)
    async def button_cancelar(self, interaction: discord.Interaction, button: ui.Button):
        questoes_em_criacao.pop(self.user_id, None)
        await interaction.message.delete()
        await interaction.response.send_message(
            "🗑️ Criação de questão cancelada.",
            ephemeral=True
        )


async def atualizar_embed_questao(interaction: discord.Interaction, user_id: int):
    """Atualiza o embed com os dados preenchidos"""
    dados = questoes_em_criacao.get(user_id, {})
    
    embed = discord.Embed(
        title="📋 Criar Nova Questão",
        description="Preencha os campos abaixo para criar uma questão:",
        color=discord.Color.blue()
    )
    
    # Adiciona os campos preenchidos
    embed.add_field(
        name="📝 Descrição",
        value=dados.get('descricao', '*Não preenchido*')[:100] + "..." if dados.get('descricao') else "*Não preenchido*",
        inline=False
    )
    
    embed.add_field(
        name="🖼️ Imagem",
        value=dados.get('imagem', '*Não preenchido*'),
        inline=True
    )
    
    embed.add_field(
        name="📚 Matéria",
        value=dados.get('materia', '*Não preenchido*'),
        inline=True
    )
    
    embed.add_field(
        name="⭐ Nível",
        value=dados.get('nivel', '*Não preenchido*'),
        inline=True
    )
    
    embed.add_field(
        name="🏷️ Etiqueta",
        value=dados.get('etiqueta', '*Não preenchido*'),
        inline=True
    )
    
    embed.set_footer(text="Clique nos botões abaixo para preencher cada campo")
    
    # Busca a mensagem original e atualiza
    try:
        message = await interaction.channel.fetch_message(interaction.message.id)
        await message.edit(embed=embed)
    except:
        pass


@bot.tree.command(name="criar_questao", description="Criar uma nova questão para o sistema")
async def criar_questao(interaction: discord.Interaction):
    """Comando para iniciar a criação de uma questão"""
    
    user_id = interaction.user.id
    
    # Inicializa os dados da questão
    questoes_em_criacao[user_id] = {}
    
    # Cria o embed inicial
    embed = discord.Embed(
        title="📋 Criar Nova Questão",
        description="Preencha os campos abaixo para criar uma questão:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📝 Descrição", value="*Não preenchido*", inline=False)
    embed.add_field(name="🖼️ Imagem", value="*Não preenchido*", inline=True)
    embed.add_field(name="📚 Matéria", value="*Não preenchido*", inline=True)
    embed.add_field(name="⭐ Nível", value="*Não preenchido*", inline=True)
    embed.add_field(name="🏷️ Etiqueta", value="*Não preenchido*", inline=True)
    
    embed.set_footer(text="Clique nos botões abaixo para preencher cada campo")
    
    # Cria a view com os botões
    view = BotoesQuestaoView(user_id)
    
    await interaction.response.send_message(embed=embed, view=view)
    print(f"✅ {interaction.user} iniciou criação de questão")



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