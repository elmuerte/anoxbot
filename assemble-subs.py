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


# https://anachrodox.talonbrave.info/

import sys, pathlib, sqlite3

class ScriptFile:
	def __init__(self, source):
		self.source = source

	def __enter__(self):
		self._fp = open(self.source, "rt", encoding="cp1250")
		self._more = True
		self.line = ""
		self.cmd = None
		self.next()
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
		ln = "#"
		while ln and (ln == "" or ln.startswith("#")):
			ln = self._fp.readline()
		if ln:
			ln = ln.strip()
			self.line = ln
			idx = ln.find(":")
			if idx > -1:
				self.cmd = ln[0:idx]
			else:
				self.cmd = None
		else:
			self._more = False
		return self._more

# block = name : flags
class Block:
	def __init__(self, source, id):
		self.source = source
		self.id = id
		self.paths = []
		self.current_path = None
		
	def new_path(self, line):
		self.current_path = Path(self, line)
		self.paths.append(self.current_path)
		return self.current_path
		
	def get_full_id(self):
		return str(self.source.source) + ":" + str(self.id)

# path = order : name : type : flags : timeofs : maxlen : color : count
class Path:
	def __init__(self, block, line):
		parts = line.split(":", 8)
		self.block = block
		self.subs = []
		self.current_sub = None
		self.order = parts[1]
		self.name = parts[2]
		self.type = parts[3]
		self.time_offset = parts[5]
		self.silent_time = 0
		self.sequence_stack = []
		
	def new_sub(self):
		self.current_sub = Sub(self)
		self.subs.append(self.current_sub);
		return self.current_sub
	
	def has_subs(self):
		return len(self.subs) > 0
		
	def get_full_id(self):
		return self.block.get_full_id() + ":" + self.order

class Sub:
	def __init__(self, path):
		self.id = len(path.subs)
		self.path = path
		self.speaker = None
		self.message = ""
		
	def get_full_id(self):
		return self.path.get_full_id() + ":" + str(self.id)

def should_create_new_sub(path, quote):
	if not path.current_sub:
		return True
	if path.silent_time > 5: 
		return True
	if len(path.current_sub.message) > 300 and path.current_sub.message.endswith("."):
		return True
	return path.current_sub.speaker != quote[1]

def handle_sequence(path, id, sub_id):	
	quote = db.execute("select id, speaker, message from subtitles where scene_id = ? and scene_subid = ?", (id, sub_id)).fetchone()
	if not quote:
		print("ERROR: Missing subtitle", id, sub_id)
		return
	if should_create_new_sub(path, quote):
		path.new_sub().speaker = quote[1]
	if len(path.current_sub.message) == 0:
		path.current_sub.message = quote[2]
	else:
		path.current_sub.message = path.current_sub.message + ' ' + quote[2]

# node = type : flags : timelen : other-data
def proc_command_node(path, parts):
	if not path:
		return
	commands = parts[4].split(";")
	path.silent_time += float(parts[3])
	for cmd in commands:
		if cmd.startswith("sequence="):
			idx = cmd.find("=")
			id = cmd[idx+1:].split(":")
			if len(id) != 2:
				print("ERROR: bad sequence command", cmd)
			else:
				handle_sequence(path, int(id[0]), int(id[1]))
			path.sequence_stack.append(cmd[idx+1:])
			path.silent_time = 0
		if cmd.startswith("closewindow="):
			seqid = cmd.split("=")[1]
			if seqid == "0:0":
				# close all
				path.sequence_stack = []
			else:
				try:
					path.sequence_stack.remove(seqid);
				except ValueError:
					pass
			if len(path.sequence_stack) == 0:
				path.silent_time = float(parts[3])

def create_quote(sub):
	print("New quote", sub.get_full_id(), sub.speaker, sub.message)
	db.execute(
		"""
		insert into quotes (id, source, speaker, message) values (?, ?, ?, ?)
		on conflict(id) do update set speaker = ?, message = ?
		""",
		(sub.get_full_id(), str(sub.path.block.source.source), sub.speaker, sub.message, sub.speaker, sub.message)
	)

def proc_script(script):
	blocks = []
	block = None
	path = None
	while script.has_next():
		if script.cmd == "node":
			parts = script.line.split(":", 4)
			if parts[1] == "4":
				proc_command_node(path, parts)
		elif script.cmd == "path":
			path = block.new_path(script.line)
			#print("New path", path.order, path.name)
		elif script.cmd == "block":
			block = Block(script, len(blocks)+1)
			blocks.append(block)
			path = None
		elif script.cmd == "script":
			# script = name : version : blockcount
			parts = script.line.split(":", 3)
			print("Script: '{0}' ({1} blocks)".format(parts[1], parts[3]))		
		script.next()
	for block in blocks:
		for path in block.paths:
			for sub in path.subs:
				create_quote(sub)

def proc_file(filename):
	source = pathlib.Path(filename)
	if not source.exists():
		print("File does not exists:", filename)
		return
	print("Processing file:", source)
	with ScriptFile(source) as script:
		proc_script(script)

db_conn = sqlite3.connect('quotes.db')
db = db_conn.cursor()

try:
	sys.argv.pop(0)
	for file in sys.argv:
		proc_file(file)
		db_conn.commit()
finally:
	db.close()
	db_conn.close()
