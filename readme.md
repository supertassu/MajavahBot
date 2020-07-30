# majavah-bot

This repository contains the code for [User:MajavahBot](https://en.wikipedia.org/wiki/User:MajavahBot), which operates
on many Wikimedia wikis, including the [English](https://en.wikipedia.org/wiki/User:MajavahBot),
[Finnish](https://fi.wikipedia.org/wiki/Käyttäjä:MajavahBot) Wikipedias and the
[Wikimedia Meta-Wiki](https://meta.wikimedia.org/wiki/User:MajavahBot). Its bugs are tracked on the
[Wikimedia Phabricator](https://phabricator.wikimedia.org/tag/tool-majavahbot/). The bot is hosted on
[Wikimedia Toolforge](https://toolforge.org).

## Running the bot

### Installing

The bot uses Python 3. It is currently running 3.5 in production. Clone this repository and create a virtual environment. Use pip to install dependencies from `requirements.txt`.

### Configuring

The bot has a configuration file `majavahbot/config.py` and a sample one at `majavahbot/config.example.py`.
To get started, copy the sample file over and modify any values that need modifying. It contains two types of values:

* Database credentials, for a local database to store own data and
  for a [Wiki replicas](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database) connection.
  This includes a hostname and a port to connect (for replicas use `{DB}` to properly connect to the right database)
  and the path to a configuration file containing a username and a password
  (sample format is provided at `local.my.cnf` and Toolforge has this directly provided to you).
* Page names for on-wiki configuration files. See
  https://en.wikipedia.org/wiki/User:MajavahBot/EFFP_Helper_Configuration for an example.

### The CLI

The `cli.py` file can be used to run the bot. Use `python cli.py --help` to retrieve a list of all subcommands
and `python cli.py {subcommand} --help` to get help related to that specific subcommand.

You might need to do some database fiddling directly to modify approval/trial status of a task.

## Architecture

The source code lives on `majavahbot/`. It is divided on three parts:

* `majavahbot/api/` contains a framework that the rest of the bot uses.
* `majavahbot/tasks/` contains the individual tasks that the bot can run.
* `majavahbot/web/` contains code for the [web interface](https://majavah-bot.toolforge.org)

There is also `cli.py`, which handles the command-line interface for running the bot and
`app.py` which starts the web interface.

## LICENSE

majavah-bot is free software licensed under the MIT license. See LICENSE for more details.