
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

import persistent


class ProcessManager(persistent.Persistent):

    def __init__(self):
        self.process_list = {}
        self.port_manager_element = {}

    def store(self, pid, port, pmelement):
        self.process_list[pid] = port
        self.port_manager_element[str(port[0])] = pmelement

    def delete(self, pid):
        try:
            del(self.process_list[pid])
        except KeyError:
            return False

    def get_process_port(self, pid):
        try:
            return self.process_list[pid]
        except KeyError:
            return False

    def get_process_pid(self, port):
        for key, value in self.process_list.iteritems():
            if value == port:
                return key
    
    def get_port_manager_element(self, port):
        return self.port_manager_element[port]
    
    def get(self):
        return self.process_list
    