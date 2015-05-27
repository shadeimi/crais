
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

from configobj import ConfigObj
import json
import os
import os.path
from tempfile import NamedTemporaryFile

# http://localhost:4444/grid/api/proxy?id=http://localhost:4723 will give you
# The complete node.json for appium in grid mode. Use this one retrieve all
# devices behind appium. And enjoy :)

# java -cp *:. org.openqa.grid.selenium.GridLauncher -role hub -hubConfig hubconfig.json -host 10.57.11.11 

class JsonGenerator():
    def __init__(self, deviceID, filename, port):
        self.deviceID = deviceID
        self.fileName = filename
        self.port = str(port)

        if (os.path.exists("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg") == False):
            self.conf = ConfigObj(os.environ['CONFIG_FILE_PATH'], interpolation=False, stringify=False)
        else:
            self.conf = ConfigObj("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg", interpolation=False, stringify=False)

    def generate_node(self):
        self.base_config = self.conf['mainConfiguration']['gridConfiguration']['base_configuration']
        self.base_config = {"configuration": self.base_config}
        self.base_config["configuration"]["port"] = self.port
        self.base_capabilities = self.base_config.setdefault('capabilities', [])
        
        try:
            self.array = self.deviceID.get_capabilities()['capabilities']
            self.base_capabilities.append(self.array)
        except Exception as e:
            print "JsonGenerator exception: %s" % str(e.message)
            pass
        
        self.node_json = json.dumps(self.base_config, sort_keys=True, indent=2, separators=(',', ': '))
        filePointer = open(self.fileName, 'w')
        filePointer.write(self.node_json)
        filePointer.close()
        
        # UGLY HACK!! modify the self.base_config["configuration"]["register"] value..
        with open(self.fileName, 'r+') as f:
            data = json.load(f)
            data['configuration']['register'] = True
            data['configuration']['url'] = 'http://%s:%s/wd/hub' % (self.base_config["configuration"]["host"] ,self.port)
            f.seek(0) 
            json.dump(data, f, indent=4)
                    
        








