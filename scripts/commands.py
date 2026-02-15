import discord
from discord import app_commands
from discord.ext import commands
import discord
from datetime import datetime
import asyncio
from scripts.utils import salvar_questao_local, usuario_ja_perguntou_hoje
from scripts.views import FavoritoButton, StatusQuestaoButton, StatusQuestaoView
from scripts.enquete_views import EnqueteView
import random
import string


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
    
    @bot.tree.command(name="enquete", description="Criar uma enquete com ou sem sistema de XP")
    @app_commands.describe(
        pergunta="Pergunta da enquete (opcional)",
        alternativa_a="Alternativa A (opcional)",
        alternativa_b="Alternativa B (opcional)",
        alternativa_c="Alternativa C (opcional)",
        alternativa_d="Alternativa D (opcional)",
        alternativa_e="Alternativa E (opcional)",
        resposta_correta="Alternativa correta (A, B, C, D ou E) - obrigatória apenas se valer XP",
        valer_xp="Se os participantes devem ganhar XP ao responder",
        canal="Canal onde a enquete será enviada (opcional)"
    )
    @app_commands.choices(resposta_correta=[
        app_commands.Choice(name="A", value="A"),
        app_commands.Choice(name="B", value="B"),
        app_commands.Choice(name="C", value="C"),
        app_commands.Choice(name="D", value="D"),
        app_commands.Choice(name="E", value="E")
    ])
    async def enquete(
        interaction: discord.Interaction,
        pergunta: str = None,
        alternativa_a: str = None,
        alternativa_b: str = None,
        resposta_correta: str = None,
        alternativa_c: str = None,
        alternativa_d: str = None,
        alternativa_e: str = None,
        valer_xp: bool = True,
        canal: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            pergunta = pergunta or "Sem pergunta definida."

            # Montar lista de alternativas
            alternativas_dict = {
                "A": alternativa_a or "Opção A",
                "B": alternativa_b or "Opção B"
            }
            
            if alternativa_c:
                alternativas_dict["C"] = alternativa_c
            if alternativa_d:
                alternativas_dict["D"] = alternativa_d
            if alternativa_e:
                alternativas_dict["E"] = alternativa_e
            
            # Validar resposta correta quando a enquete vale XP
            if valer_xp:
                if resposta_correta not in alternativas_dict:
                    await interaction.followup.send(
                        "❌ Para enquete com XP, você precisa informar uma resposta correta válida entre as alternativas fornecidas.",
                        ephemeral=True
                    )
                    return
            
            # Gerar ID único para a enquete
            enquete_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Criar embed
            embed = discord.Embed(
                title="📊 Enquete",
                description=f"**{pergunta}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Adicionar alternativas ao embed
            alternativas_texto = []
            emojis = {"A": "🇦", "B": "🇧", "C": "🇨", "D": "🇩", "E": "🇪"}
            
            for letra, texto in alternativas_dict.items():
                alternativas_texto.append(f"{emojis[letra]} **{letra}:** {texto}")
            
            embed.add_field(
                name="📝 Alternativas",
                value="\n".join(alternativas_texto),
                inline=False
            )
            
            if valer_xp:
                embed.add_field(
                    name="🎁 Recompensas",
                    value=(
                        f"• Responder: **+10 XP**\n"
                        f"• Acertar: **+50 XP** (5x bonus)"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎁 Recompensas",
                    value="Esta enquete **não vale XP**.",
                    inline=False
                )
            
            embed.add_field(
                name="👥 Respostas",
                value="0 pessoas responderam",
                inline=False
            )
            
            embed.set_footer(text=f"Criado por {interaction.user.name} • ID: {enquete_id}")
            
            # Criar view com botões
            alternativas_lista = list(alternativas_dict.keys())
            view = EnqueteView(
                alternativas=alternativas_lista,
                resposta_correta=resposta_correta,
                enquete_id=enquete_id,
                valer_xp=valer_xp
            )
            
            # Enviar enquete
            canal_destino = canal if canal else interaction.channel
            mensagem_enquete = await canal_destino.send(embed=embed, view=view)
            
            # Resposta de confirmação
            resposta_admin = (
                f"✅ Resposta correta: **{resposta_correta}** (oculta dos participantes)\n"
                if valer_xp else
                "🧠 Modo: enquete sem XP\n"
            )

            await interaction.followup.send(
                f"✅ **Enquete criada com sucesso!**\n\n"
                f"📊 Enquete: `{enquete_id}`\n"
                f"📍 Canal: {canal_destino.mention}\n"
                f"{resposta_admin}"
                f"🔗 [Ir para enquete]({mensagem_enquete.jump_url})",
                ephemeral=True
            )
            
            print(f"📊 Enquete criada: {enquete_id} por {interaction.user} - Resposta: {resposta_correta}")
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao criar enquete: {str(e)}",
                ephemeral=True
            )
            print(f"Erro em /enquete: {e}")
            import traceback
            traceback.print_exc()
    @bot.tree.command(name="nivel", description="Ver seu nível e XP")
    @app_commands.describe(
        usuario="Ver nível de outro usuário (opcional)"
    )
    async def nivel(interaction: discord.Interaction, usuario: discord.Member = None):
        await interaction.response.defer(ephemeral=False)
        
        try:
            from scripts.xp_system import consultar_xp, xp_para_nivel
            
            alvo = usuario if usuario else interaction.user
            
            xp_total, nivel, xp_atual_nivel, xp_proximo_nivel = await consultar_xp(
                supabase,
                alvo.id
            )
            
            if xp_total is None:
                await interaction.followup.send(
                    f"❌ {alvo.mention} ainda não tem XP registrado!",
                    ephemeral=True
                )
                return
            
            # Calcular progresso
            progresso_percentual = (xp_atual_nivel / xp_proximo_nivel) * 100
            
            # Barra de progresso visual
            barra_tamanho = 20
            barra_preenchida = int((progresso_percentual / 100) * barra_tamanho)
            barra = "█" * barra_preenchida + "░" * (barra_tamanho - barra_preenchida)
            
            embed = discord.Embed(
                title=f"📊 Nível de {alvo.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=alvo.display_avatar.url)
            
            embed.add_field(
                name="⭐ Nível",
                value=f"**{nivel}**",
                inline=True
            )
            
            embed.add_field(
                name="💎 XP Total",
                value=f"**{xp_total}** XP",
                inline=True
            )
            
            embed.add_field(
                name="📈 Progresso",
                value=f"{progresso_percentual:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="📊 Próximo Nível",
                value=f"`{barra}`\n{xp_atual_nivel}/{xp_proximo_nivel} XP",
                inline=False
            )
            
            # XP necessário para próximo nível
            xp_faltando = xp_proximo_nivel - xp_atual_nivel
            embed.add_field(
                name="🎯 Faltam",
                value=f"**{xp_faltando}** XP para o nível {nivel + 1}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao consultar nível: {str(e)}",
                ephemeral=True
            )
            print(f"Erro em /nivel: {e}")


    @bot.tree.command(name="ranking", description="Ver o ranking de XP do servidor")
    @app_commands.describe(
        limite="Quantos usuários mostrar (padrão: 10)"
    )
    async def ranking(interaction: discord.Interaction, limite: int = 10):
        await interaction.response.defer(ephemeral=False)
        
        try:
            from scripts.xp_system import ranking_xp
            
            if limite < 1:
                limite = 10
            if limite > 25:
                limite = 25
            
            top_usuarios = await ranking_xp(supabase, interaction.guild.id, limite)
            
            if not top_usuarios:
                await interaction.followup.send(
                    "❌ Ainda não há usuários com XP neste servidor!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🏆 Ranking de XP - Top {limite}",
                description=f"**{interaction.guild.name}**",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            # Emojis de medalha
            medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            ranking_texto = []
            for i, usuario_data in enumerate(top_usuarios, start=1):
                discord_id = usuario_data['discord_user_id']
                xp = usuario_data['xp_total']
                nivel = usuario_data['nivel']
                username = usuario_data['discord_username']
                
                # Tentar pegar o membro atual
                member = interaction.guild.get_member(discord_id)
                nome = member.mention if member else f"`{username}`"
                
                medalha = medalhas.get(i, f"**{i}.**")
                ranking_texto.append(f"{medalha} {nome} - Nível **{nivel}** ({xp:,} XP)")
            
            embed.description = "\n".join(ranking_texto)
            
            embed.set_footer(text=f"Solicitado por {interaction.user.name}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao buscar ranking: {str(e)}",
                ephemeral=True
            )
            print(f"Erro em /ranking: {e}")


    @bot.tree.command(name="dar_xp", description="[ADMIN] Adicionar XP manualmente a um usuário")
    @app_commands.describe(
        usuario="Usuário que receberá o XP",
        quantidade="Quantidade de XP a adicionar"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def dar_xp(interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        
        try:
            from scripts.xp_system import adicionar_xp
            
            if quantidade <= 0:
                await interaction.followup.send("❌ A quantidade deve ser maior que 0!", ephemeral=True)
                return
            
            novo_xp, novo_nivel, subiu_nivel, nivel_anterior = await adicionar_xp(
                supabase,
                usuario.id,
                str(usuario),
                interaction.guild.id,
                quantidade,
                interaction.guild
            )
            
            embed = discord.Embed(
                title="✅ XP Adicionado",
                description=f"**{quantidade} XP** adicionado a {usuario.mention}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="💎 XP Total", value=f"{novo_xp} XP", inline=True)
            embed.add_field(name="⭐ Nível", value=f"{novo_nivel}", inline=True)
            
            if subiu_nivel and nivel_anterior > 0:
                embed.add_field(
                    name="🎉 Level Up!",
                    value=f"Subiu do nível {nivel_anterior} para {novo_nivel}!",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Notificar usuário
            try:
                await usuario.send(
                    f"🎁 Você recebeu **{quantidade} XP** de {interaction.user.mention} no servidor **{interaction.guild.name}**!\n"
                    f"XP total: **{novo_xp}** | Nível: **{novo_nivel}**"
                )
            except:
                pass
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro em /dar_xp: {e}")


    @bot.tree.command(name="resetar_xp", description="[ADMIN] Resetar XP de um usuário")
    @app_commands.describe(
        usuario="Usuário que terá o XP resetado"
    )
    @app_commands.default_permissions(administrator=True)
    async def resetar_xp(interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Deletar do banco
            supabase.table('user_xp').delete().eq('discord_user_id', usuario.id).execute()
            
            # Remover todos os cargos de nível
            from scripts.xp_system import CARGOS_NIVEIS
            for cargo_id in CARGOS_NIVEIS.values():
                if cargo_id:
                    cargo = interaction.guild.get_role(cargo_id)
                    if cargo and cargo in usuario.roles:
                        await usuario.remove_roles(cargo)
            
            await interaction.followup.send(
                f"✅ XP de {usuario.mention} foi resetado!",
                ephemeral=True
            )
            
            print(f"🔄 XP resetado: {usuario} por {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro em /resetar_xp: {e}")
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
    
