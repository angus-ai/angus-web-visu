# -*- coding: utf-8 -*-

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import json

from tornado.locks import Condition
from tornado.iostream import StreamClosedError
import tornado.web
import tornado.ioloop
import tornado.gen

class EventSource(object):

    def __init__(self):
        self.lock = Condition()
        self.events = None

    @tornado.gen.coroutine
    def publish(self, events):
        self.events = events
        self.lock.notify_all()

    @tornado.gen.coroutine
    def wait(self):
        yield self.lock.wait()

class NotificationPusher(tornado.web.RequestHandler):
    def initialize(self, event_source):
        self.source = event_source

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    @tornado.gen.coroutine
    def get(self):
        self.set_header('Content-Type', 'text/event-stream')
        while True:
            yield self.source.wait()
            try:
                self.write('data: {}\n\n'.format(json.dumps(self.source.events)))
                yield self.flush()
            except StreamClosedError:
                break
