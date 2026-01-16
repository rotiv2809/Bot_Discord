import discord
<<<<<<< Updated upstream
from discord import ui
from scripts.modals import DescricaoModal, atualizar_embed_questao
from scripts.nivel_etiqueta import NivelView, EtiquetaModal
=======
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime
import io
>>>>>>> Stashed changes

# Mapeamento de matérias para IDs de canais
MATERIAS_CANAIS = {
    "Matemática": 1437144074779099328,
    "Física": 1437144607426084894,
    "Química": 1431724171607412920,
    "Humanas": 1437144849110532219,
    "Linguagens": 1450565544620200067,
    "Outros": 1450565643983126558
}

class MateriaSelect(ui.Select):
    """Dropdown para seleção de matéria"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
        
        options = [
            discord.SelectOption(label="Matemática", emoji="🔢", description="Questões de matemática"),
            discord.SelectOption(label="Física", emoji="⚛️", description="Questões de física"),
            discord.SelectOption(label="Química", emoji="🧪", description="Questões de química"),
            discord.SelectOption(label="Humanas", emoji="📖", description="História, Geografia, Filosofia, etc."),
            discord.SelectOption(label="Linguagens", emoji="📝", description="Português, Literatura, Inglês, etc."),
            discord.SelectOption(label="Outros", emoji="📚", description="Outras matérias"),
        ]
        
        super().__init__(
            placeholder="Selecione a matéria...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_materia"
        )
    
    async def callback(self, interaction: discord.Interaction):
        materia_selecionada = self.values[0]
        
        # Salva a matéria e o ID do canal
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['materia'] = materia_selecionada
        self.questoes_em_criacao[self.user_id]['canal_id'] = MATERIAS_CANAIS[materia_selecionada]
        
        await interaction.response.send_message(
            f"✅ Matéria selecionada: **{materia_selecionada}**",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id, self.questoes_em_criacao)


<<<<<<< Updated upstream
class MateriaView(ui.View):
    """View temporária para o dropdown de matérias"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__(timeout=60)
        self.add_item(MateriaSelect(user_id, questoes_em_criacao))


class BotoesQuestaoView(ui.View):
    """View com os botões para preencher os campos da questão"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
    
    @ui.button(label="📝 Descrição", style=discord.ButtonStyle.primary, custom_id="btn_descricao")
    async def button_descricao(self, interaction: discord.Interaction, button: ui.Button):
        # Abre o modal de descrição
        modal = DescricaoModal(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🖼️ Imagem", style=discord.ButtonStyle.secondary, custom_id="btn_imagem")
    async def button_imagem(self, interaction: discord.Interaction, button: ui.Button):
        # Ativa o modo de espera de imagem
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['aguardando_imagem'] = True
        self.questoes_em_criacao[self.user_id]['canal_imagem'] = interaction.channel_id
        
        await interaction.response.send_message(
            "📷 **Modo de captura de imagem ativado!**\n\n"
            "Por favor, envie uma imagem neste canal das seguintes formas:\n"
            "• Anexe uma imagem (arraste e solte ou clique no +)\n"
            "• Cole uma imagem diretamente no chat\n"
            "• Envie um link de imagem\n\n"
            "⏱️ Você tem 2 minutos para enviar a imagem.\n"
            "💡 Para pular, clique novamente no botão 🖼️ Imagem.",
            ephemeral=True
        )
    
    @ui.button(label="📚 Matéria", style=discord.ButtonStyle.secondary, custom_id="btn_materia")
    async def button_materia(self, interaction: discord.Interaction, button: ui.Button):
        view = MateriaView(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_message(
            "📚 **Selecione a matéria da questão:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="⭐ Nível", style=discord.ButtonStyle.secondary, custom_id="btn_nivel")
    async def button_nivel(self, interaction: discord.Interaction, button: ui.Button):
        view = NivelView(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_message(
            "⭐ **Selecione o nível de dificuldade da questão:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="🏷️ Etiqueta", style=discord.ButtonStyle.secondary, custom_id="btn_etiqueta")
    async def button_etiqueta(self, interaction: discord.Interaction, button: ui.Button):
        modal = EtiquetaModal(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✅ Finalizar", style=discord.ButtonStyle.success, custom_id="btn_finalizar", row=2)
    async def button_finalizar(self, interaction: discord.Interaction, button: ui.Button):
        dados = self.questoes_em_criacao.get(self.user_id, {})
        
        # Validação
        campos_obrigatorios = {
            'descricao': '📝 Descrição',
            'materia': '📚 Matéria'
        }
        
        faltando = [nome for campo, nome in campos_obrigatorios.items() if not dados.get(campo)]
        
        if faltando:
            await interaction.response.send_message(
                f"❌ **Campos obrigatórios faltando:**\n" + "\n".join(f"• {campo}" for campo in faltando),
                ephemeral=True
            )
            return
        
        # Defer para ter mais tempo
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Busca o canal da matéria
            canal_id = dados.get('canal_id')
            canal = interaction.guild.get_channel(canal_id)
            
            if not canal:
                await interaction.followup.send(
                    "❌ Erro: Canal da matéria não encontrado!",
                    ephemeral=True
                )
                return
            
            # Cria o embed da questão
            embed_questao = discord.Embed(
                title="❓ Nova Questão",
                description=dados['descricao'],
                color=discord.Color.blue()
            )
            
            embed_questao.add_field(
                name="📚 Matéria",
                value=dados['materia'],
                inline=True
            )
            
            if dados.get('nivel'):
                embed_questao.add_field(
                    name="⭐ Nível",
                    value=dados['nivel'],
                    inline=True
                )
            
            if dados.get('etiqueta'):
                embed_questao.add_field(
                    name="🏷️ Etiquetas",
                    value=dados['etiqueta'],
                    inline=True
                )
            
            embed_questao.set_footer(
                text=f"Criado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            if dados.get('imagem'):
                embed_questao.set_image(url=dados['imagem'])
            
            # Cria o tópico no canal
            nome_topico = f"Questão - {dados['materia']}"
            if len(dados['descricao']) > 50:
                nome_topico = f"{dados['descricao'][:47]}..."
            else:
                nome_topico = dados['descricao']
            
            # Cria thread/tópico
            mensagem_inicial = await canal.send(embed=embed_questao)
            topico = await mensagem_inicial.create_thread(
                name=nome_topico[:100],  # Limite de 100 caracteres
                auto_archive_duration=1440  # 24 horas
            )
            
            await interaction.followup.send(
                f"✅ **Questão criada com sucesso!**\n\n"
                f"📍 Canal: {canal.mention}\n"
                f"🧵 Tópico: {topico.mention}\n"
                f"📚 Matéria: **{dados['materia']}**",
=======
class GerenciarQuestaoSelect(ui.Select):
    """Select menu para gerenciar questões"""
    def __init__(self, token):
        self.token = token
        
        options = [
            discord.SelectOption(
                label="Marcar como Resolvida",
                description="Move para resolvidas com histórico em TXT",
                emoji="✅",
                value="resolver"
            ),
            discord.SelectOption(
                label="Deletar Questão",
                description="Remove a questão permanentemente",
                emoji="🗑️",
                value="deletar"
            )
        ]
        
        super().__init__(
            placeholder="Gerenciar Questão",
            options=options,
            custom_id=f"gerenciar_questao_select_{token}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Busca o thread
            thread = None
            mensagem_original = None
            
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                async for msg in thread.parent.history(limit=100):
                    if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                        mensagem_original = msg
                        break
            elif hasattr(interaction.message, 'thread') and interaction.message.thread:
                thread = interaction.message.thread
                mensagem_original = interaction.message
            
            if not thread:
                await interaction.followup.send("❌ Thread não encontrado!", ephemeral=True)
                return
            
            if not mensagem_original:
                mensagem_original = interaction.message
            
            # Executa a ação selecionada
            if self.values[0] == "resolver":
                await self.marcar_resolvida(interaction, thread, mensagem_original)
            elif self.values[0] == "deletar":
                await self.deletar_questao(interaction, thread, mensagem_original)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro no select: {e}")
            import traceback
            traceback.print_exc()
    
    async def marcar_resolvida(self, interaction, thread, mensagem_original):
        """Marca questão como resolvida e move para canal resolvidas"""
        try:
            # Busca o canal de resolvidas
            canal_resolvidas = interaction.guild.get_channel(CANAL_RESOLVIDAS_ID)
            
            if not canal_resolvidas:
                await interaction.followup.send("❌ Canal de resolvidas não configurado!", ephemeral=True)
                return
            
            # Busca canal de favoritos
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            
            # USA O TOKEN DA QUESTÃO
            token = self.token
            
            # PEGA TODOS OS USUÁRIOS QUE REAGIRAM COM ⭐ (ANTES DE DELETAR!)
            usuarios_favoritaram = set()
            try:
                for reaction in mensagem_original.reactions:
                    if str(reaction.emoji) == "⭐":
                        async for user in reaction.users():
                            if not user.bot:  # Ignora bots
                                usuarios_favoritaram.add(user)
                        break
            except Exception as e:
                print(f"Erro ao pegar reações: {e}")
            
            print(f"📊 {len(usuarios_favoritaram)} usuários favoritaram a questão {token}")
            
            # 1. COLETA TODAS AS MENSAGENS DO THREAD
            mensagens_texto = []
            mensagens_texto.append("=" * 80)
            mensagens_texto.append(f"QUESTÃO RESOLVIDA - {thread.name}")
            mensagens_texto.append(f"TOKEN: {token}")
            mensagens_texto.append("=" * 80)
            mensagens_texto.append(f"Data de Resolução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            mensagens_texto.append(f"Resolvida por: {interaction.user.name} ({interaction.user.id})")
            mensagens_texto.append("=" * 80)
            mensagens_texto.append("")
            
            # Adiciona informações do embed original
            if mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                mensagens_texto.append("INFORMAÇÕES DA QUESTÃO:")
                mensagens_texto.append("-" * 80)
                if embed_original.title:
                    mensagens_texto.append(f"Título: {embed_original.title}")
                if embed_original.description:
                    # Remove o token da descrição
                    desc = embed_original.description
                    if "Token:" in desc:
                        desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                    mensagens_texto.append(f"Descrição: {desc}")
                if embed_original.author:
                    mensagens_texto.append(f"Autor: {embed_original.author.name}")
                mensagens_texto.append("-" * 80)
                mensagens_texto.append("")
            
            mensagens_texto.append("HISTÓRICO DE MENSAGENS:")
            mensagens_texto.append("=" * 80)
            mensagens_texto.append("")
            
            # Coleta mensagens do thread (IGNORA MENSAGENS VAZIAS/DO BOT)
            contador = 0
            mensagens_usuario = []
            
            async for message in thread.history(oldest_first=True, limit=None):
                # Ignora mensagens do bot que são só views/botões
                if message.author.bot and not message.content and not message.embeds:
                    continue
                
                # Ignora mensagens vazias
                if not message.content and not message.attachments and not message.embeds:
                    continue
                
                mensagens_usuario.append(message)
            
            # Processa as mensagens válidas
            for message in mensagens_usuario:
                contador += 1
                timestamp = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
                autor = f"{message.author.name}"
                
                mensagens_texto.append(f"[{timestamp}] {autor}:")
                
                if message.content:
                    mensagens_texto.append(f"  {message.content}")
                
                # Adiciona info sobre anexos
                if message.attachments:
                    for attachment in message.attachments:
                        mensagens_texto.append(f"  📎 Anexo: {attachment.filename} ({attachment.url})")
                
                mensagens_texto.append("")
            
            mensagens_texto.append("=" * 80)
            mensagens_texto.append(f"Total de mensagens: {contador}")
            mensagens_texto.append(f"Usuários que favoritaram: {len(usuarios_favoritaram)}")
            mensagens_texto.append("=" * 80)
            
            # Cria o arquivo TXT
            arquivo_texto = "\n".join(mensagens_texto)
            arquivo_bytes = io.BytesIO(arquivo_texto.encode('utf-8'))
            arquivo_nome = f"{token}.txt"
            arquivo = discord.File(arquivo_bytes, filename=arquivo_nome)
            
            # 2. CRIA EMBED PARA O CANAL RESOLVIDAS
            if mensagem_original.embeds:
                embed = mensagem_original.embeds[0].copy()
            else:
                embed = discord.Embed(
                    title="Questão Resolvida",
                    description="Conteúdo não disponível",
                    color=discord.Color.green()
                )
            
            embed.color = discord.Color.green()
            embed.title = embed.title.replace("📚", "✅") if "📚" in embed.title else f"✅ {embed.title}"
            
            # Remove campos antigos
            fields_para_remover = []
            for i, field in enumerate(embed.fields):
                if field.name in ["📊 Status", "ID do usuário"]:
                    fields_para_remover.append(i)
            
            for i in sorted(fields_para_remover, reverse=True):
                embed.remove_field(i)
            
            # Adiciona novos campos
            embed.add_field(name="📊 Status", value="✅ Resolvida", inline=True)
            embed.add_field(
                name="👤 Resolvida por",
                value=f"{interaction.user.mention}",
                inline=True
            )
            embed.add_field(
                name="📅 Data",
                value=datetime.now().strftime("%d/%m/%Y %H:%M"),
                inline=True
            )
            embed.add_field(
                name="💬 Mensagens",
                value=f"{contador} mensagens",
                inline=True
            )
            embed.add_field(
                name="⭐ Favoritos",
                value=f"{len(usuarios_favoritaram)} usuários",
                inline=True
            )
            
            embed.set_footer(text=f"Token: {token}")
            
            # 3. POSTA NO CANAL RESOLVIDAS
            view_resolvidas = FavoritoButtonResolvidas(token)
            mensagem_resolvida = await canal_resolvidas.send(
                embed=embed,
                file=arquivo,
                view=view_resolvidas
            )
            
            # 4. ENVIA PARA OS FAVORITOS DE TODOS QUE REAGIRAM COM ⭐
            if canal_favoritos and usuarios_favoritaram:
                print(f"📤 Enviando para {len(usuarios_favoritaram)} usuários...")
                
                # Identifica a matéria
                materia = None
                for nome, canal_id in MATERIAS_CANAIS.items():
                    if thread.parent.id == canal_id:
                        materia = nome
                        break
                
                if not materia:
                    materia = "Geral"
                
                for user in usuarios_favoritaram:
                    try:
                        # Nome do thread privado do usuário
                        thread_name = f"{materia} - {user.name}"
                        
                        # Procura thread existente
                        thread_existente = None
                        for t in canal_favoritos.threads:
                            if t.name == thread_name and not t.archived:
                                thread_existente = t
                                break
                        
                        if not thread_existente:
                            async for t in canal_favoritos.archived_threads(limit=100):
                                if t.name == thread_name:
                                    thread_existente = t
                                    if t.archived:
                                        await t.edit(archived=False)
                                    break
                        
                        # Cria thread se não existir
                        if not thread_existente:
                            thread_fav = await canal_favoritos.create_thread(
                                name=thread_name,
                                type=discord.ChannelType.private_thread,
                                auto_archive_duration=10080,
                                invitable=False
                            )
                            await thread_fav.add_user(user)
                            
                            welcome_embed = discord.Embed(
                                title="⭐ Seus Favoritos",
                                description=f"Espaço privado para questões de **{materia}**!",
                                color=discord.Color.gold()
                            )
                            await thread_fav.send(embed=welcome_embed)
                        else:
                            thread_fav = thread_existente
                        
                        # Cria embed para favoritos
                        embed_favorito = discord.Embed(
                            title=f"✅ {token} • Resolvida",
                            description=embed.description if embed.description else "Questão resolvida!",
                            color=discord.Color.green(),
                            timestamp=datetime.now()
                        )
                        
                        if embed.image:
                            embed_favorito.set_image(url=embed.image.url)
                        
                        if embed.author:
                            embed_favorito.set_author(
                                name=embed.author.name,
                                icon_url=embed.author.icon_url
                            )
                        
                        embed_favorito.add_field(
                            name="🏷️ Token",
                            value=f"`{token}`",
                            inline=True
                        )
                        
                        embed_favorito.add_field(
                            name="👤 Resolvida por",
                            value=interaction.user.mention,
                            inline=True
                        )
                        
                        embed_favorito.add_field(
                            name="🔗 Ver no Canal",
                            value=f"[Ir para resolvidas]({mensagem_resolvida.jump_url})",
                            inline=False
                        )
                        
                        embed_favorito.set_footer(text=f"Token: {token} • Você favoritou esta questão")
                        
                        await thread_fav.send(embed=embed_favorito)
                        print(f"  ✅ Enviado para {user.name}")
                        
                    except Exception as e:
                        print(f"  ❌ Erro ao enviar para {user.name}: {e}")
                
                print(f"✅ Concluído! Enviado para favoritos de {len(usuarios_favoritaram)} usuários")
            
            # 5. DELETA A QUESTÃO ORIGINAL
            try:
                await mensagem_original.delete()
                await thread.delete()
                print(f"🗑️ Questão {token} deletada")
            except Exception as e:
                print(f"Erro ao deletar: {e}")
            
            # 6. CONFIRMA PARA O USUÁRIO
            await interaction.followup.send(
                f"✅ **Questão `{token}` marcada como resolvida!**\n\n"
                f"📦 Movida para {canal_resolvidas.mention}\n"
                f"📄 Histórico: {contador} mensagens\n"
                f"⭐ Notificados: {len(usuarios_favoritaram)} usuários\n"
                f"🔗 [**Ver questão resolvida**]({mensagem_resolvida.jump_url})",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao marcar resolvida: {e}")
            import traceback
            traceback.print_exc()
    
    async def deletar_questao(self, interaction, thread, mensagem_original):
        """Deleta a questão completamente"""
        await interaction.followup.send(
            "⚠️ **Deletar esta questão?**\n\n"
            "Ação permanente! Deletando em 5 segundos...",
            ephemeral=True
        )
        
        import asyncio
        await asyncio.sleep(5)
        
        try:
            await mensagem_original.delete()
            await thread.delete()
        except Exception as e:
            print(f"Erro ao deletar: {e}")


class StatusQuestaoView(ui.View):
    """View com select menu E botão de favoritar"""
    def __init__(self, token):
        super().__init__(timeout=None)
        self.token = token
        self.add_item(GerenciarQuestaoSelect(token))
    
    @ui.button(label="⭐ Favoritar", style=discord.ButtonStyle.primary, custom_id="favoritar_questao_aberta", row=1)
    async def favoritar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            token = self.token
            
            # Busca a mensagem original para adicionar reação
            mensagem_original = None
            thread = None
            
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                async for msg in thread.parent.history(limit=100):
                    if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                        mensagem_original = msg
                        break
            elif hasattr(interaction.message, 'thread') and interaction.message.thread:
                mensagem_original = interaction.message
                thread = interaction.message.thread
            
            # ADICIONA REAÇÃO ⭐ NA MENSAGEM ORIGINAL
            if mensagem_original:
                try:
                    await mensagem_original.add_reaction("⭐")
                    print(f"⭐ Reação adicionada por {interaction.user.name} na questão {token}")
                except Exception as e:
                    print(f"Erro ao adicionar reação: {e}")
            
            # Identifica a matéria
            materia = None
            canal_questao = interaction.channel
            
            if isinstance(canal_questao, discord.Thread):
                canal_questao = canal_questao.parent
            
            for nome, canal_id in MATERIAS_CANAIS.items():
                if canal_questao.id == canal_id:
                    materia = nome
                    break
            
            if not materia:
                await interaction.followup.send("❌ Matéria não identificada!", ephemeral=True)
                return
            
            # Busca canal de favoritos
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            if not canal_favoritos:
                await interaction.followup.send("❌ Canal de favoritos não encontrado!", ephemeral=True)
                return
            
            # Canal resolvidas para o link
            canal_resolvidas = interaction.guild.get_channel(CANAL_RESOLVIDAS_ID)
            
            # Thread privado
            thread_name = f"{materia} - {interaction.user.name}"
            
            thread_existente = None
            for t in canal_favoritos.threads:
                if t.name == thread_name and not t.archived:
                    thread_existente = t
                    break
            
            if not thread_existente:
                async for t in canal_favoritos.archived_threads(limit=100):
                    if t.name == thread_name:
                        thread_existente = t
                        if t.archived:
                            await t.edit(archived=False)
                        break
            
            if not thread_existente:
                thread_fav = await canal_favoritos.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    auto_archive_duration=10080,
                    invitable=False
                )
                await thread_fav.add_user(interaction.user)
                
                welcome_embed = discord.Embed(
                    title="⭐ Seus Favoritos",
                    description=f"Espaço privado para questões de **{materia}**!",
                    color=discord.Color.gold()
                )
                await thread_fav.send(embed=welcome_embed)
            else:
                thread_fav = thread_existente
            
            # COLETA SNAPSHOT
            mensagens_historico = []
            contador_msgs = 0
            
            if thread:
                async for message in thread.history(oldest_first=True, limit=30):
                    if message.author.bot and not message.content:
                        continue
                    if not message.content and not message.attachments:
                        continue
                    
                    contador_msgs += 1
                    timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")
                    mensagens_historico.append(f"**[{timestamp}] {message.author.name}:**")
                    if message.content:
                        conteudo = message.content[:150] + "..." if len(message.content) > 150 else message.content
                        mensagens_historico.append(f"{conteudo}\n")
            
            historico_texto = "\n".join(mensagens_historico[:8]) if mensagens_historico else "Sem mensagens"
            if len(mensagens_historico) > 8:
                historico_texto += f"\n*... +{len(mensagens_historico) - 8} mensagens*"
            
            # Embed
            mensagem_para_embed = mensagem_original if mensagem_original else interaction.message
            embed = discord.Embed(
                title=f"📌 {token} • Em Aberto",
                description="⚠️ **Questão em aberto.** Snapshot do momento.\n\n"
                           "Você receberá uma notificação aqui quando esta questão for resolvida!",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            if mensagem_para_embed.embeds:
                embed_original = mensagem_para_embed.embeds[0]
                
                if embed_original.description:
                    desc = embed_original.description
                    if "Token:" in desc:
                        desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                    embed.add_field(
                        name="📝 Questão",
                        value=desc[:800],
                        inline=False
                    )
                
                if embed_original.image:
                    embed.set_image(url=embed_original.image.url)
                
                if embed_original.author:
                    embed.set_author(
                        name=embed_original.author.name,
                        icon_url=embed_original.author.icon_url
                    )
            
            if historico_texto and contador_msgs > 0:
                embed.add_field(
                    name=f"💬 Discussão ({contador_msgs} msgs)",
                    value=historico_texto[:900],
                    inline=False
                )
            
            # LINK COM BUSCA NO CANAL RESOLVIDAS
            if canal_resolvidas:
                embed.add_field(
                    name="🔍 Buscar quando resolvida",
                    value=f"Token: `{token}`\n[Ir para {canal_resolvidas.mention}]({canal_resolvidas.jump_url})\n"
                          f"Use Ctrl+F e busque por `{token}`",
                    inline=False
                )
            
            embed.add_field(
                name="🔗 Link Atual",
                value=f"[Questão em aberto]({thread.jump_url if thread else mensagem_para_embed.jump_url})\n"
                      f"⚠️ Inválido quando resolvida",
                inline=False
            )
            
            embed.set_footer(text=f"Token: {token} • Snapshot • Você será notificado quando resolvida")
            
            await thread_fav.send(embed=embed)
            
            await interaction.followup.send(
                f"✅ **`{token}` favoritada em {thread_fav.mention}!**\n\n"
                f"📸 Snapshot salvo\n"
                f"⭐ Reação adicionada\n"
                f"🔔 Você receberá notificação quando resolvida\n"
                f"🔍 Use o token para buscar nas resolvidas",
>>>>>>> Stashed changes
                ephemeral=True
            )
            
            # Remove a mensagem original
            try:
                await interaction.message.delete()
            except:
                pass
            
            # Limpa os dados
            self.questoes_em_criacao.pop(self.user_id, None)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao favoritar: {e}")
            import traceback
            traceback.print_exc()


class FavoritoButtonResolvidas(ui.View):
    """Botão favoritar para resolvidas"""
    def __init__(self, token):
        super().__init__(timeout=None)
        self.token = token
    
    @ui.button(label="⭐ Favoritar", style=discord.ButtonStyle.primary, custom_id="favoritar_resolvida", row=0)
    async def favoritar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            token = self.token
            
            # Identifica matéria
            materia = None
            if interaction.message.embeds:
                titulo = interaction.message.embeds[0].title
                for nome in MATERIAS_CANAIS.keys():
                    if nome in titulo:
                        materia = nome
                        break
            
            if not materia:
                await interaction.followup.send("❌ Matéria não identificada!", ephemeral=True)
                return
            
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            if not canal_favoritos:
                await interaction.followup.send("❌ Canal de favoritos não encontrado!", ephemeral=True)
                return
            
            thread_name = f"{materia} - {interaction.user.name}"
            
            thread_existente = None
            for thread in canal_favoritos.threads:
                if thread.name == thread_name and not thread.archived:
                    thread_existente = thread
                    break
            
            if not thread_existente:
                async for thread in canal_favoritos.archived_threads(limit=100):
                    if thread.name == thread_name:
                        thread_existente = thread
                        if thread.archived:
                            await thread.edit(archived=False)
                        break
            
            if not thread_existente:
                thread = await canal_favoritos.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    auto_archive_duration=10080,
                    invitable=False
                )
                await thread.add_user(interaction.user)
                
                welcome_embed = discord.Embed(
                    title="⭐ Seus Favoritos",
                    description=f"Espaço privado para **{materia}**!",
                    color=discord.Color.gold()
                )
                await thread.send(embed=welcome_embed)
            else:
                thread = thread_existente
            
            # Embed
            mensagem_original = interaction.message
            embed = discord.Embed(
                title=f"✅ {token} • Resolvida",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            if mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                desc = embed_original.description
                if desc and "Token:" in desc:
                    desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                
                embed.description = desc
                
                if embed_original.image:
                    embed.set_image(url=embed_original.image.url)
                if embed_original.author:
                    embed.set_author(
                        name=embed_original.author.name,
                        icon_url=embed_original.author.icon_url
                    )
            
            embed.add_field(
                name="🏷️ Token",
                value=f"`{token}`",
                inline=True
            )
            
            embed.add_field(
                name="🔗 Ver Original",
                value=f"[Clique aqui]({mensagem_original.jump_url})",
                inline=True
            )
            
            if mensagem_original.attachments:
                arquivo_url = mensagem_original.attachments[0].url
                embed.add_field(
                    name="📄 Histórico TXT",
                    value=f"[Download]({arquivo_url})",
                    inline=False
                )
            
            embed.set_footer(text=f"Token: {token}")
            
            await thread.send(embed=embed)
            
            await interaction.followup.send(
<<<<<<< Updated upstream
                f"❌ Erro ao criar questão: {str(e)}",
                ephemeral=True
            )
            print(f"Erro ao criar questão: {e}")
    
    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="btn_cancelar", row=2)
    async def button_cancelar(self, interaction: discord.Interaction, button: ui.Button):
        self.questoes_em_criacao.pop(self.user_id, None)
        await interaction.message.delete()
        await interaction.response.send_message(
            "🗑️ Criação de questão cancelada.",
            ephemeral=True
        )
=======
                f"✅ `{token}` favoritada em {thread.mention}!",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro: {e}")


# Compatibilidade
StatusQuestaoButton = StatusQuestaoView
FavoritoButton = StatusQuestaoView
>>>>>>> Stashed changes
