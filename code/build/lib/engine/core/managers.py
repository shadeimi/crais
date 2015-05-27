import time
from functools import wraps
import threading

import libusb1
import os
from pyadb import ADB
from configobj import ConfigObj
import ZODB.DB
import BTrees.OOBTree
import transaction

from device import DeviceManager
from engine.core.jsonGenerator import JsonGenerator
import socket
import tempfile
import subprocess32

import errno
from socket import error as socket_error
from process import ProcessManager
import psutil, urllib2, json
import string
import random
import signal


def retry(exception_to_check, tries=4, delay=3, backoff=1, logger=None):
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry
    return deco_retry


class HotplugManager(threading.Thread):
    _instance = None

    def __init__(self, lock, config_path):
        print config_path
        self.conf = ConfigObj(config_path)
        self.adb = ADB(self.conf['mainConfiguration']
                                ['adbConfiguration']['adbPath'])
        self.adb.restart_server()
        self.lock = lock
        self.storage = ZODB.DB(None)
        self.connection = self.storage.open()
        self.root = self.connection.root
        self.root.devices = BTrees.OOBTree.BTree()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(HotplugManager,
                                  cls).__new__(cls, *args, **kwargs)
            cls._ins = super(HotplugManager,
                             cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @retry(libusb1.LIBUSB_ERROR_ACCESS, tries=2)
    def _usb_connection(self, device, event):
        """ TODO: Manage missing udev rules """
        
        key = "%04x:%04x" % (device.getVendorID(), device.getProductID())
        if event == 2:
            self.lock.acquire()
            try:
                # Delete key object from ZODB
                del self.root.devices[key]
                transaction.get().commit()
            except Exception as e:
                print str(e.message)
                transaction.abort()
                pass
            self.lock.release()

        elif event == 1 and device.getSerialNumber() is not None:
            self.adb.restart_server()
            devices = list(self.adb.get_devices())[1:][0]
            try:
                if device.getSerialNumber() in devices:
                    self.adb.set_target_device(device.getSerialNumber())
                    version = self.adb.shell_command('getprop ro.build.version.release').rstrip()
                    model = ''.join((self.adb.shell_command('settings get secure android_id')).splitlines())

                    self.lock.acquire()
                    try:
                        dm = DeviceManager(model, version)
                        self.root.devices[str(key)] = dm
                        transaction.commit()
                    except (Exception, AttributeError) as e:
                        print str(e.message)
                        transaction.abort()
                        pass
                    self.lock.release()

            except (IndexError, AttributeError, TypeError, KeyError) as e:
                print str(e.message)
                pass

        self.adb.kill_server()

    def callback(self, context, device, event):
        try:
            print "Device %s: %s" % (
                {
                    libusb1.LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED: 'arrived',
                    libusb1.LIBUSB_HOTPLUG_EVENT_DEVICE_LEFT: 'left',
                }[event],
                device
            )

            self._usb_connection(device, event)

        except (AttributeError, libusb1.USBError) as e:
            print str(e.message)
            pass



class AppiumManager(threading.Thread):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppiumManager,
                                  cls).__new__(cls, *args, **kwargs)
            cls._ins = super(AppiumManager,
                             cls).__new__(cls, *args, **kwargs)
        return cls._instance


    def __init__(self, lock, config_path):
        self.conf = ConfigObj(config_path)
        self.appium_config = self.conf['mainConfiguration']['appiumConfiguration']

        self.thread = threading.Thread.__init__(self)
        self.lock = lock
        self.storage = ZODB.DB(None)
        self.connection = self.storage.open()
        self.root = self.connection.root
        self.root.processList = BTrees.OOBTree.BTree()


    def _check_socket(self, host, port):
        time.sleep(1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            return sock.connect((host, port))
        except socket_error as serr:
            if serr.errno != errno.ECONNREFUSED:
                return False

    def _create_appium_bash_script(self, android_id, port):
        cmd_output_path = tempfile.NamedTemporaryFile(delete=False)
        cmd_file_name = cmd_output_path.name
        cmd_output_path.write("#!/bin/bash\n")
        cmd_output_path.write("source %s\n" % self.appium_config["appiumProfile"])
        cmd_tempfile = self._generate_nodejson_file(android_id)
        if self.appium_config["nodeSCL"] == "True":
            cmd_output_path.write("%s '%s --port %s --nodeconfig %s'" % (self.appium_config["nodePath"],
                                                                          self.appium_config["appiumPath"],
                                                                          port, cmd_tempfile))
        else:
            cmd_output_path.write("%s --port %s --nodeconfig %s" % (self.appium_config["appiumPath"],
                                                                     port, cmd_tempfile))
        cmd_output_path.close()
        os.chmod(cmd_file_name, 0755)
        return cmd_file_name

    def _generate_nodejson_file(self, device):
        def id_generator(size=4, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for _ in range(size))

        baseJson = {}
        json_output_path = tempfile.NamedTemporaryFile(delete=False)
        json_file_name = json_output_path.name
        dm = DeviceManager(device, '5.0') # TODO: Find a way to catch the real android version
        fake_key = '%s:%s' % (id_generator(4), id_generator(4))
        baseJson[fake_key] = dm
        JsonGenerator(deviceDB=baseJson, filename=json_file_name).generate_node()
        return json_file_name

    def spawn_server(self, android_id, port):
        def t_spawn_server(self, android_id, port):
            # TODO: Manage appium logfile

            transaction.begin
            if not self._check_socket(self.appium_config["appiumHost"], port) \
                    and not ProcessManager().get_process_port(port):
                self.lock.acquire()
                script = self._create_appium_bash_script(android_id, port)
                proc = subprocess32.Popen(script, shell=True)
                self._check_socket(self.appium_config["appiumHost"], port)
                pm = ProcessManager()
                pm.store(proc.pid, port)
                self.root.processList[android_id] = pm
                self.lock.release()
            else:
                transaction.abort
                exit(-1)

            transaction.commit()
            return proc.pid

        self.thread = threading.Thread(target=t_spawn_server, args=(self, android_id, port,))
        self.thread.start()


    def get_appium_process(self, port):
        return self.root.processList[port]

    @retry(urllib2.URLError)
    def _wait_appium_session(self, port):
        try:
            url = "http://%s:%s/wd/hub/sessions" % (self.appium_config["appiumHost"], str(port))
            print "connect to " + url
            response = urllib2.urlopen(urllib2.Request(url))
            page = response.read()
            data = json.loads(page)
            if data['status'] != 0 or len(data['value']) > 0:
                raise Exception("invalid status or values")
            return True
        except urllib2.URLError as e:
            return False

    def kill_server(self, pid):
        try:
            def on_terminate(proc):
                print("process {} terminated".format(proc))

            p = psutil.Process(pid)
            child_pid = p.children(recursive=True)
            for pid in child_pid:
                pid.terminate()

            gone, alive = psutil.wait_procs(child_pid, timeout=3, callback=on_terminate)
            for p in alive:
                p.kill()

            del self.root.processList[pid]
            if self.check_server():
                return True

        except (KeyError, psutil.NoSuchProcess, TypeError):
            return

        # TODO: Delete tmpfile

    def check_server(self, pid=None, port=None):
        if pid:
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True
        if port:
            pass
