import discord
import asyncio
from database_consult import consultar_aluno_por_email

def setup_events(context):
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
    async def on_message(message):
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
        
        # Verifica se é um canal de ticket E se está marcado para verificação
        if not message.channel.name.startswith("ticket-"):
            return
        
        if message.channel.id not in tickets_verificacao_ativa:
            return
        
        email = message.content.strip()
        
        # Valida se parece com email
        if "@" not in email or "." not in email:
            await message.channel.send("⚠️ Por favor, envie um email válido!")
            return
        
        await message.channel.send(f"🔍 Verificando email: {email}...")
        
        if email_ja_registrado(email):
            await message.channel.send("⚠️ Este email já está vinculado a outra conta do Discord!")
            return
        
        aluno = consultar_aluno_por_email(email)
        
        if aluno is None or not aluno[0]:
            await message.channel.send("❌ Email não encontrado na base de alunos.")
            print(f"❌ Email {email} não encontrado")
            return
        
        role = message.guild.get_role(ROLE_ID_ALUNO)
        
        if not role:
            await message.channel.send(f"❌ Erro: Cargo não encontrado!")
            return
        
        try:
            if aluno[1] == 'active':
                await message.author.add_roles(role)
                
                discord_id = str(message.author.id)
                username = str(message.author.display_name)
                guild_id = message.guild.id
                await salvar_verificacao(discord_id=discord_id, email=email, username=username, guild_id=guild_id)
                
                await message.channel.send(
                    f"✅ **Verificado com sucesso!**\n"
                    f"Cargo de aluno adicionado.\n\n"
                    f"Este ticket será fechado em 5 segundos..."
                )
                
                print(f"✅ {message.author} verificado - Email: {email}")
                
                tickets_verificacao_ativa.discard(message.channel.id)
                
                await asyncio.sleep(5)
                await message.channel.delete()
            else:
                await message.channel.send(
                    "❌ Aluno encontrado, mas inscrição não ativa, por que não voltar a ser aluno?"
                )
        
        except Exception as e:
            await message.channel.send(f"❌ Erro: {e}")
            print(f"❌ Erro na verificação: {e}")