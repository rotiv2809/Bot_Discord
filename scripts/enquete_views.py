import discord
from discord import ui
from datetime import datetime
from scripts.xp_system import adicionar_xp, XP_POR_RESPOSTA, XP_RESPOSTA_CORRETA_MULTIPLIER

class EnqueteButton(ui.Button):
    def __init__(self, alternativa: str, emoji: str, resposta_correta: str, enquete_id: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=alternativa,
            emoji=emoji,
            custom_id=f"enquete_{enquete_id}_{alternativa}"
        )
        self.alternativa = alternativa
        self.resposta_correta = resposta_correta
        self.enquete_id = enquete_id
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            from main import bot_context
            supabase = bot_context['supabase']
            
            user_id = interaction.user.id
            message_id = interaction.message.id
            
            # Verificar se já respondeu
            response = supabase.table('enquete_respostas') \
                .select('*') \
                .eq('enquete_message_id', message_id) \
                .eq('discord_user_id', user_id) \
                .execute()
            
            if response.data and len(response.data) > 0:
                await interaction.followup.send(
                    "⚠️ Você já respondeu esta enquete!",
                    ephemeral=True
                )
                return
            
            # Calcular XP ganho
            acertou = self.alternativa == self.resposta_correta
            xp_base = XP_POR_RESPOSTA
            xp_ganho = xp_base * XP_RESPOSTA_CORRETA_MULTIPLIER if acertou else xp_base
            
            # Registrar resposta
            supabase.table('enquete_respostas').insert({
                'enquete_message_id': message_id,
                'discord_user_id': user_id,
                'alternativa_escolhida': self.alternativa,
                'xp_ganho': xp_ganho
            }).execute()
            
            # Adicionar XP
            novo_xp, novo_nivel, subiu_nivel, nivel_anterior = await adicionar_xp(
                supabase,
                user_id,
                str(interaction.user),
                interaction.guild.id,
                xp_ganho,
                interaction.guild
            )
            
            # Mensagem de resposta
            if acertou:
                embed = discord.Embed(
                    title="✅ Resposta Correta!",
                    description=f"Você escolheu a alternativa **{self.alternativa}** e acertou!",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Resposta Incorreta",
                    description=f"Você escolheu **{self.alternativa}**. A resposta correta era **{self.resposta_correta}**.",
                    color=discord.Color.red()
                )
            
            embed.add_field(
                name="🎁 XP Ganho",
                value=f"+{xp_ganho} XP",
                inline=True
            )
            
            embed.add_field(
                name="📊 XP Total",
                value=f"{novo_xp} XP",
                inline=True
            )
            
            embed.add_field(
                name="⭐ Nível",
                value=f"Nível {novo_nivel}",
                inline=True
            )
            
            # Se subiu de nível
            if subiu_nivel and nivel_anterior > 0:
                embed.add_field(
                    name="🎉 Level Up!",
                    value=f"Você subiu do nível {nivel_anterior} para o nível {novo_nivel}!",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Atualizar contador de respostas no embed original
            await self.atualizar_contador(interaction.message, supabase)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao processar resposta: {str(e)}",
                ephemeral=True
            )
            print(f"Erro no botão da enquete: {e}")
            import traceback
            traceback.print_exc()
    
    async def atualizar_contador(self, message, supabase):
        """Atualiza o contador de respostas no embed"""
        try:
            # Contar respostas
            response = supabase.table('enquete_respostas') \
                .select('alternativa_escolhida', count='exact') \
                .eq('enquete_message_id', message.id) \
                .execute()
            
            total_respostas = response.count if response.count else 0
            
            # Atualizar embed
            if message.embeds:
                embed = message.embeds[0]
                
                # Atualizar ou adicionar campo de respostas
                campo_encontrado = False
                for i, field in enumerate(embed.fields):
                    if field.name == "👥 Respostas":
                        embed.set_field_at(i, name="👥 Respostas", value=f"{total_respostas} pessoas responderam", inline=False)
                        campo_encontrado = True
                        break
                
                if not campo_encontrado:
                    embed.add_field(name="👥 Respostas", value=f"{total_respostas} pessoas responderam", inline=False)
                
                await message.edit(embed=embed)
                
        except Exception as e:
            print(f"Erro ao atualizar contador: {e}")


class EnqueteView(ui.View):
    def __init__(self, alternativas: list, resposta_correta: str, enquete_id: str):
        super().__init__(timeout=None)
        
        emojis = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯"]
        
        for i, alternativa in enumerate(alternativas):
            self.add_item(EnqueteButton(
                alternativa=alternativa,
                emoji=emojis[i] if i < len(emojis) else "📌",
                resposta_correta=resposta_correta,
                enquete_id=enquete_id
            ))