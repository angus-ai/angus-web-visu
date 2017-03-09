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

import StringIO
import datetime
import numpy as np
import logging
import Queue
import time
import multiprocessing

import pytz
import cv2

import angus

LOGGER = logging.getLogger(__name__)

CONF = {
    "appearance": 0.8,
    "disappearance": 0.8,
    "age_estimated": 0.5,
    "gender_estimated": 0.5,
    "focus_locked": 0.9,
    "emotion_detected": 0.4,
    "direction_estimated": 0.8
}

class Worker(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop("index", 0)
        super(Worker, self).__init__(*args, **kwargs)
        self.output = multiprocessing.Queue(20)
        self.capture = None
        self.daemon = True

    def init_capture(self):
        capture = cv2.VideoCapture(self.index)

        capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 480)
        capture.set(cv2.cv.CV_CAP_PROP_FPS, 10)

        LOGGER.info("Capture settings: %sx%s %sfps",
                    capture.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH),
                    capture.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT),
                    capture.get(cv2.cv.CV_CAP_PROP_FPS)
        )

        LOGGER.info("Capture configured")

        if not capture.isOpened():
            LOGGER.error("Capture can not be openened")
            return False

        self.capture = capture
        return True

    def init_angus(self):
        # Try max 5 times angus-server connexion
        conn = angus.connect()
        service = None
        for count in range(5):
            try:
                service = conn.services.get_service("scene_analysis", version=1)
                service.enable_session()
                break
            except Exception as e:
                LOGGER.error(e)
                LOGGER.warning("Scene Analysis not ready (attempt #%s/5), wait 1s and try again",
                               count+1)
                time.sleep(2)
                continue
        if service is None:
            LOGGER.error("Scene analysis is not available, shutdown")
            return False

        LOGGER.info("Scene Analysis service connected")
        self.service = service
        return True

    def loop(self):
        ret, frame = self.capture.read()
        if not ret:
            LOGGER.warning("No image anymore")
            return False

        stamp = datetime.datetime.now(pytz.utc)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, buff = cv2.imencode(".jpg", gray, [cv2.IMWRITE_JPEG_QUALITY, 80])
        buff = StringIO.StringIO(np.array(buff).tostring())

        try:
            job = self.service.process({"image": buff,
                                    "timestamp" : stamp.isoformat(),
                                    "camera_position": "facing",
                                    "sensitivity": CONF,
            })
        except Exception as e:
            LOGGER.error(e.message)
            LOGGER.error("Unknow error (to be checked), just continue")
            return

        res = job.result
        notifications = []

        if not "error" in res:
            # This parses the events
            if "events" in res:
                for event in res["events"]:
                    value = res["entities"][event["entity_id"]][event["key"]]
                    event_stg = "{} - {}, {}, {}".format(event["entity_id"],
                                                           event["type"],
                                                           event["key"],
                                                           value)
                    notifications.append(event_stg)

            # This parses the entities data
            for key, val in res["entities"].iteritems():
                x, y, dx, dy = map(int, val["face_roi"])
                cv2.rectangle(frame, (x, y), (x+dx, y+dy), (0, 255, 0), 2)

        ret, frame = cv2.imencode(".jpg", frame,  [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame = frame.tostring()

        try:
            self.output.put_nowait((frame, notifications))
        except Queue.Full:
            LOGGER.error("Queue is full")
            return False

        return True

    def run(self):

        if not (self.init_capture() and self.init_angus()):
            self.capture.release()
            return

        LOGGER.info("Start grab camera")

        while self.capture.isOpened():
            if not self.loop():
                break

        LOGGER.info("Release capture")
        self.capture.release()
        LOGGER.info("Image capture down")
