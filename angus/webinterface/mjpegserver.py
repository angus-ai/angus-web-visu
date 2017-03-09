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

import tornado.web

class MJPEGHandler(tornado.web.RequestHandler):
    """Produce results as a multipart stream.
    """
    def initialize(self, config):
        """Initialize the handler.
        """
        self.up = True
        self.config = config

    @tornado.gen.coroutine
    def get(self):
        """Stream output results.
        """
        self.set_header('Content-Type',
                        'multipart/x-mixed-replace;boundary=--myboundary')

        while self.up:
            frame = self.config["last_frame"]
            response = "\r\n".join(("--myboundary",
                                    "Content-Type: image/jpeg",
                                    "Content-Length: " + str(len(frame)),
                                    "",
                                    frame,
                                    ""))
            self.write(response)
            yield self.flush()
            yield tornado.gen.sleep(0.05)

    def on_connection_close(self):
        """Exit when connection close.
        """
        self.up = False
