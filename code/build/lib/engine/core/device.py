
import json
import persistent
import os
import os.path
from configobj import ConfigObj


class DeviceManager(persistent.Persistent):
    def __init__(self, model, version):
        if (os.path.exists("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg") == False):
            self.conf = ConfigObj(os.environ['CONFIG_FILE_PATH'], interpolation=False, stringify=False)
        else:
            self.conf = ConfigObj("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg", interpolation=False, stringify=False)

        self.node_config = self.conf['mainConfiguration']['gridConfiguration']['node_configuration']

        self.node_config['id'] = model
        self.node_config['version'] = version

        self.capabilities = {'capabilities': self.node_config}

    def get_capabilities(self):
        return self.capabilities
