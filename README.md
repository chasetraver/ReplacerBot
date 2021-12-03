# ReplacerBot
Discord Bot to discourage use of restricted words via a social points system, and offer random words chosen daily.

runs using Python 3.9 and using the discord python API
will require the creation of a replacers.py file for the user to create their own curated list of restricted words.
User will also require their own discord bot API key, as well as an account with the Oxford API to be able to use their service, if you want to use the bot's definitions function.
The bot will also require your server's channelid and authorization ID to post to. You can see how to get that here: https://youtu.be/xh28F6f-Cds?t=99

pointroles in check_points_roles should also be modified to the names of roles in your server you want to be assigned based on people's standing with the bot.
