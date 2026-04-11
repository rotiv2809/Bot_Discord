import discord
import asyncio
from database_consult import consultar_aluno_por_email, consultar_expiracao_em_dias, consultar_cargos_por_email
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
            
            # Verifica se o usuário está em processo de verificação
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

                        # Adicionar cargos de curso (EsPCEx, ESA, EFOMM, etc.)
                        cargos_curso = await asyncio.to_thread(consultar_cargos_por_email, email)
                        cargos_adicionados = []
                        for cargo_id in cargos_curso:
                            cargo = guild.get_role(cargo_id)
                            if cargo:
                                await member.add_roles(cargo)
                                cargos_adicionados.append(cargo.name)
                                print(f"🎖️ Cargo de curso adicionado: {cargo.name} → {message.author}")
                        
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
                            description=f"Bem-vindo(a)!",
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
                            supabase.table("verificacoes") \
                                .delete() \
                                .eq("discord_id", str(discord_id)) \
                                .execute()
                            continue

                        status = await asyncio.to_thread(consultar_aluno_por_email, email)

                        if status != "active":
                            role = guild.get_role(ROLE_ID_ALUNO)
                            if role and role in member.roles:
                                await member.remove_roles(role)
                                print(f"🚫 Cargo removido de {member} ({email})")

                            supabase.table("verificacoes") \
                                 .delete() \
                                 .eq("discord_id", str(discord_id)) \
                                 .execute()
                    
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
    
    # Iniciar sistema
    iniciar_verificacao_diaria()