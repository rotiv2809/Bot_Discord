import discord
import asyncio
from database_consult import consultar_aluno_por_email
from discord.ext import tasks
from datetime import time, datetime, timedelta


def setup_events(context):
    ID_CANAL_ENVIAR_QUESTOES = context['ID_CANAL_ENVIAR_QUESTOES']
    """Registra todos os eventos do bot"""
    bot = context['bot']
    supabase = context['supabase']
    tickets_verificacao_ativa = context['tickets_verificacao_ativa']
    ID_DO_CANAL_VERIFICACOES = context['ID_DO_CANAL_VERIFICACOES']
    ROLE_ID_ALUNO = context['ROLE_ID_ALUNO']
    CATEGORIA_VERIFICACAO_ID = context['CATEGORIA_VERIFICACAO_ID']
    
    def email_ja_registrado(email: str) -> bool:
        try:
            response = supabase.table("verificacoes").select("email").eq("email", email).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Erro ao verificar email no banco: {e}")
            return False
    
    async def salvar_verificacao(discord_id: str, email: str, username: str, guild_id: str) -> dict:
        """Salva a verificação no Supabase"""
        try:
            data = {
                'discord_id': discord_id,
                'email': email,
                'username': username,
                'guild_id': guild_id,
                'verificado_em': discord.utils.utcnow().isoformat()
            }
            
            response = supabase.table('verificacoes').insert(data).execute()
            
            print(f"✅ Verificação salva: {username} ({email})")
            return {'success': True, 'data': response.data}
        
        except Exception as e:
            print(f"❌ Erro ao salvar no Supabase: {e}")
            return {'success': False, 'error': str(e)}
    
    @bot.event
    async def on_message(message: discord.Message):
        # Ignora mensagens do bot
        if message.author.bot:
            return

        # Limpa mensagens no canal de verificações
        if message.channel.id == ID_DO_CANAL_VERIFICACOES:
            await message.delete()
            try:
                await message.author.send("⚠️ Use apenas o comando `/verificar` neste canal!")
            except:
                pass
            return
        
        # Limpa mensagens no canal de envio de questões
        if message.channel.id == ID_CANAL_ENVIAR_QUESTOES:
            await message.delete()
            try:
                await message.author.send(
                    "📌 Este canal é apenas para usar o comando `/criarquestao`."
                )
            except:
                pass
            return

        # Verifica se é um canal de ticket
        if not message.channel.name.startswith("ticket-"):
            return

        # Verifica se o ticket está ativo para verificação
        if message.channel.id not in tickets_verificacao_ativa:
            return

        email = message.content.strip()

        # Validação simples de email
        if "@" not in email or "." not in email:
            await message.channel.send("⚠️ Por favor, envie um email válido!")
            return

        await message.channel.send(f"🔍 Verificando email: `{email}`...")

        # Email já vinculado a outro Discord
        if email_ja_registrado(email):
            await message.channel.send(
                "⚠️ Este email já está vinculado a outra conta do Discord!"
            )
            return

        # 🔥 CONSULTAR STATUS DO ALUNO
        status = consultar_aluno_por_email(email)

        # 🔴 Caso 1: email não encontrado
        if status == None:
            # ✅ NOVA LÓGICA - VERIFICAÇÃO MANUAL
            print(f"⚠️ Email não encontrado na base: {email}")
            
            # Enviar mensagem inicial no ticket
            await message.channel.send(
                f"⏳ **Verificação Manual Necessária**\n\n"
                f"📧 Email `{email}` não foi encontrado automaticamente na base de dados.\n\n"
                f"🔍 **Nossa equipe foi notificada!**\n"
                f"⏱️ Por favor, aguarde alguns minutos.\n\n"
                f"Um moderador irá validar manualmente se você está cadastrado.\n"
                f"Você receberá uma resposta aqui no ticket em breve.\n\n"
                f"_Tempo médio de resposta: 5-15 minutos_"
            )
            
            # Enviar para canal de moderadores
            from scripts.verificacao_manual import solicitar_verificacao_manual
            sucesso = await solicitar_verificacao_manual(
                bot,
                message.author.id,
                str(message.author),
                email,
                message.channel.id
            )
            
            if sucesso:
                print(f"✅ Solicitação de verificação manual enviada: {email}")
            else:
                print(f"❌ Falha ao enviar solicitação de verificação manual: {email}")
                
                # Fallback: mostrar embed de "não cadastrado" se falhar
                embed = discord.Embed(
                    title="🚀 Comece sua preparação com a Tropa do Arcanjo",
                    description=(
                        "❌ **Este email ainda não está cadastrado em nossa base.**\n\n"
                        "Antes de tudo, confirme se o email informado está **correto** e tente novamente.\n\n"
                        "Se você busca **aprovação em concursos militares**, aqui você encontra um método direto, "
                        "materiais atualizados e conteúdo focado exatamente no que cai nas provas.\n\n"
                        "👉 **[Clique aqui e conheça nossos cursos](https://www.tropadoarcanjo.com.br/cursos/?utm_source=www.google.com&sck=03c062e1-ad19-488a-8144-d81c63196029||)**\n\n"
                        "📌 **Já é aluno?** Caso tenha digitado o email corretamente e ainda assim não conseguiu a verificação, "
                        "clique em <#1431767520280317992> para abrir um **ticket de atendimento**.\n"
                        "Nossa equipe irá te ajudar **o mais rápido possível** ✅"
                    ),
                    color=discord.Color.blue()
                )

                try:
                    file = discord.File(
                        fp="images/imagembanner.png",
                        filename="imagembanner.png"
                    )
                    embed.set_image(url="attachment://imagembanner.png")
                    embed.set_footer(text="Tropa do Arcanjo")
                    
                    await message.channel.send(
                        "📢 **Não localizamos este email em nossa base no momento.**",
                        embed=embed,
                        file=file
                    )
                except FileNotFoundError:
                    # Se a imagem não existir, envia sem ela
                    await message.channel.send(
                        "📢 **Não localizamos este email em nossa base no momento.**",
                        embed=embed
                    )
            
            return  # ✅ Importante: não continua o fluxo

        # 🟡 Caso 2: já foi aluno, mas assinatura não está ativa
        if status == "inactive":
            embed = discord.Embed(
                title="🎓 Continue sua preparação com a Tropa do Arcanjo",
                description=(
                    "⚠️ **Sua assinatura não está ativa no momento.**\n\n"
                    "Você já conhece nosso método e sabe como ele funciona.\n"
                    "Agora é a hora de **retomar sua preparação com foco total**, "
                    "materiais atualizados e condições exclusivas para ex-alunos.\n\n"
                    "👉 **[Clique aqui e garanta seu acesso agora](https://www.tropadoarcanjo.com.br/cursos/?utm_source=www.google.com&sck=03c062e1-ad19-488a-8144-d81c63196029||)**"
                ),
                color=discord.Color.orange()
            )

            try:
                file = discord.File(
                    fp="images/imagembanner.png",
                    filename="imagembanner.png"
                )
                embed.set_image(url="attachment://imagembanner.png")
                embed.set_footer(text="Tropa do Arcanjo")

                await message.channel.send(
                    "🚨 **Identificamos este email em nossa base, mas a assinatura está inativa.**",
                    embed=embed,
                    file=file
                )
            except FileNotFoundError:
                await message.channel.send(
                    "🚨 **Identificamos este email em nossa base, mas a assinatura está inativa.**",
                    embed=embed
                )
            
            return

        # ✅ Caso 3: assinatura ativa → segue fluxo normal
        if status == "active":
            role = message.guild.get_role(ROLE_ID_ALUNO)

            if not role:
                await message.channel.send("❌ Erro: Cargo de aluno não encontrado!")
                return

            try:
                await message.author.add_roles(role)

                discord_id = str(message.author.id)
                username = str(message.author.display_name)
                guild_id = message.guild.id

                await salvar_verificacao(
                    discord_id=discord_id,
                    email=email,
                    username=username,
                    guild_id=guild_id
                )

                await message.channel.send(
                    "✅ **Verificado com sucesso!**\n"
                    "Cargo de aluno adicionado.\n\n"
                    "Este ticket será fechado em 5 segundos..."
                )

                print(f"✅ {message.author} verificado - Email: {email}")

                tickets_verificacao_ativa.discard(message.channel.id)

                await asyncio.sleep(5)
                await message.channel.delete()

            except Exception as e:
                await message.channel.send(f"❌ Erro ao aplicar verificação: {e}")
                print(f"❌ Erro na verificação: {e}")

    
    # ✅ LIMPEZA AUTOMÁTICA DE TICKETS ANTIGOS
    def iniciar_limpeza_tickets():
        bot = context['bot']
        CATEGORIA_VERIFICACAO_ID = context['CATEGORIA_VERIFICACAO_ID']
        
        @tasks.loop(hours=24)  # Roda 1x por dia
        async def limpar_tickets_antigos():
            """Limpa tickets com mais de 7 dias automaticamente"""
            try:
                print("🧹 Iniciando limpeza automática de tickets antigos...")
                
                for guild in bot.guilds:
                    categoria = guild.get_channel(CATEGORIA_VERIFICACAO_ID)
                    
                    if not categoria:
                        continue
                    
                    agora = datetime.now()
                    deletados = 0
                    
                    for canal in categoria.channels:
                        if not canal.name.startswith("ticket-"):
                            continue
                        
                        # Verificar idade do canal
                        idade = agora - canal.created_at.replace(tzinfo=None)
                        
                        if idade > timedelta(days=7):  # Mais de 7 dias
                            try:
                                await canal.delete()
                                deletados += 1
                                await asyncio.sleep(0.5)  # Evitar rate limit
                                print(f"  🗑️ Ticket deletado: {canal.name} ({idade.days} dias)")
                            except Exception as e:
                                print(f"  ❌ Erro ao deletar {canal.name}: {e}")
                    
                    if deletados > 0:
                        print(f"✅ Limpeza automática: {deletados} tickets deletados no servidor {guild.name}")
                    else:
                        print(f"✅ Limpeza automática: Nenhum ticket antigo encontrado em {guild.name}")
                        
            except Exception as e:
                print(f"❌ Erro na limpeza automática: {e}")
                import traceback
                traceback.print_exc()
        
        @limpar_tickets_antigos.before_loop
        async def before_limpar_tickets():
            await bot.wait_until_ready()
            print("⏳ Aguardando bot ficar pronto para iniciar limpeza de tickets")
        
        limpar_tickets_antigos.start()
        print("🧹 Sistema de limpeza automática de tickets iniciado")

            
    def iniciar_verificacao_diaria():
        bot = context['bot']
        supabase = context['supabase']
        ROLE_ID_ALUNO = context['ROLE_ID_ALUNO']

        @tasks.loop(hours=6)
        async def verificacao_diaria():
            print("🌙 Iniciando verificação diária de assinaturas...")

            try:
                response = supabase.table("verificacoes").select("*").execute()
                verificacoes = response.data or []

                print(f"📦 {len(verificacoes)} verificações encontradas")

                # ✅ Processar em lotes de 10 para não travar o bot
                TAMANHO_LOTE = 10
                
                for i in range(0, len(verificacoes), TAMANHO_LOTE):
                    lote = verificacoes[i:i + TAMANHO_LOTE]
                    
                    if len(verificacoes) > TAMANHO_LOTE:
                        print(f"🔄 Processando lote {i//TAMANHO_LOTE + 1}/{(len(verificacoes) + TAMANHO_LOTE - 1)//TAMANHO_LOTE}")
                    
                    for v in lote:
                        discord_id = int(v["discord_id"])
                        email = v["email"]
                        guild_id = int(v["guild_id"])

                        guild = bot.get_guild(guild_id)
                        if not guild:
                            print(f"❌ Guild {guild_id} não encontrada")
                            continue

                        member = guild.get_member(discord_id)

                        # 1️⃣ Usuário saiu do servidor → apaga do banco
                        if not member:
                            print(f"🧹 Usuário {discord_id} não está mais no servidor, removendo registro")
                            supabase.table("verificacoes") \
                                .delete() \
                                .eq("discord_id", str(discord_id)) \
                                .execute()
                            continue

                        # 2️⃣ Verifica se a assinatura ainda está ativa
                        # ✅ CORREÇÃO: Rodar de forma não-bloqueante
                        status = await asyncio.to_thread(consultar_aluno_por_email, email)

                        if status != "active":
                            role = guild.get_role(ROLE_ID_ALUNO)
                            if role and role in member.roles:
                                await member.remove_roles(role)
                                print(f"🚫 Cargo removido de {member} ({email})")

                            # Apagar o vínculo quando cancelar
                            supabase.table("verificacoes") \
                                 .delete() \
                                 .eq("discord_id", str(discord_id)) \
                                 .execute()
                    
                    # ✅ Pausa entre lotes
                    if i + TAMANHO_LOTE < len(verificacoes):
                        await asyncio.sleep(2)
                
                print(f"✅ Verificação diária concluída!")

            except Exception as e:
                print(f"❌ Erro na verificação diária: {e}")
                import traceback
                traceback.print_exc()

        @verificacao_diaria.before_loop
        async def before():
            await bot.wait_until_ready()
            print("⏳ Aguardando bot ficar pronto para iniciar verificação diária")

        verificacao_diaria.start()
    
    # Iniciar sistemas
    iniciar_limpeza_tickets()
    iniciar_verificacao_diaria()
