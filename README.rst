======================
 Mobile API extensions
======================

The Plugin contains extended Open edX APIs for mobile applications developed by RaccoonGang.

Installation
############

Features
############

Offline HTML Block
*****************

TODO

Offline SCORM XBlock
*****************

This feature provides an enhanced version of the Scorm XBlock for Open edX, based on the original https://github.com/overhangio/openedx-scorm-xblock. This updated version introduces a new feature that allows for the synchronization of mobile offline Scorm grade with the LMS when the application is opened with a stable internet connection.

To add this XBlock add to advanced modules ``mobile_scorm`` in studio.

Open edX devstack
*****************

- Clone this repo in the src folder of your devstack.
- Open a new Lms/Devstack shell.
- Install the plugin as follows: pip install -e /path/to/your/src/mobile-api-extensions
- Restart Lms/Studio services.
