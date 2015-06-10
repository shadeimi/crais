
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

import time
from functools import wraps
import threading
from threading import Thread

import libusb1
import os, re
import traceback
from pyadb import ADB
from configobj import ConfigObj
import ZODB.DB
import BTrees.OOBTree
import transaction

from device import DeviceManager
from engine.core.jsonGenerator import JsonGenerator
from socket import *
import tempfile
import subprocess32
from subprocess32 import Popen, PIPE, STDOUT

import errno
from socket import error as socket_error
from process import ProcessManager
from port import PortManager
import psutil, urllib2, json
import string
import random
import signal
import socket 

pl = PortManager()

class ADBExtender(ADB):
    
    __extender_output = None
    
    def fork_server_on_port(self, port=5037):
        """
        Fork ADB server using -a parameter & -P for port
        adb -a -P <port> fork-server
        """
        self.__clean__()
        self.port = port
        self.run_cmd('-a -P %s fork-server server&' % self.port)
        return self.__extender_output
    
    def restart_server(self):
        self.kill_server()
        return self.fork_server_on_port()
    

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
        self.conf = ConfigObj(config_path)
        self.adb = ADBExtender(self.conf['mainConfiguration']['adbConfiguration']['adbPath'])
        self.imdInfoBinPath = self.conf['mainConfiguration']['iDeviceConfiguration']['imdInfoBinPath']
        self.adb.restart_server()
        self.lock = lock
        self.storage = ZODB.DB(None)
        self.connection = self.storage.open()
        self.root = self.connection.root
        self.root.devices = BTrees.OOBTree.BTree()
        self.am = AppiumManager(self.lock, self.conf)

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(HotplugManager,
                                  cls).__new__(cls, *args, **kwargs)
            cls._ins = super(HotplugManager,
                             cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def _check_device_in_ZODB(self, key):
        return key in self.root.devices.keys()

    def _check_android(self, key):
        pass
    
    @retry(IndexError, tries=3)
    @retry(KeyError, tries=3)
    def _acquire_ios_parameters(self, deviceSerialNumber):
        p1 = subprocess32.Popen([self.imdInfoBinPath, "--udid", deviceSerialNumber], shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        ideviceInfo = p1.stdout.read()

        b = filter(None, ideviceInfo.splitlines())
        c = {}
        for j in b:
            raw = j.split(':')
            c[raw[0].strip()] = raw[1].strip()
        
        return {'udid': c['UniqueDeviceID'], 'id': c['SerialNumber'], 'browserName': c['ProductType'].split(',')[0],
                'version': c['ProductVersion'], 'name': c['DeviceName'], 'platform': "MAC"}
        

    @retry(IndexError, tries=3)
    @retry(KeyError, tries=3)
    @retry(libusb1.LIBUSB_ERROR_ACCESS, tries=2)
    def _usb_connection(self, device, event):
        """ TODO: Manage missing udev rules """
        key = "%04x:%04x" % (device.getVendorID(), device.getProductID())
        
        if event == 2 and self._check_device_in_ZODB(key):
            deviceKey = self.root.devices[key]
            try:     
                   
                ks = self.am.kill_server(deviceKey)       
            except Exception as e:
                print traceback.format_exc()
                
            del self.root.devices[key]
            transaction.commit()
                

        elif event == 1 and device.getSerialNumber() is not None:
            time.sleep(5)    
            
            if key.split(':')[0] == "05ac" and (not bool(re.match('[a-z]+$', device.getSerialNumber(), re.IGNORECASE)) 
                                                and not bool(re.match('[0-9]+$', device.getSerialNumber(), re.IGNORECASE))):
                self.lock.acquire()
                try: 
                    deviceParams = self._acquire_ios_parameters(device.getSerialNumber())
                    address = socket.gethostbyname(socket.gethostname())
                    dm = DeviceManager(model=deviceParams['id'], version=deviceParams['version'], name=deviceParams['name'],
                                       address=address, udid=deviceParams['udid'], browser="Safari", platform=deviceParams['platform'])
                    
                    self.root.devices[str(key)] = dm
                    transaction.commit()
                    self.am.spawn_server(self.root.devices[str(key)], deviceType=2)
                    
                except (Exception, IndexError, AttributeError, TypeError, KeyError) as e:
                    print 'ERROR: Cannot acquire device %s' % key
                    print traceback.format_exc()
                    pass
                
                self.lock.release()
                
            else:    
                try:
                    time.sleep(5)
                    self.devices = list(self.adb.get_devices())[1:][0]
                    if device.getSerialNumber() in self.devices:
                        self.adb.set_target_device(device.getSerialNumber())
                        version = self.adb.shell_command('getprop ro.build.version.release').rstrip()
                        model = ''.join((self.adb.shell_command('settings get secure android_id')).splitlines())
                        name = self.adb.shell_command('getprop ro.product.model').rstrip()
                        udid = self.adb.shell_command('getprop ro.serialno').rstrip()
                        address = socket.gethostbyname(socket.gethostname())
                        if not model.isalnum():
                            cmd = 'content query --uri content://settings/secure --projection name:value --where "name=\'android_id\'"'
                            model = self.adb.shell_command(cmd).strip().split(',')[1].split('=')[1]
    
                        self.lock.acquire()
                        try:
                            dm = DeviceManager(model, version, name, address, udid)
                            self.root.devices[str(key)] = dm
                            transaction.commit()
                            self.am.spawn_server(self.root.devices[str(key)], deviceType=1)
                        except (Exception, AttributeError) as e:
                            print str(e.message)
                            transaction.abort()
                            pass
                        self.lock.release()
                        
                except (IndexError, AttributeError, TypeError, KeyError) as e:
                    print 'ERROR: Cannot acquire device %s' % key
                    print traceback.format_exc()
                    pass
                

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


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs, Verbose)
        self._return = None
    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,
                                                **self._Thread__kwargs)
    def join(self):
        Thread.join(self)
        return self._return    
    

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
        """ deviceType is 1 for Android devices & 2 for Apple devices """
        
        self.conf = ConfigObj(config_path)
        self.appium_config = self.conf['mainConfiguration']['appiumConfiguration']
        self.iwdpBinPath = self.conf['mainConfiguration']['iDeviceConfiguration']['iwdpBinPath']
        self.idvInstallerPath = self.conf['mainConfiguration']['iDeviceConfiguration']['ideviceinstallerPath']
        self.thread = threading.Thread.__init__(self)
        self.lock = lock
        
        self.storage = ZODB.DB(None)
        self.connection = self.storage.open()
        self.root = self.connection.root
        self.root.processList = BTrees.OOBTree.BTree()

    def spawn_server(self, deviceID, deviceType):
        
        def get_port():
            global pl
            return pl.pop()

        def android_spawn_server(deviceID, portValues):
            try:
                self.lock.acquire()
                pm = ProcessManager()
                script = self._create_appium_bash_script(deviceID, portValues['appiumPort'], portValues['chromedriverPort'], portValues['bootstrapPort'])
                proc = subprocess32.Popen(script, shell=True)
                print "Bootstrapping Appium instance with PID: %s" % proc.pid
                pm.store((proc.pid,), (portValues['appiumPort'],), portValues)
                self.root.processList[deviceID.get_capabilities()['capabilities']['id']] = pm
                transaction.commit()
                self.lock.release()
            except Exception as e:
                transaction.abort()
                print traceback.format_exc()

            return proc.pid
        
        def apple_spawn_server(deviceID, portValues):
            try:
                self.lock.acquire()
                pm = ProcessManager()
                
                iwdp_script = self._create_iwdp_bash_script(deviceID, portValues['iwdpPort'])
                with open(os.devnull, "w") as fnull:
                    iwdp_proc = subprocess32.Popen(iwdp_script, shell=True, stdout = fnull, stderr = fnull)
                    
                print "Bootstrapping iOS Webkit Debug Proxy instance with PID: %s" % iwdp_proc.pid
                
                appium_script = self._create_appium_bash_script(deviceID, portValues['appiumPort'], portValues['chromedriverPort'], portValues['bootstrapPort'])
                appium_proc = subprocess32.Popen(appium_script, shell=True)
                print "Bootstrapping Appium instance with PID: %s" % appium_proc.pid
                
                pm.store((iwdp_proc.pid, appium_proc.pid,), (portValues['appiumPort'], portValues['iwdpPort'],), portValues)
                self.root.processList[deviceID.get_capabilities()['capabilities']['id']] = pm
                transaction.commit()
                self.lock.release()
            except Exception as e:
                transaction.abort()
                print traceback.format_exc()

            return (iwdp_proc.pid, appium_proc.pid,)
        
        portThread = ThreadWithReturnValue(target=get_port)
        portThread.start()
        portValues = portThread.join()
        
        if deviceType == 1: #Android
            thread = ThreadWithReturnValue(target=android_spawn_server, args=(deviceID, portValues, ))
            thread.start() 
            
        elif deviceType == 2: #Apple
            thread = ThreadWithReturnValue(target=apple_spawn_server, args=(deviceID, portValues,))
            thread.start()

    def _create_appium_bash_script(self, deviceID, appiumPort, chromedriverPort, bootstrapPort):
        cmd_output_path = tempfile.NamedTemporaryFile(delete=False)
        cmd_file_name = cmd_output_path.name
        cmd_output_path.write("#!/bin/bash\n")
        cmd_output_path.write("source %s\n" % self.appium_config["appiumProfile"])
        cmd_tempfile = self._generate_nodejson_file(deviceID, appiumPort)
        android_udid = deviceID.get_capabilities()['capabilities']['udid']
        if self.appium_config["nodeSCL"] == "True":
            cmd_output_path.write("%s '%s -U %s -bp %s --port %s  --chromedriver-port %s --nodeconfig %s --address %s --log-timestamp --log-no-colors " % (self.appium_config["nodePath"],
                                                                          self.appium_config["appiumPath"], android_udid, bootstrapPort,
                                                                          appiumPort, chromedriverPort, cmd_tempfile, self.appium_config["appiumHost"]))
        else:
            cmd_output_path.write("%s -U %s --port %s  --chromedriver-port %s -bp %s --nodeconfig %s --address %s --log-timestamp --log-no-colors " % (self.appium_config["appiumPath"],
                                                                     android_udid, appiumPort, chromedriverPort,  bootstrapPort, cmd_tempfile, self.appium_config["appiumHost"]))
        cmd_output_path.close()
        os.chmod(cmd_file_name, 0755)
        return cmd_file_name
    
    def _create_iwdp_bash_script(self, deviceID, port):
        udid = deviceID.get_capabilities()['capabilities']['udid']
        cmd_output_path = tempfile.NamedTemporaryFile(delete=False)
        cmd_file_name = cmd_output_path.name
        cmd_output_path.write("#!/bin/bash\n")
        cmd_output_path.write("source %s\n" % self.appium_config["appiumProfile"])
        cmd_output_path.write("%s %s -c %s:%s -d" % (self.appium_config['nodePath'], self.iwdpBinPath, udid, port))
        
        cmd_output_path.close()
        os.chmod(cmd_file_name, 0755)
        return cmd_file_name

    def _generate_nodejson_file(self, deviceID, port):
        json_output_path = tempfile.NamedTemporaryFile(delete=False)
        json_file_name = json_output_path.name
        JsonGenerator(deviceID, filename=json_file_name, port=port).generate_node()
        return json_file_name

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

    def kill_server(self, deviceID):
        port = self.root.processList[deviceID.get_capabilities()['capabilities']['id']].get().values()[0]        
        pl.push(self.root.processList[deviceID.get_capabilities()['capabilities']['id']].get_port_manager_element(str(port[0])))
        
        def _kill_server(pid):
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
                
                return True
    
            except (KeyError, psutil.NoSuchProcess, TypeError) as e:
                print str(e.message)
                print traceback.format_exc()
                return False
        
        pid = self.root.processList[deviceID.get_capabilities()['capabilities']['id']].get().keys()[0]
        pproc = None
           
        for p in pid:
            thread = threading.Thread(target=_kill_server, args=(p, ))
            thread.start()
        
        for p in port:
            pproc = subprocess32.Popen(["lsof", "-t", "-i:%s" % p], stdout=PIPE, stderr=PIPE).communicate()
        
        for i in pproc:
            
            if i: 
                thread = threading.Thread(target=_kill_server, args=(int(i.rstrip()), ))
                thread.start()
                 
            
             
            
            
            
            
