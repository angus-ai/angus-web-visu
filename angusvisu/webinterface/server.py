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

"""
Create a complete server with:
* 1 worker
* 1 mjpeg server
* notification system
"""
import logging
import os.path
import os
import Queue

import tornado.web
import tornado.ioloop
import tornado.gen

from notifier import EventSource, NotificationPusher
from mjpegserver import MJPEGHandler
from worker import Worker

LOGGER = logging.getLogger(__name__)
PWD = os.path.dirname(__file__)

def unfold(queue, config):
    try:
        new_frame, notifs = queue.get_nowait()
        if len(notifs) > 0:
            config["event_source"].publish(notifs)
        config["last_frame"] = new_frame
    except Queue.Empty:
        pass

def watch_process(process):
    if not process.is_alive():
        LOGGER.warning("Process is down, shutdown")
        tornado.ioloop.IOLoop.instance().stop()

def make_app():
    LOGGER.info("Make server application")

    video_index = 0

    event_source = EventSource()
    config = {
        "last_frame": None,
        "event_source": event_source,
    }

    # Worker
    worker = Worker(index=video_index)
    worker.start()

    # Unfold results
    unfolder = tornado.ioloop.PeriodicCallback(lambda: unfold(worker.output, config), 10)
    unfolder.start()

    # Worker watchdog
    worker_watch = tornado.ioloop.PeriodicCallback(lambda: watch_process(worker), 1000)
    worker_watch.start()

    # Sender
    return tornado.web.Application([
        (r"/mjpeg", MJPEGHandler, dict(config=config)),
        (r"/notifications", NotificationPusher, dict(event_source=event_source)),
        (r"/", tornado.web.RedirectHandler, dict(url="/index.html")),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": PWD}),
    ])

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    make_app().listen(8888)
    LOGGER.info("Start ioLoop")
    tornado.ioloop.IOLoop.current().start()
