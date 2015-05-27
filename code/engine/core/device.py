
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

import json
import persistent
import os
import os.path
from configobj import ConfigObj


class DeviceManager(persistent.Persistent):
    def __init__(self, model, version, name, address, udid, browser=None, platform=None):
        if (os.path.exists("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg") == False):
            self.conf = ConfigObj(os.environ['CONFIG_FILE_PATH'], interpolation=False, stringify=False)
        else:
            self.conf = ConfigObj("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg", interpolation=False, stringify=False)

        self.node_config = self.conf['mainConfiguration']['gridConfiguration']['node_configuration']

        self.node_config['id'] = model
        self.node_config['version'] = version
        self.node_config['name'] = name
        self.node_config['address'] = address
        self.node_config['udid'] = udid
        
        if browser is not None:
            self.node_config['browserName'] = browser
        
        if browser is not None:
            self.node_config['platform'] = platform
        
        self.capabilities = {'capabilities': self.node_config}

    def get_capabilities(self):
        return self.capabilities
