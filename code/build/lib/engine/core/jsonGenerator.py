from configobj import ConfigObj
import json
import os
import os.path


# http://localhost:4444/grid/api/proxy?id=http://localhost:4723 will give you
# The complete node.json for appium in grid mode. Use this one retrieve all
# devices behind appium. And enjoy :)


class JsonGenerator():
    def __init__(self, *args, **kwargs):
        self.deviceDB = kwargs.get('deviceDB')
        self.fileName = kwargs.get('filename') if kwargs.has_key('filename') else 'node.json'

        if (os.path.exists("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg") == False):
            self.conf = ConfigObj(os.path.join(os.path.dirname(
                                  os.path.abspath(__file__)), 'config.cfg'),
                                  interpolation=False, stringify=False)
        else:
            self.conf = ConfigObj("/jhub/_prod/server_ptiqa_crais_daemon/conf/config.cfg", interpolation=False, stringify=False)

        self.base_config = self.conf['mainConfiguration']['gridConfiguration']['base_configuration']
        self.base_config = {"configuration": self.base_config}
        self.base_config["configuration"]["register"] = "True"
        self.base_capabilities = self.base_config.setdefault('capabilities', [])
        self.node_json = json.dumps(self.base_config, sort_keys=True, indent=2, separators=(',', ': '))


    def generate_node(self):
        if len(self.deviceDB) != 0:
            try:
                for i in self.deviceDB.iterkeys():
                    self.array = self.deviceDB[i].get_capabilities()['capabilities']
                    self.base_capabilities.append(self.array)
            except Exception as e:
                print "JsonGenerator exception: %s" % str(e.message)
                pass

        f = open(self.fileName, 'w')
        f.write(self.node_json)
        f.close()








