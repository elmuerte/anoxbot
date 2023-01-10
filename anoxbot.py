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

import sqlite3
from mastodon import Mastodon

db_conn = sqlite3.connect('quotes.db')
db = db_conn.cursor()

quote = db.execute("""
select id, speaker, message from quotes
where enabled = true
and length(speaker || message) < 496
and length(message) > 10
order by random()
limit 1
""").fetchone()
db.execute("update quotes set last_used = current_timestamp where id = ?", (quote[0],))
db_conn.commit()

postMsg = "{0}\n{1}".format(quote[1], quote[2])
print('Posting quote:', quote[0])
#print(postMsg)

# Posting the quote
mastodon = Mastodon(
    access_token = 'token.secret',
    api_base_url = 'https://botsin.space/'
)
mastodon.status_post(postMsg)
