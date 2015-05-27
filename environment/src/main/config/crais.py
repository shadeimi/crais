
"""
CRAIS - Middleware for Device Management through Selenium GRID
Copyright (C): 2015 Buongiorno S.p.A. 
Author: Aniello Barletta <aniello.barletta@buongiorno.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import threading
import signal
import sys

import usb1
import libusb1
import Pyro4
import Pyro4.util
from cement.core import foundation, exc
from cement.core.controller import CementBaseController, expose
from cement.core import foundation, controller, handler
from configobj import ConfigObj

from engine.core.managers import HotplugManager
from engine.core.managers import AppiumManager

import time
import os
import os.path
import weakref

license = """
CRAIS version 0.1, Copyright (C) 2015 - Buongiorno S.p.A.
Author: Aniello Barletta <aniello.barletta@buongiorno.com>\n
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.\n"""

class CraisController(CementBaseController, threading.Thread):

    class Meta:
        label = 'base'
        description = "Crais Engine & RPC Interface "
        arguments = [
            (['--test'], dict(help="True if you want to run python unit-testing suite")),
            ]

    @expose(hide=True)
    def default(self):
        print("Inside CraisController.default()")
        
    @expose(help="Local USB device manager")
    def core(self):
        """ Start the USB listener """
        lock = threading.Lock()
        os.environ['CONFIG_FILE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_config.cfg' if self.app.pargs.test else 'config.cfg')
        config_path = os.environ['CONFIG_FILE_PATH']
        usbl = HotplugManager(lock, config_path)
        context = usb1.USBContext()
        print license
        print("CRAIS Bootstrap Process Completed - Acquiring connected devices.. \n")

        if not context.hasCapability(libusb1.LIBUSB_CAP_HAS_HOTPLUG):
            print 'Hotplug support is missing. Please update your libusb version.'
            return
        context.hotplugRegisterCallback(usbl.callback)

        try:
            while True:
                context.handleEvents()
        except (KeyboardInterrupt, SystemExit) as e:
            print "Error: %s" % str(e.message)

    @expose(help="Start RPC Interface")
    def rpc(self):
        print license
        print("Starting CRAIS RPC Server")
        
        os.environ['CONFIG_FILE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_config.cfg' if self.app.pargs.test else 'config.cfg')
        lock = threading.Lock()
        config_path = os.environ['CONFIG_FILE_PATH']
        config_obj = ConfigObj(config_path)
        ns_config = config_obj['mainConfiguration']['craisConfiguration']
        appiummanager = AppiumManager(lock, config_path)

        Pyro4.Daemon.serveSimple(
            {
                appiummanager: "engine.core.managers.AppiumManager"
            },
            host='localhost', 
            ns=True)

    @expose(help="RPC Interface based on Pyro4")
    def query(self):
        from engine.core import device
        print("Query CRAIS RPC Server")
        os.environ['CONFIG_FILE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_config.cfg' if self.app.pargs.test else 'config.cfg')
        config_path = os.environ['CONFIG_FILE_PATH']
        config_obj = ConfigObj(config_path)
        ns_config = config_obj['mainConfiguration']['craisConfiguration']
 
        sys.excepthook = Pyro4.util.excepthook
        appiumObject = Pyro4.Proxy("PYRONAME:engine.core.managers.AppiumManager@%s:%s" % (ns_config['ns_address'], ns_config['ns_port']))
        try:
            # TODO: Circular dependency error!!
            dmr = device.DeviceManager(model='9dh2savt', version='4.4')
            dm = weakref.ref(dmr)
            pid = appiumObject.spawn_server(dm)
            time.sleep(10)
            appiumObject.kill_server(pid=pid)

        except (KeyError, ValueError) as e:
            print str(e.message)
            return False


class CraisApp(foundation.CementApp):
    class Meta:
        label = 'crais'
        base_controller = CraisController


def main():
    app = CraisApp()
    try:
        app.setup()
        app.run()
    except exc.CaughtSignal as e:
        if e.signum == signal.SIGTERM:
            print("Caught signal SIGTERM.. Shutting down..")
        elif e.signum == signal.SIGINT:
            print("Caught signal SIGINT... Shutting down..")
    finally:
        app.close()

if __name__ == '__main__':
    main()
