from os import environ, path
import discord
from discord.utils import get
import requests
import datetime
from datetime import timedelta
import json
import asyncio
import random
from sylcount import sylco
from replacers import nothingisms
from nltk.stem import WordNetLemmatizer

token = environ.get('DISCORDBOTKEY')
channelid = int(environ.get('DISCORDBOTCHANNELID'))
auth = environ.get('DISCORDBOTAUTH')
app_key = environ.get('OXFORDAPIKEY')
app_id = environ.get('OXFORDAPIID')

client = discord.Client()
goodword = "good"
badword = "bad"


async def make_new_words():
    global goodword
    global badword
    goodword = await get_word()
    badword = await get_word()
    today = datetime.date.today()
    message = f":sun_with_face: @here New Gamerwords for {today} :sun_with_face:\nPositive word of the day: \t :ok_hand: " \
              f"{goodword} :100: \n\nNegative word of the day: \t\t:face_with_symbols_over_mouth: {badword} :smiling_imp:"
    return message


async def get_word():
    while True:
        r = requests.get('https://random-word-api.herokuapp.com/word?number=1&swear=0')
        if r.status_code >= 400:
            print(r.status_code)
            return "something went wrong."
        word = json.loads(r.text)[0]
        if sylco(word) <= 2:
            return word
        print(word)


async def corrective_message(message):
    for word in nothingisms:
        message = await replacer(message, word)
    return message


async def replacer(message, word):
    randomizer = random.randint(1, 2)
    if randomizer == 1:
        replace_word = goodword
    else:
        replace_word = badword
    return message.replace(word, replace_word)


async def get_old_words():
    global goodword
    global badword
    headers = {
        # how to get authorization token here: https://youtu.be/xh28F6f-Cds?t=99
        'authorization': auth
    }
    old_words_message = requests.get(f'https://discord.com/api/v8/channels/{channelid}/messages?limit=1',
                                     headers=headers)
    old_words_message = json.loads(old_words_message.text)[0]['content']
    old_message_list = old_words_message.split()
    goodword = old_message_list[13]
    badword = old_message_list[21]


async def help_message(message):
    await message.channel.send(":exclamation:``!help`` generates list of commands Gamerwords bot uses (you are here)\n"
                               ":confetti_ball:``!points`` shows you how many Gamerpoints you have (you get points "
                               "from using the daily words, and lose points from using nothingisms.)\n"
                               ":no_entry_sign:``!nothingisms`` shows list of nothingisms.\n"
                               ":sunglasses:``!gamerwords`` shows the words of the day, as well "
                               "as where you can find them regularly.\n"
                               ":trophy: ``!leaderboard`` see who's :ok_hand: at defeating nothingisms.\n"
                               ":books: ``!definitions`` to see what those gamerwords mean when they're not being "
                               "better nothingisms."
                               "")
    pass


async def get_definitions():
    message = ""
    for word in (goodword, badword):
        get_word_def = await dictionary_request(word)
        if get_word_def.status_code >= 400:
            if get_word_def.status_code == 404:
                # gets 'root' word from the word of the day
                lemmatizer = WordNetLemmatizer()
                rootword = lemmatizer.lemmatize(word)
                print(rootword)
                # retries with 'root' word
                get_word_def = await dictionary_request(rootword)
                if get_word_def.status_code >= 300:
                    if get_word_def.status_code == 404:
                        message = message + f"Definition for {word} was not found.\n\n"
                        continue
                    else:
                        message = message + f"Could not get definition for {word}.\n\n"
                        print(f"something went wrong getting the {word} definition.")
                        print(get_word_def.status_code)
                        continue
            else:
                message = message + f"Could not get definition for {word}.\n\n"
                print(f"something went wrong getting the {word} definition.")
                print(get_word_def.status_code)
                continue

        word_def = json.loads(get_word_def.text)
        defcount = 1
        message = message + f"{word}:\n"
        try:
            for result in word_def['results']:
                for lexicalentries in result['lexicalEntries']:
                    for entries in lexicalentries['entries']:
                        for senses in entries['senses']:
                            for definition in senses['definitions']:
                                message = message + f"{defcount}. {definition}\n"
                                defcount = defcount + 1
        except KeyError:
            message = message + "Error with dictionary. Definition could not be found."
            print(word + " had key error.")
        message = message + '\n'
    return message


async def dictionary_request(word):
    url = f"https://od-api.oxforddictionaries.com/api/v2/entries/en-us/{word}?fields=definitions&strictMatch=false"
    return requests.get(url, headers={"Accept": "application/json", "app_id": app_id, "app_key": app_key})


async def leaderboard(message):
    leaders = await get_leaders()
    if len(leaders) > 10:
        del leaders[10:len(leaders)]

    leader_message = f":confetti_ball:\t:100:\t:trophy: LEADERBOARD :trophy:\t:100:\t:confetti_ball:\n"
    for count, leader in enumerate(leaders, start=1):
        leader_message = leader_message + f"\t{count}. {await client.fetch_user(leader[0])} with {leader[1]} points.\n"
    await message.channel.send(leader_message)


async def get_leaders():
    members = []
    data = get_points_data()
    for member in data:
        members.append((member, data[member]['points']))
    pointsort = lambda user: user[1]
    members.sort(key=pointsort, reverse=True)
    return members


async def points_check(author):
    data = get_points_data()
    if author in data:
        points = data[author]['points']
    else:
        points = 0
    return points


def modify_points(message, point_id, pointsmod):
    # message is not used at this time, see TODO below
    max_points_per_hour = 5

    data = get_points_data()
    # check if user exists
    if point_id in data:

        # penalties are in hours based on
        spampenalty = (1, 1, 3, 5, 8, 12, 24, 72, 168)
        spamtier = data[point_id]['spamtier']
        # check for point spam
        last_modified = datetime.datetime.strptime(data[point_id]['lastmodified'], '%Y-%m-%d %H:%M:%S.%f')
        if pointsmod > 0:
            if last_modified + timedelta(hours=spampenalty[spamtier]) > datetime.datetime.now():
                if data[point_id]['timesmodified'] > max_points_per_hour:
                    # TODO message 'hey dont spam' (can't use async function in sync function)
                    if data[point_id]['spamtier'] < 8:
                        data[point_id]['spamtier'] = data[point_id]['spamtier'] + 1

        if spamtier == 0 or pointsmod < 0:
            # give points if not spamming
            data[point_id]['points'] += pointsmod
        points = data[point_id]['points']

        # set anti-spam 'timer'
        if pointsmod > 0:
            data[point_id]['lastmodified'] = datetime.datetime.now()
            if last_modified + timedelta(hours=spampenalty[spamtier]) > datetime.datetime.now():
                data[point_id]['timesmodified'] += 1
            else:
                data[point_id]['timesmodified'] = 0
                data[point_id]['spamtier'] = 0

    else:
        # make new user
        data[point_id] = {'points': 0 + pointsmod, 'timesmodified': 0, 'lastmodified': f'{datetime.datetime.now()}',
                          'spamtier': 0}
        points = data[point_id]['points']

    with open('points', 'w') as outfile:
        # prevents crashing from trying to turn datetime into JSON
        data[point_id]['lastmodified'] = str(data[point_id]['lastmodified'])
        json.dump(data, outfile)
        outfile.close()

    return points


def get_points_data():
    with open('points', 'r') as infile:
        data = json.load(infile)
        infile.close()
    return data


async def check_points_roles(author, points):
    # TODO make this run as a wrapper for modify points
    pointroles = ['👑FrankPledges', '🙏Kotow', '😏Ska', '😴pogchump', '🦜Twitch Parrot', '🙉Pogchimp']

    # role modification
    if points >= 100000:
        await add_role(author, pointroles[0], pointroles)
    elif points >= 10000:
        await add_role(author,  pointroles[1], pointroles)
    elif points >= 1000:
        await add_role(author,  pointroles[2], pointroles)
    elif points < 0:
        await add_role(author,  pointroles[3], pointroles)
    elif points <= -10000:
        await add_role(author,  pointroles[4], pointroles)
    elif points <= -100000:
        await add_role(author,  pointroles[5], pointroles)


async def add_role(member, role, roles):
    roles.remove(role)
    role = get(member.guild.roles, name=role)
    await member.add_roles(role)
    await remove_roles(member, roles)


async def remove_roles(member, roles):
    for role in roles:
        remove_me = get(member.guild.roles, name=role)
        await member.remove_roles(remove_me)


def isSpamming(point_id):
    # here because I cannot await message in modify_points
    point_id = str(point_id)
    data = get_points_data()
    spamtier = data[point_id]['spamtier']
    return spamtier


# bot events
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    channel = client.get_channel(id=channelid)
    await get_old_words()
    while True:
        # if datetime.datetime.now().today().weekday() == 0:
            if datetime.datetime.now().hour == 11:
                gamerwords = await make_new_words()
                await channel.send(gamerwords)
                print(f"sent gamerwords out at {datetime.datetime.now()}")
            await asyncio.sleep(3600)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message):
        await message.channel.send("Hello! I'm the Gamerwords bot. I help people replace 'nothingisms' with new "
                                   "daily words that contribbute to conversations equally!"
                                   "\n Type ``!help`` for my commands! ")
        return

    if len(message.content) > 0:
        # ! commands
        # TODO change command operator to variable settable by user and stored in file
        if message.content[0] == "!":
            if message.content.lower() == "!nothingisms":
                await message.channel.send(nothingisms)
                return

            if message.content.lower() == '!help':
                await help_message(message)
                return

            if message.content.lower() == '!gamerwords':
                channel = client.get_channel(id=channelid)
                await message.channel.send(f"Today's good word is {goodword}.\nToday's bad word is {badword}."
                                           f" \n New words posted daily in {channel.mention}!")
                return

            if message.content.lower() == '!definitions':
                definitions = await get_definitions()
                await message.channel.send(definitions)
                return

            if message.content.lower() == '!points':
                points = await points_check(str(message.author.id))
                if points >= 0:
                    await message.channel.send(f":confetti_ball: {message.author.mention}, you have {points} points! :confetti_ball:")
                else:
                    await message.channel.send(f"Uh, {message.author.mention}, you have {points} points... :grimacing:")
                return

            if message.content.lower() == '!leaderboard':
                await leaderboard(message)
                return

        # corrective message
        in_message = message.content.lower()
        for word in nothingisms:
            if word in in_message:
                await message.add_reaction('\N{THUMBS DOWN SIGN}')
                await message.channel.send(
                    f" Hey {message.author.mention}, did you mean, '{await corrective_message(in_message)}'?")
                points = modify_points(message, str(message.author.id), -100)
                await check_points_roles(message.author, points)
                return
        if goodword in in_message or badword in in_message:
            points = modify_points(message, str(message.author.id), 100)
            spamtier = isSpamming(message.author.id)
            if spamtier > 0:
                await message.add_reaction('\N{THUMBS DOWN SIGN}')
                await message.channel.send(
                    f" Hey {message.author.mention}, can you not spam? That's not very {goodword} of you. "
                    f"You're being placed in spamtier {spamtier}.")
                points = modify_points(message, str(message.author.id), -100 * spamtier)
            else:
                await message.add_reaction('\N{THUMBS UP SIGN}')
            await check_points_roles(message.author, points)
            return

if __name__ == '__main__':
    client.run(token)
