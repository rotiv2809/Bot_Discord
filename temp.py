@bot.tree.command(name="verificar")
async def verificar(interaction: discord.Interaction, email: str):

    user = interaction.user
    guild = interaction.guild

    print(f"📧 [INSTÂNCIA {INSTANCE_ID}] Verificação solicitada por {user} - Email: {email}")

    # Resposta inicial (obrigatória para slash commands)
    await interaction.response.send_message(
        f"🔍 Verificando email: {email}...",
        ephemeral=True
    )

    # Verifica duplicidade de email
    if email_ja_registrado(email):
        await interaction.followup.send(
            "⚠️ Este email já está vinculado a outra conta do Discord! Caso seja um erro, por favor abra um ticket.",
            ephemeral=True
        )
        return

    aluno = consultar_aluno_por_email(email)

    if aluno:
        role = guild.get_role(ROLE_ID_ALUNO)

        if not role:
            await interaction.followup.send(
                f"❌ Erro: Cargo com ID {ROLE_ID_ALUNO} não encontrado no servidor!",
                ephemeral=True
            )
            print(f"❌ ROLE_ID_ALUNO {ROLE_ID_ALUNO} não existe no servidor {guild.name}")
            return

        # Tentar dar o cargo
        try:
            await user.add_roles(role)
            print(f"✅ Cargo adicionado para {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Erro: Bot não tem permissão para adicionar cargos!",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao adicionar cargo: {e}",
                ephemeral=True
            )
            return

        # Salvar no banco
        try:
            discord_id = str(user.id)
            username = str(user.display_name)
            guild_id = guild.id

            await salvar_verificacao(
                discord_id=discord_id,
                email=email,
                username=username,
                guild_id=guild_id
            )

            await interaction.followup.send(
                f"✅ Verificado! Cargo de aluno adicionado.",
                ephemeral=True
            )
            print(f"✅ {user} verificado e salvo no banco")

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Cargo dado, mas erro ao salvar no banco: {e}",
                ephemeral=True
            )
            print(f"❌ Erro ao salvar no Supabase: {e}")

    else:
        await interaction.followup.send(
            "❌ Email não encontrado na base de alunos.",
            ephemeral=True
        )
        print(f"❌ Email {email} não encontrado na API")
