import discord
from discord.ext import commands

class Control(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def help(self, ctx):
        await ctx.send('All available commands and descriptions can be found at: \nhttps://github.com/aytiel/PHTM-b0t/tree/gw2-uploader')

    @commands.command()
    async def shutdown(self, ctx):
        guild = ctx.guild
        if guild is None:
            has_perms = False
        else:
            has_perms = ctx.channel.permissions_for(guild.me).manage_messages
        if has_perms:
            await ctx.message.delete()
            for message in self.bot.clear_list:
                try:
                    await message.delete()
                except discord.NotFound:
                    continue
            self.bot.clear_list.clear()
        else:
            await ctx.send('No tengo permisos para borrar mensajes. Habilita esto en el futuro.')
            
        if self.bot.owner_id == 0 or not self.bot.owner_id == ctx.author.id:
            return await ctx.send('Actualmente no tienes permiso para usar el bot. Solo el usuario actual puede usar el bot.')    
            
        await self.bot.logout()
        await self.bot.close()
        
def setup(bot):
    bot.add_cog(Control(bot))