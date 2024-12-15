import json
import requests
import calendar
import datetime
import time
import glob
import os
import copy
import re
from tkinter import filedialog
from tkinter import *

import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import settings.config

class Arcdps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs_order = {}
        self.show_time = False
        self.num_logs = 0
        
        with open('cogs/data/logs.json', 'r') as logs_data:
            self.logs = json.load(logs_data)
    
    @commands.command()
    async def login(self, ctx):#, username=None, password=None):
        guild = ctx.guild
        if guild is None:
            has_perms = False
        else:
            has_perms = ctx.channel.permissions_for(guild.me).manage_messages
        if has_perms:
            await ctx.message.delete()
        else:
            await ctx.send('No tengo permisos para borrar mensajes. Habilita esto en el futuro.')

        with open('cogs/data/user.json', 'r') as key_file:
            key = json.load(key_file)
        #if not username is None and not password is None:
        #    raidar_endpoint = 'https://www.gw2raidar.com/api/v2/token'
        #    cred = {'username': username, 'password': password}
        #    res = requests.post(raidar_endpoint, data=cred)
        #    if not res.status_code == 200:
        #        target = await ctx.send('ERROR :robot: : GW2Raidar login failed.')
        #        self.bot.clear_list.append(target)
        #        return
        #    else:
        #        token = res.json()['token']
        #        key['key'] = 'Token {}'.format(token)
        #        self.bot.owner_key = key['key']
        key['id'] = ctx.author.id
        self.bot.owner_id = ctx.author.id
        key['name'] = ctx.author.name
        await self.bot.update_status(key['name'])
        
        confirmed = False
        while len(self.bot.owner_filepath) == 0 or not confirmed:
            out = 'Utiliza el explorador de archivos para seleccionar tu carpeta de logs.'
            try:
                target = await ctx.author.send(out)
            except discord.Forbidden:
                target = await ctx.send(out)
            root = Tk()
            root.withdraw()
            key['filepath'] = filedialog.askdirectory(initialdir = "/", title = "Selecciona tu carpeta de logs")
            self.bot.owner_filepath = key['filepath']

            try:
                message = await ctx.author.send('Tu carpeta de logs seleccionada es:\n```{}\nClick ✅ para confirmar, ❌ para reintentar```'.format(self.bot.owner_filepath))
            except discord.Forbidden:
                message = await ctx.send('Tu orden de log seleccionado es:\n```{}\nClick ✅ para confirmar, ❌ para reintentar```'.format(self.bot.owner_filepath))
            await message.add_reaction('✅')
            await message.add_reaction('❌')
        
            def r_check(r, user):
                return user == ctx.author and r.count > 1
            
            ans, user = await self.bot.wait_for('reaction_add', check=r_check)
            if str(ans.emoji) == '✅':
                confirmed = True
            await message.delete()
            await target.delete()
        
        with open('cogs/data/user.json', 'w') as key_file:
            json.dump(key, key_file, indent=4)
        target = await ctx.send('Inicio de sesión correcto')
        self.bot.clear_list.append(target)
        
    @commands.command()
    async def upload(self, ctx, type: str, *argv):
        guild = ctx.guild
        if guild is None:
            has_perms = False
        else:
            has_perms = ctx.channel.permissions_for(guild.me).manage_messages
        
        if has_perms:
            await ctx.message.delete()
        else:
            await ctx.send('No tengo permisos para borrar mensajes. Habilita esto en el futuro.')
            return
        
        if self.bot.owner_id == 0 or not self.bot.owner_id == ctx.author.id:
            target = await ctx.send('Actualmente no tienes permiso para usar el bot. Solo el usuario actual puede usar el bot.')
            self.bot.clear_list.append(target)
            return
        
        if len(self.bot.owner_filepath) == 0:
            target = await ctx.send('No se encontró ninguna carpeta de logs. Inicia sesión y selecciona tu carpeta arcdps.cbtlogs.')
            self.bot.clear_list.append(target)
            return
        
        if not type in ['raids', 'fractals']:
            target = await ctx.send('Indica si deseas subir logs de "raids" o "fractales".')
            self.bot.clear_list.append(target)
            return 
        
        self.__init__(self.bot)
        i = 0
        title = []
        while i < len(argv):
            if argv[i] == '--time':
                self.show_time = True
                i += 1
            elif argv[i] == '--num':
                if i == len(argv)-1:
                    target = await ctx.send('Ingresa el número de logs para el parámetro `--num`')
                    self.bot.clear_list.append(target)
                    return
                try:
                    self.num_logs = int(argv[i+1])
                    if self.num_logs <= 0:
                        target = await ctx.send('Número inválido de logs para el parámetro `--num`.')
                        self.bot.clear_list.append(target)
                        return
                    i += 2
                except ValueError:
                    target = await ctx.send('Número inválido de logs para el parámetro `--num`.')
                    self.bot.clear_list.append(target)
                    return
            else:
                title.append(argv[i])
                i += 1
        
        mode = await self.set_logs_order(ctx, type)
        
        logs_length = 0
        error_logs = 0
        for e in self.logs_order:
            for b in self.logs_order[e]:
                print('------------------------------')
                logs_length += 1
                path = ['{0}/{1}/'.format(self.bot.owner_filepath, x) for x in self.logs[type][e][b]['name']]
                path_filter = set(p for p in path if os.path.exists(p))
                
                if len(path_filter) == 0:
                    target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: BLOODSTONE`')
                    self.bot.clear_list.append(target)
                    error_logs += 1
                    continue
                
                all_files = []
                for path in path_filter:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_name, file_ext = os.path.splitext(file)
                            if file_ext in ['.zevtc', '.evtc'] or os.path.splitext(file_name)[1] == '.evtc':
                                file_path = os.path.join(root, file)
                                modified_date = os.path.getmtime(file_path)
                                all_files.append((file_path, modified_date))
                
                if len(all_files) == 0:
                    target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: EMPYREAL`')
                    self.bot.clear_list.append(target)
                    error_logs += 1
                    continue
                elif len(all_files) < self.num_logs:
                    target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: DRAGONITE`')
                    self.bot.clear_list.append(target)
                    error_logs += 1
                    continue
                
                all_files.sort(key=lambda x: x[1], reverse=True)
                if mode == 'dps.report' and self.num_logs > 0:
                    latest_files = [x[0] for x in all_files[:self.num_logs]]
                    latest_files.reverse()
                latest_file = all_files[0][0]
                self.logs[type][e][b]['filename'] = os.path.basename(latest_file)
                
                if mode == 'dps.report' or mode == 'Both':
                    print(f'Uploading {b}: dps.report...')
                    dps_endpoint = 'https://dps.report/uploadContent?json=1&generator=ei'
                        
                    if mode == 'dps.report' and self.num_logs > 0:
                        self.logs[type][e][b]['dps.report'] = []
                        if self.show_time:
                            self.logs[type][e][b]['duration'] = []
                        error_multi_logs = 0
                        for count, lf in enumerate(latest_files, 1):
                            print(f'Subiendo log {count}...')
                            with open(lf, 'rb') as file:
                                files = {'file': file}
                                res = requests.post(dps_endpoint, files=files)
                                if not res.status_code == 200:
                                    target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}({count}). `Error Code: LYSSA`')
                                    self.bot.clear_list.append(target)
                                    self.logs[type][e][b]['dps.report'].append('about:blank')
                                    error_multi_logs += 1
                                    continue
                                try:
                                    json_data = res.json()
                                    log = json_data['permalink']
                                    self.logs[type][e][b]['dps.report'].append(log)
                                    if self.show_time:
                                        if json_data['encounter']['jsonAvailable']:
                                            params = {'permalink': log}
                                            res = requests.get('https://dps.report/getJson', params=params)
                                            if res.status_code == 200:
                                                self.logs[type][e][b]['duration'].append(res.json().get('duration', 'UNKNOWN'))
                                            else:
                                                target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}({count}). `Error Code: DWAYNA`')
                                                self.logs[type][e][b]['duration'].append('ERROR')
                                                self.bot.clear_list.append(target)
                                        else:
                                            target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}({count}). `Error Code: GRENTH`')
                                            self.logs[type][e][b]['duration'].append('ERROR')
                                            self.bot.clear_list.append(target)
                                except ValueError:
                                    target = await ctx.send(f'ERROR :robot: : Could not decode JSON for {b}({count}). `Error Code: JSON`')
                                    self.bot.clear_list.append(target)
                        if error_multi_logs == len(latest_files):
                            error_logs += 1
                            continue
                    else:
                        with open(latest_file, 'rb') as file:
                            files = {'file': file}
                            res = requests.post(dps_endpoint, files=files)
                            if not res.status_code == 200:
                                target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: LYSSA`')
                                self.bot.clear_list.append(target)
                                error_logs += 1
                                continue
                            try:
                                json_data = res.json()
                                self.logs[type][e][b]['dps.report'] = json_data['permalink']
                                if self.show_time:
                                    if json_data['encounter']['jsonAvailable']:
                                        params = {'permalink': json_data['permalink']}
                                        res = requests.get('https://dps.report/getJson', params=params)
                                        if res.status_code == 200:
                                            self.logs[type][e][b]['duration'] = res.json().get('duration', 'UNKNOWN')
                                        else:
                                            target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: DWAYNA`')
                                            self.bot.clear_list.append(target)
                                    else:
                                        target = await ctx.send(f'ERROR :robot: : an error has occurred with {b}. `Error Code: GRENTH`')
                                        self.bot.clear_list.append(target)
                            except ValueError:
                                target = await ctx.send(f'ERROR :robot: : JSON INVALIDO {b}. `CODIGO DE ERROR: JSON`')
                                self.bot.clear_list.append(target)
                    print(f'Uploaded {b}: dps.report')

                if mode == 'GW2Raidar' or mode == 'Both':
                    print('Uploading {}: GW2Raidar...'.format(b))
                    if len(self.bot.owner_key) == 0:
                        target = await ctx.send('ERROR :robot: : Key not found. Please log into GW2Raidar before uploading.')
                        self.bot.clear_list.append(target)
                        return
                    raidar_endpoint = 'https://www.gw2raidar.com/api/v2/encounters/new'
                    with open(latest_file, 'rb') as file:
                        files = {'file': file}
                        res = requests.put(raidar_endpoint, headers={'Authorization': self.bot.owner_key}, files=files)
                        if not res.status_code == 200:
                            if res.status_code == 401:
                                target = await ctx.send('ERROR :robot: : an error has occurred with {}. `Error Code: RYTLOCK`'.format(b))
                                self.bot.clear_list.append(target)
                                error_logs += 1
                                continue
                            elif res.status_code == 400:
                                target = await ctx.send('ERROR :robot: : an error has occurred with {}. `Error Code: ZOJJA`'.format(b))
                                self.bot.clear_list.append(target)
                                error_logs += 1
                                continue
                            else:
                                target = await ctx.send('ERROR :robot: : an error has occurred with {}. `Error Code: SNAFF`'.format(b))
                                self.bot.clear_list.append(target)
                                error_logs += 1
                                continue
                        else:
                            self.logs[type][e][b]['GW2Raidar']['success'] = True
                    print('Uploaded {}: GW2Raidar'.format(b))
        
        if not error_logs == logs_length:
            print('------------------------------')
            if mode == 'GW2Raidar' or mode == 'Both':
                counter = 0
                await self.update_raidar(ctx, type, counter, logs_length, mode)
            await self.print_logs(ctx, type, ' '.join(title), mode)
        
    async def set_logs_order(self, ctx, type: str):
        temp_logs = copy.deepcopy(self.logs)
        #out = 'Type the `number` of the parser that you wish to upload to.\n```md\n1. dps.report\n2. GW2Raidar\n3. Both\n```'
        #try:
        #    message = await ctx.author.send(out)
        #except discord.Forbidden:
        #    target = await ctx.send('I do not have permission to DM you. Please enable this in the future.')
        #    self.bot.clear_list.append(target)
        #    return
        
        def m_check(m):
            return m.author == ctx.author and m.channel == message.channel
            
        #ans = await self.bot.wait_for('message', check=m_check)
        #await message.delete()
        #mode_num = ans.content
        
        #def switch(x):
        #    return {
        #        '1': 'dps.report',
        #        '2': 'GW2Raidar',
        #        '3': 'Both'
        #    }.get(x, 'Both')
            
        mode = 'dps.report'

        while True:
            logs_len = len(self.logs_order)
            out = 'Ingresa el `número` de la Wing/Escala que deseas subir'
            if logs_len == 0:
                out += ' o `0` para subir todos los bosses de todas las Wings/Escalas.\n'
            else:
                out += '.\n'
            out += 'Escribe `x` para confirmar tu seleccion.\n```md\n'
            if len(temp_logs[type]) == 0:
                break

            event = []
            for count, e in enumerate(temp_logs[type], 1):
                out += '{0}. {1}\n'.format(count, e)
                event.append(e)
            if logs_len == 0:
                out += '\n0. [Subir todos los bosses]'
            out += '\n[x]: [Confirmar orden de Wing/Fractal]\n```'
            message = await ctx.author.send(out)
                
            ans = await self.bot.wait_for('message', check=m_check)
            await message.delete()
            e_order = ans.content
            if e_order == 'x':
                break
            try:
                if int(e_order) == 0 and logs_len == 0:
                    self.logs_order = {e: [boss for boss in temp_logs[type][e]] for e in temp_logs[type]}
                    break

                e_pos = int(e_order) - 1
                if e_pos < 0 or e_pos >= len(event):
                    continue
                self.logs_order[event[e_pos]] = []
            except ValueError:
                continue
            
            while True:
                event_len = len(self.logs_order[event[e_pos]])
                out = 'Ingresa el `number` del boss que deseas subir'
                if event_len == 0:
                    out += ' o `0` para subir todos los bosses.\n'
                else:
                    out += '.\n'
                out += 'Escribe `x` para confirmar tu seleccion.\n```md\n'
                if len(temp_logs[type][event[e_pos]]) == 0:
                    break

                boss = []
                for count, b in enumerate(temp_logs[type][event[e_pos]], 1):
                    out += '{0}. {1}\n'.format(count, b)
                    boss.append(b)
                if event_len == 0:
                    out += '\n0. [Subir todos los bosses]'
                out += '\n[x]: [Confirmar orden de los bosses]\n```'
                message = await ctx.author.send(out)
                
                ans = await self.bot.wait_for('message', check=m_check)
                await message.delete()
                b_order = ans.content
                if b_order == 'x':
                    break
                try:
                    if int(b_order) == 0 and event_len == 0:
                        self.logs_order[event[e_pos]] = boss
                        break

                    b_pos = int(b_order) - 1
                    if b_pos < 0 or b_pos >= len(boss):
                        continue
                    self.logs_order[event[e_pos]].append(boss[b_pos])
                except ValueError:
                    continue
                
                del temp_logs[type][event[e_pos]][boss[b_pos]]            
            del temp_logs[type][event[e_pos]]
        del temp_logs

        print_order = 'Subiendo a {}...\n'.format(mode)
        for e in self.logs_order:
            if not len(self.logs_order[e]) == 0:
                print_order += '{0}: {1}\n'.format(e, self.logs_order[e])
        message = await ctx.author.send('Tu orden de logs seleccionado es:\n```{}\nClick ✅ para confirmar, ❌ para cancelar```'.format(print_order))
        await message.add_reaction('✅')
        await message.add_reaction('❌')
        
        def r_check(r, user):
            return user == ctx.author and r.count > 1
            
        ans, user = await self.bot.wait_for('reaction_add', check=r_check)
        if str(ans.emoji) == '❌':
            self.logs_order = {}
        await message.delete()
        
        return mode
        
    async def update_raidar(self, ctx, type: str, counter: int, length: int, mode: str):
        if length == 0:
            return
   
        if len(self.bot.owner_key) == 0:
            target = await ctx.send('ERROR :robot: : Key not found. Please log into GW2Raidar before uploading.')
            self.bot.clear_list.append(target)
            return
        raidar_endpoint = 'https://www.gw2raidar.com/api/v2/encounters?limit={}'.format(str(length))
        res = requests.get(raidar_endpoint, headers={'Authorization': self.bot.owner_key})
        if not res.status_code == 200:
            target = await ctx.send('ERROR :robot: : an error has occurred. `Error Code: CAITHE`')
            self.bot.clear_list.append(target)
            return
        else:   
            for e in self.logs_order:
                for b in self.logs_order[e]:
                    if not self.logs[type][e][b]['GW2Raidar']['success'] or not self.logs[type][e][b]['GW2Raidar']['link'] == 'about:blank':
                        continue
                    for encounter in res.json()['results']:
                        if self.logs[type][e][b]['filename'] in encounter['filename']:
                            raidar_link = 'https://www.gw2raidar.com/encounter/{}'.format(encounter['url_id'])
                            self.logs[type][e][b]['GW2Raidar']['link'] = raidar_link
                            if self.show_time and mode == 'GW2Raidar':
                                raidar_json = '{}.json'.format(raidar_link)
                                json_res = requests.get(raidar_json)
                                if not json_res.status_code == 200:
                                    target = await ctx.send('ERROR :robot: : an error has occurred with {}. `Error Code: LOGAN`'.format(b))
                                    self.bot.clear_list.append(target)
                                else:
                                    seconds = json_res.json()['encounter']['phases']['All']['duration']
                                    m, s = divmod(seconds, 60)
                                    duration = '%02d:%06.3f' % (m, s)
                                    self.logs[type][e][b]['duration'] = duration
                            break
                    if not self.logs[type][e][b]['GW2Raidar']['link'] == 'about:blank':
                        continue
                    elif counter == 6:
                        target = await ctx.send('ERROR :robot: : The logs were unsuccessfully analyzed within the time frame.')
                        self.bot.clear_list.append(target)
                        return
                    else:
                        print('The logs have not been analyzed. Retrying in 2.5 min: {}...'.format(str(counter)))
                        time.sleep(150)
                        counter += 1
                        return await self.update_raidar(ctx, type, counter, length, mode)
                    
    async def print_logs(self, ctx, type: str, name: str, mode: str):
        if len(name) > 0:
            title = '__{0} | {1}__'.format(name, str(datetime.date.today()))
        else:
            title = '__{}__'.format(str(datetime.date.today()))
        embed = discord.Embed(title=title, colour=0xb30000)
        embed.set_footer(text='Creado por Phantom#4985 | PhantomSoulz.2419. Mantenido por LeShock')
        embed.set_thumbnail(url='https://wiki.guildwars2.com/images/b/b5/Mystic_Coin.png')
        for e in self.logs[type]:
            out = ''
            name = '{}:'.format(e)
            no_link = 0
            for count, b in enumerate(self.logs[type][e]):
                if self.logs[type][e][b]['dps.report'] == 'about:blank' and self.logs[type][e][b]['GW2Raidar']['link'] == 'about:blank':
                    no_link += 1
                    continue
                boss = b
                
                boss_e = None
                for emoji in self.bot.emoji_list:
                    if emoji.name == b.replace(' ', '_'):
                        boss_e = emoji
                        break

                if mode == 'dps.report':
                    if self.num_logs > 0:
                        if not boss_e is None:
                            out += '{}  '.format(boss_e)
                        out += '**{}**  '.format(boss)
                        for count, log in enumerate(self.logs[type][e][b]['dps.report'], 1):
                            if self.show_time and 'duration' in self.logs[type][e][b] and not self.logs[type][e][b]['duration'][count-1] == 'ERROR':
                                out += '|  [{0}]({1})  '.format(self.logs[type][e][b]['duration'][count-1], log)
                            else:
                                out += '|  [Log {0}]({1})  '.format(count, log)
                        out += '\n'
                    else:
                        if not count == no_link and not self.show_time:
                            out += '  |  '
                        if not boss_e is None:
                            out += '{}  '.format(boss_e)
                        out += '**[{0}]({1})**'.format(boss, self.logs[type][e][b]['dps.report'])
                        if self.show_time and not 'duration' in self.logs[type][e][b]:
                            out += '\n'
                elif mode == 'GW2Raidar':
                    if not count == no_link and not self.show_time:
                        out += '  |  '
                    if not boss_e is None:
                        out += '{}  '.format(boss_e)
                    out += '**[{0}]({1})**'.format(boss, self.logs[type][e][b]['GW2Raidar']['link'])
                    if self.show_time and not 'duration' in self.logs[type][e][b]:
                        out += '\n'
                elif mode == 'Both':
                    if not boss_e is None:
                        out += '{}  '.format(boss_e)
                    out += '**{0}**  |  [dps.report]({1})  ·  [GW2Raidar]({2})'.format(boss, self.logs[type][e][b]['dps.report'], self.logs[type][e][b]['GW2Raidar']['link'])
                    if not self.show_time or not 'duration' in self.logs[type][e][b]:
                        out += '\n'
                if self.show_time and 'duration' in self.logs[type][e][b] and not isinstance(self.logs[type][e][b]['duration'], list):
                    out += '  |  **Duración**: {}\n'.format(self.logs[type][e][b]['duration'])
                
            if no_link == len(self.logs[type][e]):
                continue
            embed.add_field(name=name, value=out, inline=False)
            
        await ctx.send(embed=embed)
        
def setup(bot):
    bot.add_cog(Arcdps(bot))