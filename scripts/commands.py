import discord
from discord import app_commands
from discord.ext import commands
import discord
from datetime import datetime
import asyncio
from scripts.utils import salvar_questao_local, usuario_ja_perguntou_hoje
from scripts.views import FavoritoButton, StatusQuestaoButton, StatusQuestaoView


MATERIAS_CANAIS = {
    "Matemática": 1437144074779099328,
    "Física": 1437144607426084894,
    "Química": 1431724171607412920,

    "História": 1462861471758422147,
    "Geografia": 1462861526493958285,
    "Português": 1462861348458463253,
    "Inglês": 1462861408214585509,

    "Outros": 1450565643983126558
}

CANAL_FAVORITOS_ID = 1451670988243861676

def setup_commands(context):
    """Registra todos os comandos slash do bot"""
    bot = context['bot']
    supabase = context['supabase']
    tickets_verificacao_ativa = context['tickets_verificacao_ativa']
    questoes_em_criacao = context['questoes_em_criacao']
    CATEGORIA_VERIFICACAO_ID = context['CATEGORIA_VERIFICACAO_ID']
    ROLE_ID_ALUNO = context['ROLE_ID_ALUNO']
    
    @bot.tree.command(name="verificar", description="Iniciar processo de verificação")
    async def verificar(interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        # Verifica se já tem o cargo de aluno
        role_aluno = guild.get_role(ROLE_ID_ALUNO)
        if role_aluno and role_aluno in user.roles:
            await interaction.response.send_message("❌ Você já está verificado como aluno!", ephemeral=True)
            return
        
        # Responde no servidor
        await interaction.response.send_message(
            "✅ Processo de verificação iniciado!\n\n"
            "📬 **Verifique sua DM** - enviei as instruções por lá.",
            ephemeral=True
        )
        
        # Envia DM para o usuário
        try:
            embed = discord.Embed(
                title="🎓 Verificação de Aluno",
                description=(
                    "Bem-vindo ao processo de verificação!\n\n"
                    "Para ter acesso completo ao servidor, você precisa verificar "
                    "que faz parte da tropa."
                ),
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📧 Como funciona?",
                value=(
                    "1️⃣ Digite seu **email** aqui na DM\n"
                    "2️⃣ Verificaremos se você está na base de alunos\n"
                    "3️⃣ Se aprovado, você receberá o cargo automaticamente"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Importante",
                value=(
                    "• Use o email cadastrado\n"
                    "• Responda apenas com o email\n"
                    "• Exemplo: `tropaehbraba@gmail.com`"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Servidor: {guild.name}")
            
            await user.send(embed=embed)
            
            # Marca que o usuário está em processo de verificação
            tickets_verificacao_ativa.add(user.id)
            print(f"✅ Verificação iniciada via DM: {user.name} ({user.id})")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Não consegui enviar DM!**\n\n"
                "Por favor, habilite mensagens diretas de membros do servidor:\n"
                "1. Clique com botão direito no servidor\n"
                "2. **Privacidade** → Ativar **Mensagens diretas**\n"
                "3. Tente o comando `/verificar` novamente",
                ephemeral=True
            )
            return
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
        
    @bot.tree.command(name="criarquestao", description="Cria uma nova questão")
    @app_commands.describe(
        descricao="Descrição da questão",
        materia="Matéria da questão",
        imagem="Envie uma imagem da questão (opcional)"
    )
    @app_commands.choices(materia=[
    app_commands.Choice(name="Matemática", value="Matemática"),
    app_commands.Choice(name="Física", value="Física"),
    app_commands.Choice(name="Química", value="Química"),

    app_commands.Choice(name="História", value="História"),
    app_commands.Choice(name="Geografia", value="Geografia"),
    app_commands.Choice(name="Português", value="Português"),
    app_commands.Choice(name="Inglês", value="Inglês"),

    app_commands.Choice(name="Outros", value="Outros")
    ])

    async def criarquestao(
        interaction: discord.Interaction,
        descricao: str,
        materia: str,
        imagem: discord.Attachment | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        
        # 🔒 Limite de 1 pergunta por dia
        # if usuario_ja_perguntou_hoje(interaction.user.id):
        #     await interaction.followup.send(
        #         "⛔ **Limite diário atingido!**\n\n"
        #         "Você já fez uma pergunta hoje.\n"
        #         "Tente novamente amanhã!",
        #         ephemeral=True
        #     )
        #     return

        try:
            # GERA TOKEN ÚNICO
            import random
            import string
            letras = ''.join(random.choices(string.ascii_uppercase, k=2))
            numeros = ''.join(random.choices(string.digits, k=2))
            token = f"Q-{letras}{numeros}"
            
            # ✅ Não salvamos mais localmente, apenas usamos a URL da imagem
            imagem_url = imagem.url if imagem else None
            
            # Obter o canal correto baseado na matéria
            canal_id = MATERIAS_CANAIS.get(materia)
            if not canal_id:
                await interaction.followup.send(
                    "❌ Matéria não encontrada nos canais configurados.",
                    ephemeral=True
                )
                return
            
            canal = bot.get_channel(canal_id)
            if not canal:
                await interaction.followup.send(
                    "❌ Canal não encontrado. Verifique as permissões do bot.",
                    ephemeral=True
                )
                return
            
            # Criar embed para o tópico COM TOKEN
            embed = discord.Embed(
                title=f"📚 Dúvida de {materia}",
                description=f"**🏷️ Token: `{token}`**\n\n{descricao}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url
            )
            
            if imagem:
                embed.set_image(url=imagem.url)
            
            embed.set_footer(text=f"Token: {token} • ID: {interaction.user.id}")
            
            # Criar a view com select menu e botão de favoritar
            view = StatusQuestaoView(token)
            
            # Criar o tópico no canal COM A VIEW E TOKEN
            mensagem = await canal.send(embed=embed, view=view)
            
            # Criar thread (tópico) a partir da mensagem
            thread = await mensagem.create_thread(
                name=f"{token} • {materia} - {interaction.user.name}",
                auto_archive_duration=1440  # 24 horas
            )

            # Adicionar o usuário ao tópico
            await thread.add_user(interaction.user)

            await mensagem.edit(
                content=f"💬 **Discussão:** {thread.mention}"
            )
            
            # Resposta de sucesso
            resposta = f"✅ **Questão criada com sucesso!**\n\n"
            resposta += f"🏷️ **Token:** `{token}`\n"
            # resposta += f"📁 **Dados salvos em:** `{arquivo_questao}`\n"
            resposta += f"📝 **Matéria:** {materia}\n"
            resposta += f"💬 **Tópico criado:** {thread.mention}\n"
            
            #if imagem:
            #    resposta += f"🖼️ **Imagem salva:** `{imagem_path}`\n"
            
            await interaction.followup.send(resposta, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao criar questão: {str(e)}",
                ephemeral=True
            )
            print(f"Erro em criarquestao: {e}")
    