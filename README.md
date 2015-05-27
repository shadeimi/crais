Crais
=====

Middleware for Device Management through Selenium GRID using appium

This module is based on the well-documented libusb1 python library, in order to use
the hotplug mechanism to auto-acquire devices (both android & iOS), storing them in a DB for node.json file generation.

The module is based on ZODB engine to store and manage persistent devices class instances,
and use the ConfigObj module for configurations. Please adapt the config.cfg for your needs.
At now, there's no control for the appium instance (will be added ASAP), but the module is
mature enough to manage hotplug events.
