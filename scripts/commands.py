import discord
import asyncio
from scripts.views import BotoesQuestaoView

def setup_commands(context):
    """Registra todos os comandos slash do bot"""
    bot = context['bot']
    supabase = context['supabase']
    tickets_verificacao_ativa = context['tickets_verificacao_ativa']
    questoes_em_criacao = context['questoes_em_criacao']
    CATEGORIA_VERIFICACAO_ID = context['CATEGORIA_VERIFICACAO_ID']
    ROLE_ID_ALUNO = context['ROLE_ID_ALUNO']
    
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
        view = BotoesQuestaoView(user_id, questoes_em_criacao)
        
        await interaction.response.send_message(embed=embed, view=view)
        print(f"✅ {interaction.user} iniciou criação de questão")