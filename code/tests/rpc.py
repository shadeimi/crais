
import random
import unittest
import Pyro4
import Pyro4.util
from cement.core import foundation, exc
from cement.core.controller import CementBaseController, expose
from configobj import ConfigObj

from engine.core.managers import HotplugManager
from engine.core.managers import AppiumManager
import sys, os, socket, threading, time

class RPCSequenceFunctions(unittest.TestCase):

    def setUp(self):
        os.environ['CONFIG_FILE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_config.cfg')
        config_path = os.environ['CONFIG_FILE_PATH']
        config_obj = ConfigObj(config_path)
        ns_config = config_obj['mainConfiguration']['craisConfiguration']

        sys.excepthook = Pyro4.util.excepthook
        self.appiumObject = Pyro4.Proxy("PYRONAME:engine.core.managers.AppiumManager@%s:%s" % (ns_config['ns_address'], ns_config['ns_port']))
        
    def test_spawn(self):
        pid = self.appiumObject.spawn_server(android_id="pippo", port=1234)
        time.sleep(10)
        self.appiumObject.kill_server(pid=pid)

if __name__ == '__main__':
    unittest.main()