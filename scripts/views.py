import discord
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime

MATERIAS_CANAIS = {
    "Matemática": 1437144074779099328,
    "Física": 1437144607426084894,
    "Química": 1431724171607412920,
    "Humanas": 1437144849110532219,
    "Linguagens": 1450565544620200067,
    "Outros": 1450565643983126558
}

CANAL_FAVORITOS_ID = 1451670988243861676
CANAL_RESOLVIDAS_ID = 1450565720500080741  # <<< COLOQUE O ID DO CANAL RESOLVIDAS AQUI



class StatusQuestaoButton(ui.View):
    """View com botões de status e favoritar"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="✅ Finalizar", style=discord.ButtonStyle.success, custom_id="finalizar_questao", row=0)
    async def finalizar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Busca o thread de múltiplas formas
            thread = None
            mensagem_original = None
            
            # Caso 1: Está dentro do thread
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                # Busca a mensagem que criou o thread no canal pai
                async for msg in thread.parent.history(limit=100):
                    if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                        mensagem_original = msg
                        break
            
            # Caso 2: Está no canal, mensagem tem thread anexado
            elif hasattr(interaction.message, 'thread') and interaction.message.thread:
                thread = interaction.message.thread
                mensagem_original = interaction.message
            
            # Caso 3: Busca pelo ID da mensagem
            else:
                # Tenta encontrar o thread na lista de threads ativos
                for t in interaction.channel.threads:
                    async for msg in interaction.channel.history(limit=100):
                        if hasattr(msg, 'thread') and msg.thread and msg.thread.id == t.id and msg.id == interaction.message.id:
                            thread = t
                            mensagem_original = msg
                            break
                    if thread:
                        break
            
            if not thread:
                await interaction.followup.send("❌ Thread não encontrado! Certifique-se de que a questão tem um tópico criado.", ephemeral=True)
                return
            
            if not mensagem_original:
                mensagem_original = interaction.message
            
            # Salva o canal original
            canal_original_id = thread.parent.id
            
            # Bloqueia o thread
            await thread.edit(
                locked=True,
                archived=False,
                name=f"✅ {thread.name}" if not thread.name.startswith("✅") else thread.name
            )
            
            # Atualiza o embed
            if mensagem_original.embeds:
                embed = mensagem_original.embeds[0].copy()
                embed.color = discord.Color.green()
                embed.title = embed.title.replace("📚", "✅") if "📚" in embed.title else f"✅ {embed.title}"
                
                # Atualiza ou adiciona campo de status
                status_encontrado = False
                for i, field in enumerate(embed.fields):
                    if field.name == "📊 Status":
                        embed.set_field_at(i, name="📊 Status", value="✅ Finalizada", inline=True)
                        status_encontrado = True
                        break
                
                if not status_encontrado:
                    embed.add_field(name="📊 Status", value="✅ Finalizada", inline=True)
                
                await mensagem_original.edit(embed=embed)
            
            # Envia mensagem de confirmação no thread
            embed_confirmacao = discord.Embed(
                title="✅ Questão Finalizada",
                description="Esta questão foi marcada como finalizada. O tópico foi bloqueado para novas mensagens.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed_confirmacao.set_footer(text=f"Finalizado por {interaction.user.name}")
            
            await thread.send(embed=embed_confirmacao)
            await interaction.followup.send("✅ Questão marcada como finalizada!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao finalizar questão: {str(e)}", ephemeral=True)
            print(f"Erro detalhado ao finalizar: {e}")
            import traceback
            traceback.print_exc()
    
    @ui.button(label="🔄 Reabrir", style=discord.ButtonStyle.secondary, custom_id="reabrir_questao", row=0)
    async def reabrir(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Busca o thread de múltiplas formas
            thread = None
            mensagem_original = None
            
            # Caso 1: Está dentro do thread
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                # Busca a mensagem que criou o thread no canal pai
                async for msg in thread.parent.history(limit=100):
                    if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                        mensagem_original = msg
                        break
            
            # Caso 2: Está no canal, mensagem tem thread anexado
            elif hasattr(interaction.message, 'thread') and interaction.message.thread:
                thread = interaction.message.thread
                mensagem_original = interaction.message
            
            # Caso 3: Busca pelo ID da mensagem
            else:
                for t in interaction.channel.threads:
                    async for msg in interaction.channel.history(limit=100):
                        if hasattr(msg, 'thread') and msg.thread and msg.thread.id == t.id and msg.id == interaction.message.id:
                            thread = t
                            mensagem_original = msg
                            break
                    if thread:
                        break
            
            if not thread:
                await interaction.followup.send("❌ Thread não encontrado! Certifique-se de que a questão tem um tópico criado.", ephemeral=True)
                return
            
            if not mensagem_original:
                mensagem_original = interaction.message
            
            # Desbloqueia o thread
            await thread.edit(
                locked=False,
                archived=False,
                name=thread.name.replace("✅ ", "") if thread.name.startswith("✅") else thread.name
            )
            
            # Atualiza o embed
            if mensagem_original.embeds:
                embed = mensagem_original.embeds[0].copy()
                embed.color = discord.Color.blue()
                embed.title = embed.title.replace("✅", "📚") if "✅" in embed.title else embed.title
                
                # Atualiza ou adiciona campo de status
                status_encontrado = False
                for i, field in enumerate(embed.fields):
                    if field.name == "📊 Status":
                        embed.set_field_at(i, name="📊 Status", value="🔄 Em Aberto", inline=True)
                        status_encontrado = True
                        break
                
                if not status_encontrado:
                    embed.add_field(name="📊 Status", value="🔄 Em Aberto", inline=True)
                
                await mensagem_original.edit(embed=embed)
            
            # Envia mensagem de confirmação no thread
            embed_confirmacao = discord.Embed(
                title="🔄 Questão Reaberta",
                description="Esta questão foi reaberta. O tópico está novamente disponível para discussão.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed_confirmacao.set_footer(text=f"Reaberto por {interaction.user.name}")
            
            await thread.send(embed=embed_confirmacao)
            await interaction.followup.send("🔄 Questão reaberta com sucesso!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao reabrir questão: {str(e)}", ephemeral=True)
            print(f"Erro detalhado ao reabrir: {e}")
            import traceback
            traceback.print_exc()
    
    @ui.button(label="⭐ Favoritar", style=discord.ButtonStyle.primary, custom_id="favoritar_questao", row=0)
    async def favoritar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Identifica a matéria pelo canal ou pelo thread parent
            materia = None
            canal_questao = interaction.channel
            
            # Se estiver em um thread, pega o canal pai
            if isinstance(canal_questao, discord.Thread):
                canal_questao = canal_questao.parent
            
            # Busca a matéria
            for nome, canal_id in MATERIAS_CANAIS.items():
                if canal_questao.id == canal_id:
                    materia = nome
                    break
            
            if not materia:
                await interaction.followup.send("❌ Não foi possível identificar a matéria!", ephemeral=True)
                return
            
            # Busca o canal de favoritos
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            if not canal_favoritos:
                await interaction.followup.send("❌ Canal de favoritos não encontrado!", ephemeral=True)
                return
            
            # Nome do thread privado
            thread_name = f"{materia} - {interaction.user.name}"
            
            # Procura se já existe um thread com esse nome (ativo)
            thread_existente = None
            
            # Busca em threads ativos
            for thread in canal_favoritos.threads:
                if thread.name == thread_name and not thread.archived:
                    thread_existente = thread
                    break
            
            # Se não encontrou nos ativos, busca nos arquivados
            if not thread_existente:
                async for thread in canal_favoritos.archived_threads(limit=100):
                    if thread.name == thread_name:
                        thread_existente = thread
                        # Desarquiva se necessário
                        if thread.archived:
                            await thread.edit(archived=False)
                        break
            
            # Se não existir, cria um novo thread privado
            if not thread_existente:
                # CRIA UM THREAD PRIVADO DIRETAMENTE NO CANAL
                thread = await canal_favoritos.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    auto_archive_duration=10080,  # 7 dias
                    invitable=False
                )
                
                # Adiciona o usuário ao thread
                await thread.add_user(interaction.user)
                
                # Envia mensagem de boas-vindas
                welcome_embed = discord.Embed(
                    title="⭐ Seus Favoritos",
                    description=f"Este é seu espaço privado para questões favoritadas de **{materia}**!",
                    color=discord.Color.gold()
                )
                await thread.send(embed=welcome_embed)
            else:
                thread = thread_existente
            
            # Pega a mensagem original (o embed da questão)
            mensagem_original = interaction.message
            
            # Cria um embed com a questão favoritada
            embed = discord.Embed(
                title="📌 Questão Favoritada",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            # Copia informações do embed original se existir
            if mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                
                # Copia a descrição
                if embed_original.description:
                    embed.description = embed_original.description
                
                # Copia a imagem se houver
                if embed_original.image:
                    embed.set_image(url=embed_original.image.url)
                
                # Copia o autor se houver
                if embed_original.author:
                    embed.set_author(
                        name=embed_original.author.name,
                        icon_url=embed_original.author.icon_url
                    )
            
            # Adiciona informações extras
            embed.add_field(
                name="📍 Local",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            embed.add_field(
                name="📅 Data",
                value=mensagem_original.created_at.strftime("%d/%m/%Y %H:%M"),
                inline=True
            )
            
            embed.add_field(
                name="🔗 Link Original",
                value=f"[Clique aqui]({mensagem_original.jump_url})",
                inline=False
            )
            
            embed.set_footer(text=f"Favoritado por {interaction.user.name}")
            
            # Envia para o thread privado
            await thread.send(embed=embed)
            
            # Confirma ao usuário
            await interaction.followup.send(
                f"✅ Questão favoritada com sucesso em {thread.mention}!",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao favoritar questão: {str(e)}",
                ephemeral=True
            )
            print(f"Erro ao favoritar: {e}")


# Mantém compatibilidade
FavoritoButton = StatusQuestaoButton