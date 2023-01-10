# AnoxBot

Mastodon bot posting quotes from Anachronox. The script to post quotes is quite simple, see `anoxbot.py`. The actual complexity is in creating the quote database.

This script is repsonsible for the quotes posted at https://botsin.space/@anachronox

## Generating the quote database

The quotes are extracted from decompiled APE (Anachronox Programming Language) files. 

To get the decompiled APE files you must first extract the APE files from the `gameflow.dat` file, follewed by extracting the newer APE files from the `anox1.zip` in the game data directory, and finally followed by the newer APE files in the game data's subdirectory `gameflow`.

Extracting the DAT files can be done with the DATExtract tool available on: https://anachrodox.talonbrave.info/

Decompiling the APE files is done with the modding tools on: https://code.google.com/archive/p/anachronox-modding/source/default/source

To create the quote database run the `extract-quotes.py` with the files you process. 

The `extract-quotes.py` script partially parses the APE source files to construct dialogs as they could appear in the game. Many of the dialogs have variable conditions, the script takes a best effort to take these into account. Luckily the developers did not create too complex and overlapping conditions in the dialog. And various variable substitutions could be fixed with a simple lookup table.

### Subtitle

The `extract-quotes.py` script makes a distinciton between plain quotes, and subtitles. The latter are the subtitles in cinematics and are often fragments of a dialog.

The subtitle quotes are stored in a separate table for further processing. Which is not finished yet.
