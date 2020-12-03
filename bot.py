# net stop was /y
# Discord
import json
import os
import re
import discord
from discord.ext import commands

# OpenCV
import cv2
import pytesseract
import numpy as np
from urllib.request import Request, urlopen

# MySql
import mysql.connector

with open('db.config') as f:
  config = json.load(f)

mydb = mysql.connector.connect(
  host = config['host'],
  user = config['user'],
  password = config['password'],
  database = config['database']
)

try:
  mycursor = mydb.cursor()
  print('MySQL connected')
except:
  print('Cant connect to MySQL server')

## MAin Settings
GUILD_TAG = 'C`sL'
SCREEN_CHANNEL = "screeny-z-bossow"
DM_CHANNEL = 'DMChannel'

## PKT Settings
MINIBOSS_PKT = 10
BOSS_PKT = 15
MAP_T8_PKT = 15
RM_PKT = 15
OMNI_PKT = 20
SHRINE_PKT = 5

## Role Settings
OFICER_ROLE = 'Oficer'
VETERAN_ROLE = 'Veteran'
IT_SQUAD_ROLE = 'IT Squad'

## Bot settings
f = open('token')
TOKEN = f.read()
bot = commands.Bot(command_prefix='!')

################################
#           Utils              #
################################

## Process image
def get_charlist_from_img(url):
  req = Request(url, headers={
                'User-Agent': 'Mozilla/5.0'})
  resp = urlopen(req)

  image = np.asarray(bytearray(resp.read()), dtype="uint8")
  img = cv2.imdecode(image, cv2.IMREAD_COLOR)

  h, w, c = img.shape

  scale_percent = 200
  width = int(w * scale_percent / 100)
  height = int(h * scale_percent / 100)
  dim = (width, height)

  resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

  # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  custom_oem_psm_config = r'--oem 3 --psm 6'
  return pytesseract.image_to_string(resized, lang='uo', config=custom_oem_psm_config)

## Get all chars that contain C`sL tag in line
def get_guild_chars(text_array):
  guild_array = []
  for line in text_array:
    if line.lower().find(GUILD_TAG.lower()) >= 0:
        guild_array.append(line.replace('`', '\''))
  return guild_array

## Match characters to char list in MySQL db
def get_members_in_fight(chars_array):
  mycursor.execute("SELECT char_name, id, username FROM `characters` left join `users` on users.id = user_id where users.active = 1")
  myresult = mycursor.fetchall()

  member_in_fight = []
  for line in chars_array:
    for member in myresult:
      if line.find(member[0]) >= 0:
        member_in_fight.append(member[2])
  return member_in_fight

## Add point to users
def add_points_to_usrs(usr_array, pkt):
  for usr in usr_array:
    sql_update = "UPDATE users SET pkt = pkt + %s WHERE username = %s"
    mycursor.execute(sql_update, (pkt, usr))

  mydb.commit()

## Check user exist
def check_usr_exist(usr_name):
  sql = "SELECT username FROM users where username = %s"
  mycursor.execute(sql, (usr_name,))
  mycursor.fetchone()

  return not mycursor.rowcount <= 0

## Check similar username exist
def check_like_usr_exist(usr_name):
    sql = "SELECT username FROM users where username LIKE %s"
    mycursor.execute(sql, ("%"+usr_name+"%", ))
    return mycursor.fetchall()

## Check char exist
def check_char_exist(char_name):
  sql = "SELECT char_name FROM characters where char_name = %s"
  mycursor.execute(sql, (char_name, ))
  mycursor.fetchone()

  return not mycursor.rowcount <= 0

## Check user active
def check_usr_active(char_name):
  sql = "SELECT active FROM users where char_name = %s"
  mycursor.execute(sql, (char_name, ))
  myresult = mycursor.fetchone()

  return bool(myresult[0])

## Get Bosses
def get_bosses():
  sql = "SELECT boss_name, type, dungeon FROM bosses"
  mycursor.execute(sql)
  return mycursor.fetchall()

## Find boss in fight
def get_boss_from_fight(text_array):
  bosses = get_bosses()

  for line in text_array:
    for boss in bosses:
      if line.find(boss[0]) >= 0:
        return boss
  return None

## Get Points for Bosses depend on Type
def boss_pkt(btype):
  switch = {
    1: MINIBOSS_PKT,
    2: BOSS_PKT,
  }
  return switch.get(btype, "Wrong boss type")

## Get boss describion depend on Type
def boss_desc(btype):
  switch = {
    1: 'MINI',
    2: 'MAIN',
  }
  return switch.get(btype, "Wrong boss type")

## decorator - check when message is DM (direct message)
async def is_dm(ctx):
  return isinstance(ctx.message.channel, discord.channel.DMChannel)

## decorator - check when message is not DM (direct message)
async def is_not_dm(ctx):
  return not isinstance(ctx.message.channel, discord.channel.DMChannel)

## decorator - check whenever user post at right chanell
def is_right_channel(compare_channel):
  async def predicate(ctx):
    return not isinstance(ctx.message.channel, discord.channel.DMChannel) and ctx.message.channel.name == compare_channel
  return commands.check(predicate)

#################################
#         On Ready event        #
#################################
@bot.event
async def on_ready():
  print(f'{bot.user.name} has connected to Discord!')

#################################
#     Error Handling            #
#################################
@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    await ctx.send('Command not found')

#################################
#         Command: !boss        #
#################################
@commands.check(is_right_channel)
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@bot.command(name='boss')
async def get_picture(ctx):
    message = ctx.message
    if message.author == bot.user:
        return

    if len(message.attachments) < 1:
      await ctx.send('No attachments to message.')
      return

    split_text = get_charlist_from_img(message.attachments[0].url).splitlines()

    boss = get_boss_from_fight(split_text)
    if boss is None:
      await ctx.send(f'Can not find boss from screen!')
      return

    pkt = boss_pkt(boss[1])
    boss_type = boss_desc(boss[1])

    guild_array = get_guild_chars(split_text)
    member_in_fight = get_members_in_fight(guild_array)
    if len(member_in_fight) <= 0:
      await ctx.send(f'No users from C`sL')
      return

    add_points_to_usrs(member_in_fight, MINIBOSS_PKT)

    await ctx.send(f'Boss `{boss[0]} [{boss[2]} {boss_type}]` result:```\n' + '\n'.join(str(member) for member in member_in_fight) +f'```\nAdded `{pkt}` pkt to users.')


#################################
#        Command: !shrine       #
#################################
@bot.command(name='shrine')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_picture(ctx):
    message = ctx.message
    if message.author == bot.user:
        return

    if len(message.attachments) < 1:
      await ctx.send('No attachments to message.')
      return

    split_text = get_charlist_from_img(message.attachments[0].url).splitlines()

    boss = get_boss_from_fight(split_text)
    if boss is not None:
      await ctx.send(f'Wrong screenshot - found Boss `[{boss[0]} from {boss[2]}]`. Use command `!boss`')
      return

    guild_array = get_guild_chars(split_text)
    member_in_fight = get_members_in_fight(guild_array)
    if len(member_in_fight) <= 0:
      await ctx.send(f'No users from C`sL')
      return

    add_points_to_usrs(member_in_fight, SHRINE_PKT)

    await ctx.send(f'Shrine result:```\n' + '\n'.join(str(member) for member in member_in_fight) +f'```\nAdded `{SHRINE_PKT}` pkt to users.')


#################################
#         Command: !mapT8        #
#################################
@bot.command(name='mapT8')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_picture(ctx, *args):
    message = ctx.message
    if message.author == bot.user:
        return

    multi = 1
    if len(args) == 1:
      atr = re.findall(r'\d+', args[0])
      if len(atr) > 0:
        multi = int(atr[0])

    if len(message.attachments) < 1:
      await ctx.send('No attachments to message.')
      return

    split_text = get_charlist_from_img(message.attachments[0].url).splitlines()

    boss = get_boss_from_fight(split_text)
    if boss is not None:
      await ctx.send(f'Wrong screenshot - found Boss `[{boss[0]} from {boss[2]}]`. Use command `!boss`')
      return

    member_in_fight = get_members_in_fight(split_text)
    if len(member_in_fight) < 1:
      await ctx.send('Cant find active members in picture that you attach.')
      return

    add_points_to_usrs(member_in_fight, multi * MAP_T8_PKT)

    await ctx.send(f'T8 Map x{multi} result:```\n' + '\n'.join(str(member) for member in member_in_fight) +f'```\nAdded `{multi * MAP_T8_PKT}` pkt to users.')

#################################
#         Command: !pkt         #
#################################
@bot.command(name='pkt')
#@commands.check(is_dm)
@is_right_channel(SCREEN_CHANNEL)
async def get_pkt(ctx, *args):
    if len(args) != 1:
      await ctx.channel.send("Wrong usage of command: [!pkt usr_name]")
      return

    usr_name = args[0]

    users = check_like_usr_exist(usr_name)
    if len(users) <= 0:
      await ctx.send(f'Can find user `{usr_name}`')
      return
    if len(users) > 1:
      await ctx.send(f'To many results for user `{usr_name}`')
      return


    mycursor.execute("SELECT pkt from users where username LIKE %s",
                     ("%"+usr_name+"%", ))

    myresult = mycursor.fetchall()
    await ctx.send('Liczba punktow dla uzytkownika `{}`: {} pkt'.format(users[0][0], myresult[0][0]))

###############################
#     Command: !roleTest      #
###############################
@bot.command(name='roleTest')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def role_test(ctx):
  await ctx.send('Mozesz uzyc')

###############################
#     Command: !spendPkt      #
###############################
@bot.command(name='spendPkt')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_pkt(ctx, *args):
    if len(args) != 2:
      await ctx.channel.send("Wrong usage of command: [!spendPkt usr_name pkt]")
      return

    usr_name = args[0]
    pkt = int(args[1])

    if pkt <= 0:
      await ctx.channel.send('Wrong pkt number (should be greater then zero)')
      return

    if not check_usr_exist(usr_name):
      await ctx.send('No user with name `{}`'.format(usr_name))
      return

    sql = "SELECT pkt from users where username = %s"
    mycursor.execute(sql, (usr_name, ))
    myresult = mycursor.fetchone()

    if myresult[0] < int(pkt):
      await ctx.send('Uzytkownik {} nie ma wystarczajacej liczy punktow [{} pkt]. Aktualnie posiada : {} pkt'.format(usr_name, pkt, str(myresult[0])))
      return

    sql = "UPDATE users SET pkt = pkt - %s where username = %s"
    mycursor.execute(sql, (pkt, usr_name))

    mydb.commit()

    await ctx.send('Pobrano punkty od uzytkownika {}: [{} pkt]. Aktualny stan punktow dla uztkownika to : {} pkt'.format(usr_name, pkt ,str(myresult[0] - pkt)))

###############################
#      Command: !addPkt       #
###############################
@bot.command(name='addPkt')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_pkt(ctx, *args):
    if len(args) != 2:
      await ctx.channel.send("Wrong usage of command: [!addPkt usr_name pkt]")
      return

    usr_name = args[0]
    pkt = int(args[1])

    if pkt <= 0:
      await ctx.send('Wrong pkt numer (should be greater then zero)')
      return

    if not check_usr_exist(usr_name):
      await ctx.send('Brak uzytkownika o nazwie {}'.format(usr_name))
      return

    sql = "UPDATE users SET pkt = pkt + %s where username = %s"
    mycursor.execute(sql, (pkt, usr_name))

    mydb.commit()

    await ctx.send(f'Dodatno punkty do uzytkownika `{usr_name}: [{str(pkt)} pkt]`')

###############################
#      Command: !addRM        #
###############################
@bot.command(name='addRM')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_pkt(ctx, *args):
    if len(args) != 2:
      await ctx.channel.send("Wrong usage of command: [!addRM usr_name cnt]")
      return

    usr_name = args[0]
    arg = re.findall(r'\d+', args[1])

    if len(arg) <= 0:
      await ctx.send('Wrong attribute numer (should be greater then zero)')
      return

    cnt = arg[0]
    pkt = int(cnt) * RM_PKT

    if not check_usr_exist(usr_name):
      await ctx.send('Brak uzytkownika o nazwie {}'.format(usr_name))
      return

    sql = "UPDATE users SET pkt = pkt + %s where username = %s"
    mycursor.execute(sql, (pkt, usr_name))

    mydb.commit()

    await ctx.send(f'Dodatno punkty do uzytkownika `{usr_name}: [{pkt} pkt]` za x{cnt} RM')

###############################
#     Command: !clearPkt      #
###############################
@bot.command(name='clearPkt')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_pkt(ctx, *args):
    if len(args) != 1:
      await ctx.channel.send("Wrong usage of command: [!clearPkt usr_name]")
      return

    usr_name = args[0]

    if not check_usr_exist(usr_name):
      await ctx.send(f'Brak uzytkownika o nazwie `{usr_name}`')
      return

    sql = "UPDATE users SET pkt = 0 where username = %s"
    mycursor.execute(sql, (usr_name, ))

    mydb.commit()

    await ctx.send(f'Wyzerowano punkty dla uzytkownika `{usr_name}`')

################################
#        Command: !table       #
################################
@bot.command(name='table')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def get_table(ctx):
  sql = "SELECT username, pkt from users where active = 1"
  mycursor.execute(sql)
  myresult = mycursor.fetchall()
  sorted_list = sorted(myresult, key = lambda usr: usr[1], reverse=True)

  txt = ''
  for key in sorted_list:
    txt += key[0] + ': [' + str(key[1]) +' pkt]\n'

  await ctx.send(f'Tabela punktow: ```{txt}```')

#################################
#         Command: !who         #
#################################
@bot.command(name='who')
#@bot.check(is_dm)
@is_right_channel(SCREEN_CHANNEL)
async def get_usr(ctx, *args):
    if len(args) != 1:
      await ctx.send("Wrong usage of command: [!who char_name]")
      return

    char_name = args[0]
    mycursor.execute("SELECT username FROM `characters` left join `users` on users.id = user_id WHERE char_name = %s",
                     (char_name, ))
    myresult = mycursor.fetchall()

    if len(myresult) == 0:
      await ctx.send(f"No users with character {char_name}")
      return
      
    await ctx.send(f"Character {char_name} belong to `{myresult[0][0]}`")


#################################
#         Command: !chars       #
#################################
@bot.command(name='chars')
#@bot.check(is_dm)
@is_right_channel(SCREEN_CHANNEL)
async def get_chars(ctx, *args):
    if len(args) != 1:
        await ctx.channel.send("Wrong usage of command: [!chars usr_name]")
        return

    char_name = args[0]
    usrs = check_like_usr_exist(char_name)
    if len(usrs) > 1:
      await ctx.send(f'To many results for username `{char_name}`')
      return
    if len(usrs) <= 0:
      await ctx.send(f'Can not find username `{char_name}`')
      return

    sql = "SELECT username, char_name FROM `users` INNER join `characters` on `users`.`id` = `characters`.`user_id` where users.username LIKE %s"
    mycursor.execute(sql, ("%"+char_name+"%", ))
    myresult = mycursor.fetchall()
    if len(myresult) == 0:
      await ctx.send(f'Brak postaci dla uzytkownika {char_name}')
      return

    await ctx.send(f'Postacie dla uzytkownika {myresult[0][0]}:```\n' + '\n'.join(str(x[1]) for x in myresult) + '```')

#################################
#        Command: !addChar      #
#################################
@bot.command(name='addChar')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def add_char(ctx, *args):
    if len(args) < 2:
        await ctx.channel.send("Wrong usage of command: [!addChar usr_name char_name ...  char_name]")
        return

    chars_list = args[1:]
    usr_name = args[0]

    sql_user_id = "SELECT id FROM `users` where users.username = %s"
    mycursor.execute(sql_user_id, (usr_name, ))
    usr_id = mycursor.fetchone()
    if usr_id is None:
      await ctx.send(f'Brak uzytkownika o nazwie `{usr_name}`')
      return

    for char_name in chars_list:
      sql_insert = "INSERT INTO characters (user_id, char_name) VALUES (%s, %s)"
      mycursor.execute(sql_insert, (usr_id[0], char_name))

    mydb.commit()

    await ctx.send(f'Added for user {args[0]}:```\n' + '\n'.join(str(char) for char in chars_list) + '```')

#################################
#        Command: !removeChar   #
#################################
@bot.command(name='removeChar')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def remove_char(ctx, *args):
  if len(args) != 2:
    await ctx.send("Wrong usage of command: [!removeChar usr_name char_name]")
    return

  char_name = args[1]
  usr_name = args[0]

  # Fetch user_id

  sql_user_id = "SELECT id FROM `users` where users.username = %s"
  mycursor.execute(sql_user_id, (usr_name, ))
  usr_id = mycursor.fetchone()

  if usr_id is None:
    await ctx.send(f'No user `{usr_name}`')
    return

  sql_insert = "DELETE FROM characters WHERE user_id = %s AND char_name = %s"
  mycursor.execute(sql_insert, (usr_id[0], char_name))

  mydb.commit()

  await ctx.send(f'Removed `{char_name}` from `{usr_name}`')

################################
#     Command: !renameChar     #
################################
@bot.command(name='renameChar')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def rename_char(ctx, *args):
  if len(args[0]) == 0 or len(args[1]) == 0:
    await ctx.send("Wrong usage of command: !renameChar old_name new_name")
    return

  old_name = args[0].strip()
  new_name = args[1].strip()

  if not check_char_exist(old_name):
    await ctx.send(f'Character {old_name} dose not exist')
    return

  if check_char_exist(new_name):
    await ctx.send(f'Character {new_name} already exist')
    return

  sql_update = "UPDATE characters SET char_name = %s WHERE char_name = %s"

  mycursor.execute(sql_update, (new_name, old_name))

  mydb.commit()

  await ctx.send(f'Rename character [{old_name} => {new_name}]')

#################################
#        Command: !addUsr       #
#################################
@bot.command(name='addUsr')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def add_usr(ctx, *args):
  if len(args) == 0:
      await ctx.send("Wrong usage of command:")
      return

  usr_name = args[0]

  if check_usr_exist(usr_name):
    await ctx.send(f'User `{usr_name}` already exist')
    return

  sql_insert = "INSERT INTO users (username, active, pkt) VALUES (%s, %s, %s)"
  mycursor.execute(sql_insert, (usr_name, 1, 0))

  mydb.commit()

  await ctx.send(f'Added user: {usr_name}')

################################
#     Command: !removeUsr      #
################################
@bot.command(name='removeUsr')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def remove_usr(ctx, *args):
  if len(args[0]) == 0:
    await ctx.send("Wrong usage of command: !removeUsr usr_name")
    return

  usr_name = args[0]

  sql_user_id = "SELECT id FROM `users` where users.username = %s"
  mycursor.execute(sql_user_id, (usr_name, ))
  usr_id = mycursor.fetchone()

  if usr_id is None:
    await ctx.send(f'Brak uzytkownika o nazwie {usr_name}')
    return

  sql_del = "UPDATE users SET active = 0 WHERE id = %s"
  mycursor.execute(sql_del, (usr_id))

  mydb.commit()

  await ctx.send(f'Deactivate user `{usr_name}`. To pernament remove user use `!pernamentRemoveUsr [usr_name]`')

################################
#     Command: !renameUsr     #
################################
@bot.command(name='renameUsr')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def rename_usr(ctx, *args):
  if len(args[0]) == 0 or len(args[1]) == 0:
    await ctx.send("Wrong usage of command: !renameUsr old_name new_name")
    return

  old_name = args[0].strip()
  new_name = args[1].strip()

  if not check_usr_exist(old_name):
    await ctx.send(f'User `{old_name}` dose not exist')
    return

  if check_usr_exist(new_name):
    await ctx.send(f'User `{new_name}` already exist')
    return

  sql_update = "UPDATE users SET username = %s WHERE username = %s"

  mycursor.execute(sql_update, (new_name, old_name))

  mydb.commit()

  await ctx.send(f'Rename user [{old_name} => {new_name}]')

################################
#    Command: !activateUsr     #
################################
@bot.command(name='activateUsr')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE,
  VETERAN_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def remove_usr(ctx, *args):
  if len(args[0]) == 0:
    await ctx.send("Wrong usage of command: !activateUsr usr_name")
    return

  usr_name = args[0]

  sql_user_id = "SELECT id FROM `users` where users.username = %s"
  mycursor.execute(sql_user_id, (usr_name, ))
  usr_id = mycursor.fetchone()

  if usr_id is None:
    await ctx.send(f'Brak uzytkownika o nazwie {usr_name}')
    return

  sql_del = "UPDATE users SET active = 1 WHERE id = %s"
  mycursor.execute(sql_del, (usr_id))

  mydb.commit()

  await ctx.send(f'Activate user `{usr_name}`')

################################
# Command: !pernamentRemoveUsr #
################################
@bot.command(name='pernamentRemoveUsr')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def remove_usr(ctx, *args):
  if len(args[0]) == 0:
    await ctx.send("Wrong usage of command: !pernamentRemoveUsr usr_name")
    return

  usr_name = args[0]

  sql_user_id = "SELECT id FROM users where users.username = %s"
  mycursor.execute(sql_user_id, (usr_name, ))
  usr_id = mycursor.fetchone()

  if usr_id is None:
    await ctx.send(f'Brak uzytkownika o nazwie {usr_name}')
    return

  sql_del = "DELETE FROM characters WHERE user_id = %s"
  mycursor.execute(sql_del, (usr_id))

  sql_del = "DELETE FROM users WHERE id = %s"
  mycursor.execute(sql_del, (usr_id))

  mydb.commit()

  await ctx.send(f'Pernament remove user `{usr_name}` and all characters.')

################################
# Command: !users #
################################
@bot.command(name='users')
@commands.has_any_role(
  OFICER_ROLE,
  IT_SQUAD_ROLE
)
@is_right_channel(SCREEN_CHANNEL)
async def users_list(ctx):
  sql = "SELECT username, active, pkt FROM users"
  mycursor.execute(sql)

  results = mycursor.fetchall()

  txt = ''
  for key in results:
    txt += key[0] + ': [' + str(key[2]) +' pkt] Active: '+ str(bool(key[1])) + '\n'

  await ctx.send(f'Users list: ```{txt}```')

bot.run(TOKEN)
