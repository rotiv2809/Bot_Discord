import discord
from discord import ui
from datetime import datetime
from dados import CANAL_VERIFICACOES_PENDENTES

class BotoesVerificacaoManual(ui.View):
    """Botões para aprovar/rejeitar verificação"""
    
    def __init__(self, discord_user_id: int, email: str, dm_channel_id: int = None):
        super().__init__(timeout=None)
        self.discord_user_id = discord_user_id
        self.email = email
        self.dm_channel_id = dm_channel_id
    
    @ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_verificacao")
    async def aprovar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Desabilitar botões
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            # Buscar guild e member
            guild = interaction.guild
            member = guild.get_member(self.discord_user_id)
            
            if not member:
                await interaction.followup.send("❌ Usuário não encontrado no servidor!", ephemeral=True)
                return
            
            # Adicionar cargo
            from main import bot_context
            role_id = bot_context['ROLE_ID_ALUNO']
            role = guild.get_role(role_id)
            
            if role:
                await member.add_roles(role)
            
            # Atualizar embed da solicitação
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ APROVADO"
            embed.add_field(
                name="👮 Aprovado por",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="⏰ Horário",
                value=datetime.now().strftime("%d/%m/%Y %H:%M"),
                inline=True
            )
            await interaction.message.edit(embed=embed, view=self)
            
            # Notificar usuário via DM
            try:
                embed_aprovado = discord.Embed(
                    title="✅ Verificação Aprovada!",
                    description=f"Sua verificação foi aprovada manualmente!",
                    color=discord.Color.green()
                )
                
                embed_aprovado.add_field(
                    name="📧 Email",
                    value=f"`{self.email}`",
                    inline=False
                )
                
                embed_aprovado.add_field(
                    name="🎓 Status",
                    value="Você agora tem acesso completo ao servidor!",
                    inline=False
                )
                
                embed_aprovado.set_footer(text=f"Aprovado por {interaction.user.name}")
                
                await member.send(embed=embed_aprovado)
            except:
                pass  # Se não conseguir enviar DM, ignora
            
            await interaction.followup.send(
                f"✅ Verificação aprovada com sucesso!\n"
                f"👤 {member.mention} agora tem acesso.",
                ephemeral=True
            )
            
            # Arquivar thread se for thread
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.edit(archived=True, locked=True)
            
            print(f"✅ Verificação manual APROVADA: {self.email} por {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao aprovar verificação: {e}")
            import traceback
            traceback.print_exc()
    
    @ui.button(label="❌ Rejeitar", style=discord.ButtonStyle.danger, custom_id="rejeitar_verificacao")
    async def rejeitar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Desabilitar botões
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            # Buscar membro
            guild = interaction.guild
            member = guild.get_member(self.discord_user_id)
            
            # Atualizar embed
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = "❌ REJEITADO"
            embed.add_field(
                name="👮 Rejeitado por",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="⏰ Horário",
                value=datetime.now().strftime("%d/%m/%Y %H:%M"),
                inline=True
            )
            await interaction.message.edit(embed=embed, view=self)
            
            # Notificar usuário via DM
            if member:
                try:
                    embed_rejeitado = discord.Embed(
                        title="❌ Verificação Rejeitada",
                        description=f"Sua verificação não foi aprovada.",
                        color=discord.Color.red()
                    )
                    
                    embed_rejeitado.add_field(
                        name="📧 Email",
                        value=f"`{self.email}`",
                        inline=False
                    )
                    
                    embed_rejeitado.add_field(
                        name="💡 O que fazer?",
                        value=(
                            "• Verifique se digitou o email corretamente\n"
                            "• Entre em contato com o suporte abrindo um ticket em https://discord.com/channels/1431694508663505066/1431767520280317992\n"
                            "• Tente novamente com `/verificar`"
                        ),
                        inline=False
                    )
                    
                    await member.send(embed=embed_rejeitado)
                except:
                    pass
            
            await interaction.followup.send(
                f"❌ Verificação rejeitada.\n"
                f"Usuário foi notificado via DM.",
                ephemeral=True
            )
            
            # Arquivar thread
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.edit(archived=True, locked=True)
            
            print(f"❌ Verificação manual REJEITADA: {self.email} por {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
            print(f"Erro ao rejeitar verificação: {e}")
            import traceback
            traceback.print_exc()


async def solicitar_verificacao_manual(bot, discord_user_id: int, discord_username: str, email: str, dm_channel_id: int = None):
    """
    Envia solicitação de verificação manual para canal de moderadores
    """
    try:
        canal = bot.get_channel(CANAL_VERIFICACOES_PENDENTES)
        if not canal:
            print(f"❌ Canal de verificações pendentes não encontrado!")
            return False
        
        # Criar embed
        embed = discord.Embed(
            title="🔔 VERIFICAÇÃO MANUAL NECESSÁRIA",
            description=(
                f"**Email não encontrado na base de dados**\n\n"
                f"Um usuário está tentando se verificar mas o email "
                f"não foi encontrado automaticamente."
            ),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Usuário",
            value=f"<@{discord_user_id}>\n`{discord_username}`",
            inline=False
        )
        
        embed.add_field(
            name="📧 Email",
            value=f"`{email}`",
            inline=False
        )
        
        embed.add_field(
            name="💬 Verificação",
            value="Via **DM** (Mensagem Direta)",
            inline=False
        )
        
        embed.add_field(
            name="❓ O que fazer?",
            value=(
                "• Verifique se o email está na base de alunos\n"
                "• Clique em **✅ Aprovar** se for aluno válido\n"
                "• Clique em **❌ Rejeitar** se não for aluno"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"ID: {discord_user_id}")
        
        # Criar view com botões
        view = BotoesVerificacaoManual(discord_user_id, email, dm_channel_id)
        
        # Enviar mensagem
        mensagem = await canal.send(
            content="@here Nova verificação pendente!",
            embed=embed,
            view=view
        )
        
        # Criar thread para discussão
        thread = await mensagem.create_thread(
            name=f"Verificação: {discord_username}",
            auto_archive_duration=1440  # 24h
        )
        
        await thread.send(
            f"💬 Use esta thread para discutir a verificação de **{discord_username}**\n"
            f"📧 Email: `{email}`"
        )
        
        print(f"✅ Solicitação de verificação manual enviada: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao solicitar verificação manual: {e}")
        import traceback
        traceback.print_exc()
        return False

# ─────────────────────────────────────────────
# BOTÕES DE CARGO MANUAL (quando email não encontrado no fluxo de curso)
# ─────────────────────────────────────────────

class BotoesCargoManual(ui.View):
    """Botões para o mod escolher qual cargo de curso atribuir manualmente"""

    OPCOES_CARGO = [
        ("EsPCEx",      "espcex",   "🎯"),
        ("EFOMM/AFA",   "efomm",    "⚓"),
        ("ESA",         "esa",      "🪖"),
        ("EEAR",        "eear",     "✈️"),
        ("EPCAR",       "epcar",    "🚀"),
        ("Nivelamento", "nivelamento", "📚"),
        ("Mentoria",    "mentoria", "🧠"),
        ("Live",        "live",     "🎥"),
    ]

    def __init__(self, discord_user_id: int, email: str, guild):
        super().__init__(timeout=None)
        self.discord_user_id = discord_user_id
        self.email = email
        self.guild = guild

        from database_consult import CURSOS_PRINCIPAIS, CURSOS_SECUNDARIOS
        self.todos_cargos = {**CURSOS_PRINCIPAIS, **CURSOS_SECUNDARIOS}

        for label, keyword, emoji in self.OPCOES_CARGO:
            cargo_id = self.todos_cargos.get(keyword, 0)
            if not cargo_id:
                continue
            btn = ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"cargo_manual_{discord_user_id}_{keyword}"
            )
            btn.callback = self._fazer_callback(keyword, cargo_id)
            self.add_item(btn)

    def _fazer_callback(self, keyword: str, cargo_id: int):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            try:
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

                member = self.guild.get_member(self.discord_user_id)
                if not member:
                    await interaction.followup.send("❌ Usuário não encontrado no servidor.", ephemeral=True)
                    return

                cargo = self.guild.get_role(cargo_id)
                if cargo:
                    await member.add_roles(cargo)

                # Atualiza embed
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.green()
                embed.title = "✅ Cargo atribuído manualmente"
                embed.add_field(name="🎖️ Cargo", value=cargo.name if cargo else keyword, inline=True)
                embed.add_field(name="👮 Por", value=interaction.user.mention, inline=True)
                embed.add_field(name="⏰ Horário", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
                await interaction.message.edit(embed=embed, view=self)

                await interaction.followup.send(
                    f"✅ Cargo **{cargo.name if cargo else keyword}** atribuído a {member.mention}.",
                    ephemeral=True
                )

                # Notifica o aluno via DM
                try:
                    embed_dm = discord.Embed(
                        title="✅ Cargo de curso atribuído!",
                        description=f"Nossa equipe identificou seu curso e adicionou o cargo **{cargo.name if cargo else keyword}**.",
                        color=discord.Color.green()
                    )
                    embed_dm.set_footer(text="Tropa do Arcanjo")
                    await member.send(embed=embed_dm)
                except Exception:
                    pass

                print(f"✅ Cargo manual '{keyword}' atribuído a {member} por {interaction.user}")

            except Exception as e:
                await interaction.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)
                print(f"Erro em BotoesCargoManual: {e}")

        return callback