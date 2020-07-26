# majavah-bot

This repository contains the code for [User:MajavahBot](https://en.wikipedia.org/wiki/User:MajavahBot), which operates
on many Wikimedia wikis, including the [English](https://en.wikipedia.org/wiki/User:MajavahBot),
[Finnish](https://fi.wikipedia.org/wiki/Käyttäjä:MajavahBot) and the
[Wikimedia Meta-Wiki](https://meta.wikimedia.org/wiki/User:MajavahBot). Its bugs are tracked on the
[Wikimedia Phabricator](https://phabricator.wikimedia.org/tag/tool-majavahbot/). The bot is hosted on
[Wikimedia Toolforge](https://toolforge.org).

## Architecture

The source code lives on `majavahbot/`. It is divided on three parts:

* `majavahbot/api/` contains a framework that the rest of the bot uses.
* `majavahbot/tasks/` contains the individual tasks that the bot can run.
* `majavahbot/web/` contains code for the [web interface](https://majavah-bot.toolforge.org)

There is also `cli.py`, which handles the command-line interface for running the bot and
`app.py` which starts the web interface.

## LICENSE

majavah-bot is free software licensed under the MIT license. See LICENSE for more details.