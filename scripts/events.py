import discord
import asyncio
from database_consult import consultar_aluno_por_email, consultar_cargos_por_email, consultar_expiracao_em_dias
from discord.ext import tasks
from datetime import time, datetime, timedelta
from dados import CANAL_VERIFICACOES_PENDENTES

BOT_BASE_URL = "https://seu-bot-questoes.squarecloud.app"


def setup_events(context):
    ID_CANAL_ENVIAR_QUESTOES = context['ID_CANAL_ENVIAR_QUESTOES']
    """Registra todos os eventos do bot"""
    bot = context['bot']
    supabase = context['supabase']
    tickets_verificacao_ativa = context['tickets_verificacao_ativa']
    tickets_curso_ativa = context['tickets_curso_ativa']
    ID_DO_CANAL_VERIFICACOES = context['ID_DO_CANAL_VERIFICACOES']
    ROLE_ID_ALUNO = context['ROLE_ID_ALUNO']

    # IDs de todos os cargos de curso para comparação
    from database_consult import CURSOS_PRINCIPAIS, CURSOS_SECUNDARIOS
    TODOS_CARGOS_CURSO = set(CURSOS_PRINCIPAIS.values()) | set(CURSOS_SECUNDARIOS.values())
    
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

        # ===== VERIFICAÇÃO VIA DM =====
        if isinstance(message.channel, discord.DMChannel):
            user_id = message.author.id

            # ── Fluxo 2: atribuição de cargo para validados manualmente ──
            if user_id in tickets_curso_ativa:
                email = message.content.strip().lower()

                if '@' not in email or '.' not in email:
                    await message.channel.send(
                        "❌ **Email inválido!**\n\n"
                        "Por favor, digite um email válido.\n"
                        "Exemplo: `seu.nome@gmail.com`"
                    )
                    return

                processando = await message.channel.send(f"🔍 Verificando email: `{email}`...")

                try:
                    # Busca guild do usuário
                    guild = None
                    for g in bot.guilds:
                        member = g.get_member(user_id)
                        if member:
                            guild = g
                            break

                    if not guild:
                        await processando.edit(content="❌ Erro: Servidor não encontrado!")
                        tickets_curso_ativa.discard(user_id)
                        return

                    member = guild.get_member(user_id)
                    cargos_curso, alerta_memberkit = await asyncio.to_thread(consultar_cargos_por_email, email)

                    if cargos_curso:
                        # Encontrou curso — atribui cargos e salva verificação
                        cargos_adicionados = []
                        for cargo_id in cargos_curso:
                            cargo = guild.get_role(cargo_id)
                            if cargo:
                                await member.add_roles(cargo)
                                cargos_adicionados.append(cargo.name)

                        # Salva na tabela verificacoes se ainda não estiver
                        ja_registrado = supabase.table("verificacoes") \
                            .select("discord_id") \
                            .eq("discord_id", str(user_id)) \
                            .execute()

                        if not ja_registrado.data:
                            await salvar_verificacao(
                                discord_id=str(user_id),
                                email=email,
                                username=str(message.author),
                                guild_id=str(guild.id)
                            )
                        else:
                            # Atualiza email se já existia
                            supabase.table("verificacoes") \
                                .update({"email": email}) \
                                .eq("discord_id", str(user_id)) \
                                .execute()

                        embed_ok = discord.Embed(
                            title="✅ Curso identificado!",
                            description="Seus cargos foram atualizados com sucesso.",
                            color=discord.Color.green()
                        )
                        embed_ok.add_field(
                            name="🎓 Cursos",
                            value="\n".join(f"• {c}" for c in cargos_adicionados),
                            inline=False
                        )
                        await processando.edit(content=None, embed=embed_ok)

                    else:
                        # Não encontrou curso — notifica canal com opções de cargo
                        await processando.edit(
                            content=(
                                "⚠️ **Email não encontrado na base de dados.**\n\n"
                                "Nossa equipe foi notificada e irá atribuir seu cargo manualmente em breve!"
                            )
                        )

                        canal = bot.get_channel(CANAL_VERIFICACOES_PENDENTES)
                        if canal:
                            from scripts.verificacao_manual import BotoesCargoManual
                            embed_alerta = discord.Embed(
                                title="🔔 Cargo de curso não identificado",
                                description=(
                                    f"O email **`{email}`** não foi encontrado em nenhuma base de dados.\n\n"
                                    f"Selecione manualmente qual cargo atribuir ao aluno:"
                                ),
                                color=discord.Color.orange()
                            )
                            embed_alerta.add_field(name="👤 Usuário", value=member.mention, inline=True)
                            embed_alerta.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                            embed_alerta.set_footer(text="Validado manualmente — sem curso identificado")
                            view = BotoesCargoManual(
                                discord_user_id=user_id,
                                email=email,
                                guild=guild
                            )
                            await canal.send(embed=embed_alerta, view=view)

                except Exception as e:
                    await processando.edit(content=f"❌ Erro: {str(e)}")
                    print(f"❌ Erro no fluxo de cargo via DM: {e}")
                    import traceback
                    traceback.print_exc()

                tickets_curso_ativa.discard(user_id)
                return

            # ── Fluxo 1: verificação normal ──
            if user_id in tickets_verificacao_ativa:
                email = message.content.strip()
                
                # Validação básica de email
                if '@' not in email or '.' not in email:
                    await message.channel.send(
                        "❌ **Email inválido!**\n\n"
                        "Por favor, digite um email válido.\n"
                        "Exemplo: `seu.nome@escola.edu.br`"
                    )
                    return
                
                # Mensagem de processamento
                processando = await message.channel.send(f"🔍 Verificando email: `{email}`...")
                
                try:
                    # Verificar se email já está registrado
                    if email_ja_registrado(email):
                        await processando.edit(
                            content="⚠️ **Este email já está vinculado a outra conta do Discord!**"
                        )
                        tickets_verificacao_ativa.discard(user_id)
                        return
                    
                    # 🔥 CONSULTAR STATUS DO ALUNO
                    status = await asyncio.to_thread(consultar_aluno_por_email, email)
                    
                    # 🔴 Caso 1: Email não encontrado
                    if status == None:
                        print(f"⚠️ Email não encontrado na base: {email}")
                        
                        await processando.edit(
                            content=(
                                "⏳ **Verificação Manual Necessária**\n\n"
                                f"📧 Email `{email}` não foi encontrado automaticamente.\n\n"
                                "🔍 **Nossa equipe foi notificada!**\n"
                                "⏱️ Aguarde alguns minutos para validação manual.\n\n"
                                "_Tempo médio: 5-15 minutos_"
                            )
                        )
                        
                        # Buscar servidor do usuário
                        guild = None
                        for g in bot.guilds:
                            member = g.get_member(user_id)
                            if member:
                                guild = g
                                break
                        
                        if guild:
                            # Enviar para verificação manual
                            from scripts.verificacao_manual import solicitar_verificacao_manual
                            
                            sucesso = await solicitar_verificacao_manual(
                                bot=bot,
                                discord_user_id=user_id,
                                discord_username=str(message.author),
                                email=email,
                                dm_channel_id=None
                            )
                            
                            if not sucesso:
                                # Fallback: embed de não cadastrado
                                embed = discord.Embed(
                                    title="🚀 Comece sua preparação com a Tropa do Arcanjo",
                                    description=(
                                        "❌ **Este email ainda não está cadastrado em nossa base.**\n\n"
                                        "Antes de tudo, confirme se o email informado está **correto** e tente novamente.\n\n"
                                        "Se você busca **aprovação em concursos militares**, aqui você encontra um método direto, "
                                        "materiais atualizados e conteúdo focado exatamente no que cai nas provas.\n\n"
                                        "👉 **[Clique aqui e conheça nossos cursos](https://www.tropadoarcanjo.com.br/cursos/)**\n\n"
                                        "📌 **Já é aluno?** Entre em contato com o suporte."
                                    ),
                                    color=discord.Color.blue()
                                )
                                
                                try:
                                    file = discord.File(fp="images/imagembanner.png", filename="imagembanner.png")
                                    embed.set_image(url="attachment://imagembanner.png")
                                    embed.set_footer(text="Tropa do Arcanjo")
                                    await message.channel.send(embed=embed, file=file)
                                except FileNotFoundError:
                                    await message.channel.send(embed=embed)
                        
                        tickets_verificacao_ativa.discard(user_id)
                        return
                    
                    # 🟡 Caso 2: Assinatura inativa
                    if status == "inactive":
                        embed = discord.Embed(
                            title="🎓 Continue sua preparação com a Tropa do Arcanjo",
                            description=(
                                "⚠️ **Sua assinatura não está ativa no momento.**\n\n"
                                "Você já conhece nosso método e sabe como ele funciona.\n"
                                "Agora é a hora de **retomar sua preparação com foco total**.\n\n"
                                "👉 **[Clique aqui e garanta seu acesso agora](https://www.tropadoarcanjo.com.br/cursos/)**"
                            ),
                            color=discord.Color.orange()
                        )
                        
                        try:
                            file = discord.File(fp="images/imagembanner.png", filename="imagembanner.png")
                            embed.set_image(url="attachment://imagembanner.png")
                            embed.set_footer(text="Tropa do Arcanjo")
                            await message.channel.send(
                                "🚨 **Assinatura inativa detectada.**",
                                embed=embed,
                                file=file
                            )
                        except FileNotFoundError:
                            await message.channel.send("🚨 **Assinatura inativa detectada.**", embed=embed)
                        
                        tickets_verificacao_ativa.discard(user_id)
                        return
                    
                    # ✅ Caso 3: Assinatura ativa
                    if status == "active":
                        # Buscar servidor
                        guild = None
                        for g in bot.guilds:
                            member = g.get_member(user_id)
                            if member:
                                guild = g
                                break
                        
                        if not guild:
                            await processando.edit(content="❌ Erro: Servidor não encontrado!")
                            tickets_verificacao_ativa.discard(user_id)
                            return
                        
                        member = guild.get_member(user_id)
                        if not member:
                            await processando.edit(content="❌ Erro: Você não está no servidor!")
                            tickets_verificacao_ativa.discard(user_id)
                            return
                        
                        # Adicionar cargo base de aluno
                        role = guild.get_role(ROLE_ID_ALUNO)
                        if role:
                            await member.add_roles(role)

                        # Adicionar cargos de curso
                        cargos_curso, alerta_memberkit = await asyncio.to_thread(consultar_cargos_por_email, email)
                        cargos_adicionados = []
                        for cargo_id in cargos_curso:
                            cargo = guild.get_role(cargo_id)
                            if cargo:
                                await member.add_roles(cargo)
                                cargos_adicionados.append(cargo.name)
                                print(f"🎖️ Cargo de curso adicionado: {cargo.name} → {message.author}")

                        # Se encontrado só no memberkit antigo → notifica canal
                        if alerta_memberkit:
                            canal = bot.get_channel(CANAL_VERIFICACOES_PENDENTES)
                            if canal:
                                embed_alerta = discord.Embed(
                                    title="⚠️ Aluno sem registro de curso identificável",
                                    description=(
                                        f"O email **`{email}`** foi verificado com sucesso, mas foi encontrado "
                                        f"**apenas no MemberKit antigo**, sem informação do curso.\n\n"
                                        f"O cargo de aluno foi dado, mas o cargo de curso não pôde ser atribuído automaticamente."
                                    ),
                                    color=discord.Color.yellow()
                                )
                                embed_alerta.add_field(name="👤 Usuário", value=member.mention, inline=True)
                                embed_alerta.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                                embed_alerta.set_footer(text="Verificação automática — requer ação manual")
                                try:
                                    await canal.send(embed=embed_alerta)
                                except Exception as e:
                                    print(f"❌ Erro ao notificar canal: {e}")
                        
                        # Salvar verificação
                        await salvar_verificacao(
                            discord_id=str(user_id),
                            email=email,
                            username=str(message.author),
                            guild_id=str(guild.id)
                        )
                        
                        # Mensagem de sucesso
                        embed_sucesso = discord.Embed(
                            title="✅ Verificação Aprovada!",
                            description="Bem-vindo(a)!",
                            color=discord.Color.green()
                        )
                        
                        embed_sucesso.add_field(
                            name="📧 Email",
                            value=f"`{email}`",
                            inline=False
                        )

                        if cargos_adicionados:
                            embed_sucesso.add_field(
                                name="🎓 Cursos identificados",
                                value="\n".join(f"• {c}" for c in cargos_adicionados),
                                inline=False
                            )
                        elif alerta_memberkit:
                            embed_sucesso.add_field(
                                name="🎓 Curso",
                                value="Não foi possível identificar seu curso automaticamente. Nossa equipe irá atribuir o cargo em breve!",
                                inline=False
                            )
                        
                        embed_sucesso.add_field(
                            name="🔓 Acesso",
                            value="Você agora tem acesso completo ao servidor!",
                            inline=False
                        )
                        
                        embed_sucesso.set_footer(text=f"Servidor: {guild.name}")
                        
                        await processando.edit(content=None, embed=embed_sucesso)
                        
                        tickets_verificacao_ativa.discard(user_id)
                        
                        print(f"✅ Verificação automática via DM aprovada: {email} -> {message.author}")
                        return
                
                except Exception as e:
                    await processando.edit(
                        content=f"❌ Erro ao verificar: {str(e)}\n\nTente novamente mais tarde."
                    )
                    tickets_verificacao_ativa.discard(user_id)
                    print(f"❌ Erro na verificação via DM: {e}")
                    import traceback
                    traceback.print_exc()
                
                return
        
        # Processar comandos
        await bot.process_commands(message)
    
    
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
                        if not member:
                            print(f"🧹 Usuário {discord_id} não está mais no servidor, removendo registro")
                            supabase.table("verificacoes").delete().eq("discord_id", str(discord_id)).execute()
                            continue

                        status = await asyncio.to_thread(consultar_aluno_por_email, email)

                        if status == "active":
                            # Garante cargo base
                            role = guild.get_role(ROLE_ID_ALUNO)
                            if role and role not in member.roles:
                                await member.add_roles(role)
                                print(f"✅ Cargo base recolocado em {member} ({email})")

                            # ── Corrige cargos de curso ──
                            cargos_corretos, alerta_memberkit = await asyncio.to_thread(consultar_cargos_por_email, email)
                            cargos_corretos_set = set(cargos_corretos)

                            # Cargos de curso que o membro tem atualmente
                            cargos_atuais = {r.id for r in member.roles if r.id in TODOS_CARGOS_CURSO}

                            # Remove cargos errados
                            for cargo_id in cargos_atuais - cargos_corretos_set:
                                cargo = guild.get_role(cargo_id)
                                if cargo:
                                    await member.remove_roles(cargo)
                                    print(f"🔄 Cargo de curso removido: {cargo.name} de {member}")

                            # Adiciona cargos faltando
                            for cargo_id in cargos_corretos_set - cargos_atuais:
                                cargo = guild.get_role(cargo_id)
                                if cargo:
                                    await member.add_roles(cargo)
                                    print(f"🔄 Cargo de curso adicionado: {cargo.name} para {member}")

                            if alerta_memberkit:
                                canal = bot.get_channel(CANAL_VERIFICACOES_PENDENTES)
                                if canal:
                                    embed_alerta = discord.Embed(
                                        title="⚠️ Aluno sem curso identificável",
                                        description=(
                                            f"O email **`{email}`** foi encontrado apenas no MemberKit antigo, "
                                            f"sem informação de curso.\n\n**O cargo de curso não pôde ser atribuído automaticamente.**"
                                        ),
                                        color=discord.Color.yellow()
                                    )
                                    embed_alerta.add_field(name="👤 Usuário", value=member.mention, inline=True)
                                    embed_alerta.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                                    await canal.send(embed=embed_alerta)

                        elif status is None:
                            # Não encontrado — mantém cargo, notifica canal
                            print(f"⚠️ Email {email} não encontrado — cargo mantido, notificando canal")
                            canal = bot.get_channel(CANAL_VERIFICACOES_PENDENTES)
                            if canal:
                                embed_alerta = discord.Embed(
                                    title="⚠️ Aluno não encontrado na base",
                                    description=(
                                        f"O email **`{email}`** não foi encontrado em nenhuma base de dados "
                                        f"durante a verificação automática.\n\n"
                                        f"**O cargo NÃO foi removido.** Verifique manualmente."
                                    ),
                                    color=discord.Color.yellow()
                                )
                                embed_alerta.add_field(name="👤 Usuário", value=member.mention, inline=True)
                                embed_alerta.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                                embed_alerta.set_footer(text="Verificação automática")
                                try:
                                    await canal.send(embed=embed_alerta)
                                except Exception as e:
                                    print(f"❌ Erro ao notificar canal: {e}")

                        elif status == "inactive":
                            # Inativo — remove cargo e manda DM
                            role = guild.get_role(ROLE_ID_ALUNO)
                            if role and role in member.roles:
                                await member.remove_roles(role)
                                print(f"🚫 Cargo removido de {member} ({email}) — inativo")
                                try:
                                    link_renovacao = f"{BOT_BASE_URL}/renovar?discord_id={discord_id}"
                                    embed_fim = discord.Embed(
                                        title="Seu acesso à Tropa foi encerrado.",
                                        description=(
                                            "E vou te falar a verdade…\n\n"
                                            "👉 você vai fazer falta por aqui.\n\n"
                                            "A Tropa continua.\n"
                                            "As aulas continuam.\n"
                                            "A galera continua no ritmo.\n\n"
                                            "Mas espero que você não pare.\n\n"
                                            "Que continue estudando.\n"
                                            "Que continue buscando sua aprovação.\n\n"
                                            "E se decidir voltar…\n"
                                            "a Tropa vai estar aqui pra você terminar o que começou.\n\n"
                                            f"🔗 [Voltar para a Tropa]({link_renovacao})"
                                        ),
                                        color=discord.Color.greyple()
                                    )
                                    await member.send(embed=embed_fim)
                                except discord.Forbidden:
                                    pass
                                except Exception as e:
                                    print(f"❌ Erro ao enviar DM de encerramento: {e}")

                            supabase.table("verificacoes").delete().eq("discord_id", str(discord_id)).execute()

                    if i + TAMANHO_LOTE < len(verificacoes):
                        await asyncio.sleep(2)

                # ── Após verificar todos: detectar alunos sem cargo de curso ──
                print("🔍 Verificando alunos sem cargo de curso...")
                for guild in bot.guilds:
                    role_aluno = guild.get_role(ROLE_ID_ALUNO)
                    if not role_aluno:
                        continue

                    for member in guild.members:
                        if role_aluno not in member.roles:
                            continue

                        # Tem cargo de aluno — verifica se tem algum cargo de curso
                        tem_cargo_curso = any(r.id in TODOS_CARGOS_CURSO for r in member.roles)
                        if tem_cargo_curso:
                            continue

                        # Não tem cargo de curso — verifica se está na tabela verificacoes
                        reg = supabase.table("verificacoes") \
                            .select("discord_id") \
                            .eq("discord_id", str(member.id)) \
                            .execute()

                        if reg.data:
                            # Está na tabela mas sem cargo de curso → a correção já foi feita acima
                            # Só cai aqui se não foi encontrado nas bases (alerta_memberkit)
                            continue

                        # Não está na tabela → foi validado manualmente, pede email via DM
                        if member.id not in tickets_curso_ativa:
                            tickets_curso_ativa.add(member.id)
                            try:
                                embed_dm = discord.Embed(
                                    title="📋 Identificação de curso necessária",
                                    description=(
                                        "Olá! Identificamos que você tem acesso ao servidor, "
                                        "mas ainda não identificamos qual curso você está fazendo.\n\n"
                                        "Por favor, **digite seu email cadastrado** para que possamos "
                                        "atribuir o cargo do seu curso automaticamente."
                                    ),
                                    color=discord.Color.blurple()
                                )
                                embed_dm.set_footer(text="Tropa do Arcanjo")
                                await member.send(embed=embed_dm)
                                print(f"📬 DM de identificação enviada para {member}")
                            except discord.Forbidden:
                                tickets_curso_ativa.discard(member.id)
                                print(f"⚠️ DMs fechadas para {member}")
                            except Exception as e:
                                tickets_curso_ativa.discard(member.id)
                                print(f"❌ Erro ao enviar DM para {member}: {e}")

                        await asyncio.sleep(0.5)

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
    
    # Iniciar sistema
    iniciar_verificacao_diaria()