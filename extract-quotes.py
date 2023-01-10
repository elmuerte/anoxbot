#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2023 Michiel Hendriks
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# https://anachrodox.talonbrave.info/ape/apecmds.html

import sys, pathlib, re, textwrap, sqlite3

#TODO:
# #window 64:413 -- body after condition

# These ids are not really part of the game?
excludeids = [
	#ballotine.ape
	"83:9000",
	#commbase.ape
	"97:9",
	#crevice.ape
	"94:171",
	"94:172",
	"94:173",
	"94:174",
	#grumpos.ape
	"14:4202",
	#hephtower1.ape
	"72:2001",
	"72:2002",
	"72:2003",
	"72:2004",
	"72:2005",
	"72:2006",
	"72:2007",
	"72:2008",
	"72:2009",
	"72:2010",
	#labbuilding.ape
	"60:401",
	"60:405",
	"60:410",
	"60:415",
	#onegatestn.ape
	"108:8888",
	"108:8889",
	"108:8890",
	#vendomart.ape
	"41:1515",
	#whitecaves-b.ape
	"107:101",
	#bugaboo.ape
	"50000:8600",
	#global22.ape -- ignore completely
	#global98.ape -- ignore completely
	#global99.ape -- ignore completely
	#hephaestus.ape
	"71:6000",
	"71:6100",
	"7400:1",
	#levant2.ape
	"74:600",
	#ox.ape
	"50000:5",
	#pooper.ape
	"50000:51",
	#waukees.ape
	"86:50",
	#whacks.ape
	"12:150"
]

# Name substitutions used in certain texts
substs = {}
#substs["playerchar0$"] # Current "active" player character. i.e.: func_charinparty[X] == 3
substs["whitendon_name$"] = "Guillermo"
substs["@kj_1"] = "13" # This is a random number
substs["@kj_2"] = "42" # This is a random number
substs["money_for_dance"] = "69"
substs["@gold_suite"] = "144"
substs["whacks_firstshot"] = "66"
substs["func_lastbattledamage"] = "36"
substs["@whacksnrg_health"] = "100"
substs["@clicks"] = "13"
substs["@zberrytotal"] = "7"
substs["limbus_ships_shot_down"] = "11" # Result of minigame
substs["limbus_enemies_fought"] = "5" # Result of minigame

# Lookup table for character id to name
charnames = {}
charnames["boots"] = "Boots"
charnames["pal"] = "PAL-18"
charnames["grumpos"] = "Grumpos"
charnames["rho"] = "Rho Bowman"
charnames["democratus"] = "Democratus"
charnames["stiletto"] = "Stiletto"
charnames["paco"] = "Paco \"El Puño\" Estrella"
# Used in hephtower1.ape's suspect logic
charnames["angela"] = "Sister Angela"
charnames["thomas"] = "Thomas Litton"
charnames["liseria"] = "Brother Liseria"

# Hardcoded charname for specific window IDs
hardcharname = {}
hardcharname["103:3916"] = "PAL-18"
hardcharname["103:3917"] = "PAL-18"
hardcharname["103:3919"] = "PAL-18"
hardcharname["54:4000:1"] = "Boots"
hardcharname["54:4000:2"] = "Boots"
hardcharname["54:4000:3"] = "Boots"
hardcharname["54:4001"] = "Boots"
hardcharname["54:4010:1"] = "Boots"
hardcharname["54:4010:2"] = "Boots"
hardcharname["54:4010:3"] = "Boots"
hardcharname["11:2201"] = "Boots"
hardcharname["10:4101"] = "Boots"
hardcharname["112:911:1"] = "Boots"
hardcharname["112:911:2"] = "Boots"
hardcharname["112:911:3"] = "Boots"
hardcharname["112:911:4"] = "Boots"
hardcharname["112:911:5"] = "Boots"
hardcharname["112:911:6"] = "Boots"
hardcharname["112:911:7"] = "Boots"
hardcharname["112:911:8"] = "Boots"
hardcharname["112:911:9"] = "Boots"
hardcharname["112:911:10"] = "Boots"
hardcharname["112:911:11"] = "Boots"
hardcharname["112:911:12"] = "Boots"
hardcharname["112:911:13"] = "Boots"
hardcharname["112:911:14"] = "Boots"
hardcharname["112:911:15"] = "Boots"
hardcharname["112:1010"] = "PAL-18"
hardcharname["112:1015"] = "PAL-18"
hardcharname["112:1020"] = "PAL-18"
hardcharname["112:1025:1"] = "PAL-18"
hardcharname["112:1025:2"] = "PAL-18"
hardcharname["112:1025:3"] = "PAL-18"

class ApeFile:
	def __init__(self, source):
		self.source = source

	def __enter__(self):
		self._fp = open(self.source, "rt", encoding="cp1250")
		self._more = True
		self.line = ""
		self.cmd = None
		self._switch_block_depth = -1
		self.switch_block = None
		return self

	def __exit__(self, *args):
		self._fp.close()

	# Has next lines?
	def has_next(self):
		return self._more

	# Read next line
	def next(self):
		if not self._more:
			return False
		if (ln := self._fp.readline()):
			self.line = ln
			if self.in_switch_block():
				self._incdec_block()
			ln = ln.strip()
			idx = ln.find(" ");
			if idx > -1:
				self.cmd = ln[0:idx]
				if self.cmd.find("switch") != -1:
					self._switch_block_depth = 1
					self.switch_block = self.cmd
				if self.cmd.startswith("#"):
					self.switch_block = None
			else:
				self.cmd = None
		else:
			self._more = False
		return self._more
	
	def in_switch_block(self):
		return self.switch_block != None

	# Is directive
	def is_dir(self):
		return self.cmd and self.cmd.startswith("#")

	# Skip to next directive
	def next_dir(self):
		while self.has_next():
			self.next()
			if self.is_dir():
				return

	def _incdec_block(self):
		# So that in_switch_block() still returns true when the depth is 0
		if self._switch_block_depth == 0:
			self.switch_block = None
		if self.line.find("{") != -1:
			self._switch_block_depth = self._switch_block_depth+1
		if self.line.find("}") != -1:
			self._switch_block_depth = self._switch_block_depth-1

class Quote:
	def __init__(self, source, id):
		self.source = source
		self.id = id
		self.speaker = None
		self.message = []
		self.condition = None
		self.subtitle = False
		self._cnt = 0

	def copy(self):
		self._cnt += 1
		copy = Quote(self.source, self.id + ":" + str(self._cnt))
		copy.speaker = self.speaker
		copy.message = self.message.copy()
		return copy
		
	def __repr__(self):
		return textwrap.dedent("""\
			Source:    {0.source}
			ID:        {0.id}
			Subtitle:  {0.subtitle}
			Condition: {0.condition}
			Speaker:   {0.speaker}
			Message:
			---
			{0.message}
			---""").format(self)

# Parsed argument for a string format like command (e.g. title and body)
class ApeStrFormat:
	def __init__(self, line):
		self.args = []
		self.string = None
		self.parse_line(line)

	def parse_line(self, line):
		if line == None:
			return
		# drop command
		line = line.lstrip()
		idx = line.find(" ")
		line = line[idx:]
		# Assume the first argument is the format string
		idx = line.rfind("\"")
		if idx == -1:
			return
		self.string = parse_string_literal(line[0:idx+1].strip())
		line = line[idx+1:].strip()
		self.args = [x.strip() for x in line.split(",") if x.strip()];

	def __repr__(self):
		if (len(self.args) == 0):
			return self.string
		else:
			return "<<"+self.string+">> "+repr(self.args)

def add_entry(quote):
	if len(quote.message) == 0 or not quote.speaker:
		return
	print(quote)
	speaker = format_string(quote, quote.speaker)
	if not speaker:
		return
	speaker = speaker.strip()
	msgs = [format_string(quote, x) for x in quote.message]
	if any(x is None for x in msgs):
		# broken/incomplete formatted message
		return
	msg = "".join(msgs).strip()
	if len(msg) == 0:
		return
	print("*************************\n\n{0}\n{1}\n\n*************************".format(speaker, msg))
	if quote.subtitle:
		idparts = quote.id.split(":")
		db.execute(
			"""
			insert into subtitles (id, scene_id, scene_subid, source, speaker, message) values (?, ?, ?, ?, ?, ?)
			on conflict(id) do update set speaker = ?, message = ?
			""",
			(quote.id, idparts[0], idparts[1], str(quote.source), speaker, msg, speaker, msg)
		)
	else:
		db.execute(
			"""
			insert into quotes (id, source, speaker, message) values (?, ?, ?, ?)
			on conflict(id) do update set speaker = ?, message = ?
			""",
			(quote.id, str(quote.source), speaker, msg, speaker, msg)
		)

# Parse a string literal to return the string value without escapes
def parse_string_literal(string):
	# remove leading/trailing ", and replace escape characters
	return string.strip()[1:-1].replace("\\n", "\n").replace("\\", "")

def format_string(quote, fmt):
	if fmt == None or quote == None:
		return None
	if len(fmt.args) == 0:
		return fmt.string
	dict = substs.copy()
	if quote.id in hardcharname:
		dict["playerchar0$"] = hardcharname[quote.id]
	elif (m := re.search("func_charinparty\\[([\\w]*)\\] == 3", str(quote.condition))):
		dict["playerchar0$"] = charnames[m.group(1).lower()]
	elif (m := re.search("func_charinparty\\[([\\w]*)\\] != 3", str(quote.condition))):
		if m.group(1).lower() != "boots":
			dict["playerchar0$"] = "Boots"
	elif (m := re.search("\\(LEAD_([\\w]*)\\)", str(quote.condition))):
		dict["playerchar0$"] = charnames[m.group(1).lower()]
	if (m := re.search("suspect_([\\w]*)", str(quote.condition))):
		dict["culprit$"] = charnames[m.group(1).lower()]
	args = fmt.args.copy()
	ret = ""
	offset = 0
	idx = fmt.string.find("%")
	while idx != -1:
		ret += fmt.string[offset:idx]
		offset = idx+1
		if fmt.string[offset] == "s" or fmt.string[offset] == "d":
			offset += 1
			key = args.pop(0).lower()
			if key in dict:
				ret += dict[key]
			else:
				print("ERROR: No string format lookup value for key", key)
				return None
		else:
			ret += "%"
		idx = fmt.string.find("%", offset)
	# Remainder
	if offset < len(fmt.string):
		ret += fmt.string[offset:]
	return ret

def proc_window(ape):
	window_id = ape.line[len("#window"):].strip()
	if window_id in excludeids:
		ape.next()
		return
	ape.next()
	print("Processing window", window_id)
	kraptopSpeaker = None
	basequote = Quote(ape.source, window_id)
	q = basequote
	alts = {}

	while ape.has_next():
		if ape.is_dir():
			break
		elif ape.in_switch_block():
			# We assume a switch code block does not contain speaker or message content, 
			# except for the special krapton title case
			if ape.switch_block == "startswitch" and ape.line.strip().startswith("ComicTitle_R$="):
				kraptopSpeaker = ApeStrFormat("dummy "+ape.line[ape.line.find("=")+1:])
		elif ape.cmd == "if":
			if ape.line.find("{") != -1:
				print("ERROR: encountered if with block, not supported skipping window")
				return
			# branch quote. 'If' only has 1 followup statement, and doesn't nest
			condition = ape.line[ape.line.find("("):ape.line.rfind(")")+1].strip()
			ape.next()
			if ape.cmd != "title" and ape.cmd != "body":
				# No body or title if, just ignore it
				continue;
			if not condition in alts:
				subq = basequote.copy()
				subq.condition = condition
				alts[condition] = subq
			q = alts[condition]
			continue
		elif ape.cmd == "title":
			q.speaker = ApeStrFormat(ape.line)
		elif ape.cmd == "body":
			q.message.append(ApeStrFormat(ape.line))
		elif ape.cmd == "flags" and re.search("(?i)subtitle,\s*TRUE", ape.line):
			basequote.subtitle = True
		elif ape.line.strip().startswith("}"):
			print("ERROR: encountered }, not supported skipping window")
			return;

		# Always reset active quote to base
		q = basequote
		ape.next()

	if len(alts) == 0:
		if kraptopSpeaker != None:
			basequote.speaker = kraptopSpeaker;
		add_entry(basequote)
	else:
		for subq in alts.values():
			subq.subtitle = basequote.subtitle
			if kraptopSpeaker != None:
				subq.speaker = kraptopSpeaker;
			add_entry(subq)

def proc_file(filename):
	source = pathlib.Path(filename)
	if not source.exists():
		print("File does not exists:", filename)
		return
	print("Processing file:", source)
	with ApeFile(source) as ape:
		while ape.has_next():
			if ape.cmd == "#window":
				proc_window(ape)
			else:
				ape.next_dir()

def init_db():
	db.execute('''
		create table if not exists quotes (
			id text primary key,
			source text,
			speaker text,
			message text,
			enabled boolean not null default true,
			last_used timestamp
		)
	''')
	db.execute('''
		create table if not exists subtitles (
			id text primary key,
			scene_id int,
			scene_subid int,
			source text,			
			speaker text,
			message text
		)
	''')

db_conn = sqlite3.connect('quotes.db')
db = db_conn.cursor()
init_db()

try:
	sys.argv.pop(0)
	for file in sys.argv:
		proc_file(file)
		db_conn.commit()
finally:
	db.close()
	db_conn.close()
