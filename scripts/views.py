import discord
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime
from scripts.favoritos_store import adicionar_favorito, obter_favoritos, remover_favoritos
import asyncio
import json
import os
import io
import aiohttp
from scripts.drive_uploader import upload_questao_para_drive
import tempfile
import shutil


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
CANAL_RESOLVIDAS_ID = 1450565720500080741


class GerenciarQuestaoSelect(ui.Select):
    def __init__(self, token, criador_id=None):  # ✅ Adicionar criador_id
        self.token = token
        self.criador_id = criador_id  # ✅ Guardar ID do criador
        
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
        
        # ✅ VERIFICAR PERMISSÃO ANTES DE PROCESSAR
        if self.values[0] == "deletar":
            # Verificar se é o criador OU moderador
            is_criador = self.criador_id and interaction.user.id == self.criador_id
            is_moderador = interaction.user.guild_permissions.manage_messages
            
            if not (is_criador or is_moderador):
                await interaction.followup.send(
                    "❌ **Sem permissão!**\n\n"
                    "Apenas o criador da questão ou moderadores podem deletá-la.",
                    ephemeral=True
                )
                return
            
        try:
            thread = None
            mensagem_original = None
            
            # ✅ NOVA LÓGICA: Detectar thread corretamente
            # Caso 1: Interação aconteceu DENTRO da thread
            if isinstance(interaction.channel, discord.Thread):
                thread = interaction.channel
                print(f"🔍 Thread detectada: {thread.name} (ID: {thread.id})")
                
                # Buscar mensagem original que criou a thread
                async for msg in thread.parent.history(limit=100):
                    if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                        mensagem_original = msg
                        print(f"✅ Mensagem original encontrada: {msg.id}")
                        break
            
            # Caso 2: Interação aconteceu na mensagem que TEM thread
            elif hasattr(interaction.message, 'thread') and interaction.message.thread:
                thread = interaction.message.thread
                mensagem_original = interaction.message
                print(f"🔍 Thread da mensagem: {thread.name} (ID: {thread.id})")
            
            # Caso 3: Tentar pegar do canal pai
            else:
                # Tenta buscar thread pelo token
                canal_pai = interaction.channel
                if hasattr(canal_pai, 'parent'):
                    canal_pai = canal_pai.parent
                
                print(f"🔍 Buscando thread no canal: {canal_pai.name if canal_pai else 'None'}")
                
                # Busca threads ativas
                if canal_pai:
                    for t in canal_pai.threads:
                        if self.token in t.name:
                            thread = t
                            print(f"✅ Thread encontrada por token: {thread.name}")
                            
                            # Buscar mensagem original
                            async for msg in canal_pai.history(limit=100):
                                if hasattr(msg, 'thread') and msg.thread and msg.thread.id == thread.id:
                                    mensagem_original = msg
                                    break
                            break
            
            # ❌ Se ainda não encontrou
            if not thread:
                print(f"❌ Thread não encontrada! Canal: {interaction.channel}")
                print(f"❌ Tipo do canal: {type(interaction.channel)}")
                print(f"❌ Token: {self.token}")
                await interaction.followup.send(
                    f"❌ **Thread não encontrada!**\n\n"
                    f"🔍 Debug Info:\n"
                    f"- Token: `{self.token}`\n"
                    f"- Canal: {interaction.channel.mention if hasattr(interaction.channel, 'mention') else 'N/A'}\n"
                    f"- Tipo: `{type(interaction.channel).__name__}`\n\n"
                    f"Tente usar o botão dentro da thread da questão.",
                    ephemeral=True
                )
                return
            
            # Se não encontrou mensagem original, usa a mensagem da interação
            if not mensagem_original:
                mensagem_original = interaction.message
                print(f"⚠️ Usando mensagem da interação como fallback")
            
            # ✅ Continua com o código normal
            if self.values[0] == "resolver":
                await self.marcar_resolvida(interaction, thread, mensagem_original)
            elif self.values[0] == "deletar":
                await self.deletar_questao(interaction, thread, mensagem_original)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"❌ Erro no select: {e}")
            import traceback
            traceback.print_exc()
    
    async def marcar_resolvida(self, interaction, thread, mensagem_original):
        # Criar pasta temporária
        pasta_resumo = tempfile.mkdtemp(prefix=f"questao_{self.token}_")
        
        try:
            canal_resolvidas = interaction.guild.get_channel(CANAL_RESOLVIDAS_ID)
            if not canal_resolvidas:
                await interaction.followup.send("❌ Canal de resolvidas não configurado!", ephemeral=True)
                return
            
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            token = self.token
            materia = "Outros"
            
            for nome, canal_id in MATERIAS_CANAIS.items():
                if thread.parent.id == canal_id:
                    materia = nome
                    break
            
            usuarios_favoritaram = set()
            ids = obter_favoritos(token)
            for user_id in ids:
                member = interaction.guild.get_member(user_id)
                if member and not member.bot:
                    usuarios_favoritaram.add(member)
            
            print(f"📊 {len(usuarios_favoritaram)} usuários favoritaram a questão {token}")
            
            # Gerar conteúdo do TXT
            mensagens_texto = [
                "=" * 80,
                f"QUESTÃO RESOLVIDA - {thread.name}",
                f"TOKEN: {token}",
                "=" * 80,
                f"Data de Resolução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                f"Resolvida por: {interaction.user.name} ({interaction.user.id})",
                "=" * 80,
                ""
            ]
            
            if mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                mensagens_texto.extend(["INFORMAÇÕES DA QUESTÃO:", "-" * 80])
                if embed_original.title:
                    mensagens_texto.append(f"Título: {embed_original.title}")
                if embed_original.description:
                    desc = embed_original.description
                    if "Token:" in desc:
                        desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                    mensagens_texto.append(f"Descrição: {desc}")
                if embed_original.author:
                    mensagens_texto.append(f"Autor: {embed_original.author.name}")
                mensagens_texto.extend(["-" * 80, ""])
            
            mensagens_texto.extend(["HISTÓRICO DE MENSAGENS:", "=" * 80, ""])
            
            contador = 0
            mensagens_usuario = []
            async for message in thread.history(oldest_first=True, limit=None):
                if message.author.bot and not message.content and not message.embeds:
                    continue
                if not message.content and not message.attachments and not message.embeds:
                    continue
                mensagens_usuario.append(message)
            
            for message in mensagens_usuario:
                contador += 1
                timestamp = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
                autor = f"{message.author.name}"
                mensagens_texto.append(f"[{timestamp}] {autor}:")
                if message.content:
                    mensagens_texto.append(f"  {message.content}")
                if message.attachments:
                    for attachment in message.attachments:
                        mensagens_texto.append(f"  📎 Anexo: {attachment.filename} ({attachment.url})")
                mensagens_texto.append("")
            
            mensagens_texto.extend([
                "=" * 80,
                f"Total de mensagens: {contador}",
                f"Usuários que favoritaram: {len(usuarios_favoritaram)}",
                "=" * 80,
                ""
            ])
            
            arquivo_texto = "\n".join(mensagens_texto)
            
            # Salvar imagens do thread na pasta temporária
            await salvar_imagens_do_thread(thread, pasta_resumo)
            
            # Salvar TXT na pasta temporária
            with open(os.path.join(pasta_resumo, f"{token}.txt"), "w", encoding="utf-8") as f:
                f.write(arquivo_texto)
            
            # Salvar imagem da questão (se houver) na pasta temporária
            if mensagem_original and mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                if embed_original.image:
                    imagem_url = embed_original.image.url
                    nome_arquivo = "imagem_questao.png"
                    caminho_destino = os.path.join(pasta_resumo, nome_arquivo)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(imagem_url) as resp:
                            if resp.status == 200:
                                with open(caminho_destino, "wb") as f:
                                    f.write(await resp.read())
            
            # Salvar metadata na pasta temporária
            metadata_info = {
                "token": token,
                "materia": materia,
                "subarea": "Geral",
                "data_resolucao": datetime.now().isoformat(),
                "resolvida_por": {
                    "id": interaction.user.id,
                    "name": interaction.user.name
                },
                "total_mensagens": contador,
                "favoritos": len(usuarios_favoritaram)
            }
            with open(os.path.join(pasta_resumo, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata_info, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Metadata salvo: {token}")
            
            # Preparar arquivo para enviar no Discord
            arquivo_bytes = io.BytesIO(arquivo_texto.encode('utf-8'))
            arquivo_nome = f"{token}.txt"
            arquivo = discord.File(arquivo_bytes, filename=arquivo_nome)
            
            # Criar embed
            if mensagem_original.embeds:
                embed = mensagem_original.embeds[0].copy()
            else:
                embed = discord.Embed(title="Questão Resolvida", description="Conteúdo não disponível", color=discord.Color.green())
            
            embed.color = discord.Color.green()
            embed.title = embed.title.replace("📚", "✅") if "📚" in embed.title else f"✅ {embed.title}"
            
            fields_para_remover = []
            for i, field in enumerate(embed.fields):
                if field.name in ["📊 Status", "ID do usuário"]:
                    fields_para_remover.append(i)
            
            for i in sorted(fields_para_remover, reverse=True):
                embed.remove_field(i)
            
            embed.add_field(name="📊 Status", value="✅ Resolvida", inline=True)
            embed.add_field(name="👤 Resolvida por", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="📅 Data", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
            embed.add_field(name="💬 Mensagens", value=f"{contador} mensagens", inline=True)
            embed.add_field(name="⭐ Favoritos", value=f"{len(usuarios_favoritaram)} usuários", inline=True)
            embed.set_footer(text=f"Token: {token}")
            
            view_resolvidas = FavoritoButtonResolvidas(token)
            mensagem_resolvida = await canal_resolvidas.send(embed=embed, file=arquivo, view=view_resolvidas)
            
            # Notificar usuários que favoritaram
            if canal_favoritos and usuarios_favoritaram:
                print(f"📤 Enviando para {len(usuarios_favoritaram)} usuários...")
                for user in usuarios_favoritaram:
                    try:
                        thread_name = f"{materia} - {user.name}"
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
                            await thread_fav.add_user(user)
                            welcome_embed = discord.Embed(
                                title="⭐ Seus Favoritos",
                                description=f"Espaço privado para questões de **{materia}**!",
                                color=discord.Color.gold()
                            )
                            await thread_fav.send(embed=welcome_embed)
                        else:
                            thread_fav = thread_existente
                        
                        embed_favorito = discord.Embed(
                            title=f"✅ {token} • Resolvida",
                            description=embed.description if embed.description else "Questão resolvida!",
                            color=discord.Color.green(),
                            timestamp=datetime.now()
                        )
                        
                        if embed.image:
                            embed_favorito.set_image(url=embed.image.url)
                        if embed.author:
                            embed_favorito.set_author(name=embed.author.name, icon_url=embed.author.icon_url)
                        
                        embed_favorito.add_field(name="🏷️ Token", value=f"`{token}`", inline=True)
                        embed_favorito.add_field(name="👤 Resolvida por", value=interaction.user.mention, inline=True)
                        embed_favorito.add_field(name="🔗 Ver no Canal", value=f"[Ir para resolvidas]({mensagem_resolvida.jump_url})", inline=False)
                        embed_favorito.set_footer(text=f"Token: {token} • Você favoritou esta questão")
                        
                        await thread_fav.send(embed=embed_favorito)
                        print(f"  ✅ Enviado para {user.name}")
                    except Exception as e:
                        print(f"  ❌ Erro ao enviar para {user.name}: {e}")
                
                print(f"✅ Concluído! Enviado para favoritos de {len(usuarios_favoritaram)} usuários")
            
            # Remover favoritos
            remover_favoritos(token)
            
            # Deletar thread original
            try:
                await mensagem_original.delete()
                await thread.delete()
                print(f"🗑️ Questão {token} deletada")
            except Exception as e:
                print(f"Erro ao deletar: {e}")
            
            await interaction.followup.send(
                f"✅ **Questão `{token}` marcada como resolvida!**\n\n"
                f"📦 Movida para {canal_resolvidas.mention}\n"
                f"📄 Histórico: {contador} mensagens\n"
                f"⭐ Notificados: {len(usuarios_favoritaram)} usuários\n"
                f"🔗 [**Ver questão resolvida**]({mensagem_resolvida.jump_url})",
                ephemeral=True
            )
            
            # 📤 UPLOAD PARA O DRIVE (assíncrono, não bloqueia)
            try:
                print(f"📤 Iniciando upload para Drive: {token}")
                
                async def fazer_upload():
                    try:
                        await asyncio.to_thread(
                            upload_questao_para_drive,
                            pasta_resumo,  # ✅ Passa a pasta temporária
                            token,
                            materia,
                            "Geral"
                        )
                        print(f"✅ Upload concluído com sucesso: {token}")
                        
                        # 🗑️ Limpar pasta temporária após upload
                        try:
                            shutil.rmtree(pasta_resumo)
                            print(f"🧹 Pasta temporária removida: {token}")
                        except Exception as e:
                            print(f"⚠️ Erro ao limpar pasta temp: {e}")
                            
                    except Exception as e:
                        print(f"❌ ERRO no upload para Drive ({token}): {e}")
                        import traceback
                        traceback.print_exc()
                
                # Inicia task de upload em background
                asyncio.create_task(fazer_upload())
                
            except Exception as e:
                print(f"❌ Erro ao iniciar task de upload: {e}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao marcar resolvida: {e}")
            import traceback
            traceback.print_exc()
            
            # Limpar pasta temporária em caso de erro
            try:
                shutil.rmtree(pasta_resumo)
            except:
                pass
            
    async def deletar_questao(self, interaction, thread, mensagem_original):
        """Deleta uma questão permanentemente"""
        await interaction.followup.send(
            "⚠️ **Deletar esta questão?**\n\n"
            "Ação permanente! Deletando em 5 segundos...",
            ephemeral=True
        )
        await asyncio.sleep(5)
        
        # Remove favoritos
        remover_favoritos(self.token)
        
        try:
            # Deleta mensagem e thread
            await mensagem_original.delete()
            await thread.delete()
            print(f"🗑️ Questão {self.token} deletada permanentemente")
        except Exception as e:
            print(f"Erro ao deletar: {e}")


class StatusQuestaoView(ui.View):
    def __init__(self, token):
        super().__init__(timeout=None)
        self.token = token
        self.add_item(GerenciarQuestaoSelect(token))
    
    @ui.button(label="⭐ Favoritar", style=discord.ButtonStyle.primary, custom_id="favoritar_questao_aberta", row=1)
    async def favoritar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            token = self.token
            adicionar_favorito(token, interaction.user.id)
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
            canal_favoritos = interaction.guild.get_channel(CANAL_FAVORITOS_ID)
            if not canal_favoritos:
                await interaction.followup.send("❌ Canal de favoritos não encontrado!", ephemeral=True)
                return
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
                thread_fav = await canal_favoritos.create_thread(name=thread_name, type=discord.ChannelType.private_thread, auto_archive_duration=10080, invitable=False)
                await thread_fav.add_user(interaction.user)
                welcome_embed = discord.Embed(title="⭐ Seus Favoritos", description=f"Espaço privado para questões de **{materia}**!", color=discord.Color.gold())
                await thread_fav.send(embed=welcome_embed)
            else:
                thread_fav = thread_existente
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
            mensagem_para_embed = mensagem_original if mensagem_original else interaction.message
            embed = discord.Embed(title=f"📌 {token} • Em Aberto", description="⚠️ **Questão em aberto.** Snapshot do momento.\n\nVocê receberá uma notificação aqui quando esta questão for resolvida!", color=discord.Color.gold(), timestamp=datetime.now())
            if mensagem_para_embed.embeds:
                embed_original = mensagem_para_embed.embeds[0]
                if embed_original.description:
                    desc = embed_original.description
                    if "Token:" in desc:
                        desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                    embed.add_field(name="📝 Questão", value=desc[:800], inline=False)
                if embed_original.image:
                    embed.set_image(url=embed_original.image.url)
                if embed_original.author:
                    embed.set_author(name=embed_original.author.name, icon_url=embed_original.author.icon_url)
            if historico_texto and contador_msgs > 0:
                embed.add_field(name=f"💬 Discussão ({contador_msgs} msgs)", value=historico_texto[:900], inline=False)
            embed.add_field(name="🔗 Link Atual", value=f"[Questão em aberto]({thread.jump_url if thread else mensagem_para_embed.jump_url})\n⚠️ Inválido quando resolvida", inline=False)
            embed.set_footer(text=f"Token: {token} • Snapshot • Você será notificado quando resolvida")
            await thread_fav.send(embed=embed)
            await interaction.followup.send(f"✅ **`{token}` favoritada em {thread_fav.mention}!**\n\n🔔 Você receberá notificação quando resolvida\n", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao favoritar: {e}")
            import traceback
            traceback.print_exc()


class FavoritoButtonResolvidas(ui.View):
    def __init__(self, token):
        super().__init__(timeout=None)
        self.token = token
    
    @ui.button(label="⭐ Favoritar", style=discord.ButtonStyle.primary, custom_id="favoritar_resolvida", row=0)
    async def favoritar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            token = self.token
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
                thread = await canal_favoritos.create_thread(name=thread_name, type=discord.ChannelType.private_thread, auto_archive_duration=10080, invitable=False)
                await thread.add_user(interaction.user)
                welcome_embed = discord.Embed(title="⭐ Seus Favoritos", description=f"Espaço privado para **{materia}**!", color=discord.Color.gold())
                await thread.send(embed=welcome_embed)
            else:
                thread = thread_existente
            mensagem_original = interaction.message
            embed = discord.Embed(title=f"✅ {token} • Resolvida", color=discord.Color.green(), timestamp=datetime.now())
            if mensagem_original.embeds:
                embed_original = mensagem_original.embeds[0]
                desc = embed_original.description
                if desc and "Token:" in desc:
                    desc = desc.split('\n\n', 1)[1] if '\n\n' in desc else desc
                embed.description = desc
                if embed_original.image:
                    embed.set_image(url=embed_original.image.url)
                if embed_original.author:
                    embed.set_author(name=embed_original.author.name, icon_url=embed_original.author.icon_url)
            embed.add_field(name="🏷️ Token", value=f"`{token}`", inline=True)
            embed.add_field(name="🔗 Ver Original", value=f"[Clique aqui]({mensagem_original.jump_url})", inline=True)
            if mensagem_original.attachments:
                arquivo_url = mensagem_original.attachments[0].url
                embed.add_field(name="📄 Histórico TXT", value=f"[Download]({arquivo_url})", inline=False)
            embed.set_footer(text=f"Token: {token}")
            await thread.send(embed=embed)
            await interaction.followup.send(f"✅ `{token}` favoritada em {thread.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro: {e}")


async def salvar_imagens_do_thread(thread, pasta_destino: str):
    os.makedirs(pasta_destino, exist_ok=True)
    contador = 1
    async with aiohttp.ClientSession() as session:
        async for message in thread.history(oldest_first=True, limit=None):
            if not message.attachments:
                continue
            for attachment in message.attachments:
                if not attachment.content_type:
                    continue
                if not attachment.content_type.startswith("image/"):
                    continue
                extensao = os.path.splitext(attachment.filename)[1]
                nome_arquivo = f"imagem_{contador}{extensao}"
                caminho = os.path.join(pasta_destino, nome_arquivo)
                try:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            with open(caminho, "wb") as f:
                                f.write(await resp.read())
                            contador += 1
                except Exception as e:
                    print(f"❌ Erro ao baixar imagem {attachment.url}: {e}")


StatusQuestaoButton = StatusQuestaoView
FavoritoButton = StatusQuestaoView