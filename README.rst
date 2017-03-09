=============================================
Web interface for Angus.ai services rendering
=============================================

Introduction
++++++++++++

A very simple web server that:
 1. Grab video camera frames
 2. Send it to Angus.ai to analyse
 3. Get back results (states and events)
 4. Add computed information on a new layer (above original video)
 5. Provide a server with 3 endpoints (on port 8888):

  a. http://localhost:8888/mjpeg a video stream with results
  b. http://localhost:8888/notifications an event source endpoint for events
  c. http://localhost:8888/index.html a landing page

Installation and usage
++++++++++++++++++++++

.. code:: bash

   $> pip install angus-web-visu
   $> python -m angusvisu.webinterface.server
