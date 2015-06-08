
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


class PortManager(persistent.Persistent):
    def __init__(self):
        self.portValues = {'appiumPort': 4735, 'iwdpPort': 27752, 'chromedriverPort': 9515, 'bootstrapPort': 2250}
            
    def increment(self):
        incrementalValues = []
        for index, item in enumerate(self.portValues):
            incrementalValues.append(self.portValues[item] + 1)
            
        self.portValues = dict(zip(self.portValues.keys(), incrementalValues))
            
    
    def decrement(self):
        incrementalValues = []
        for index, item in enumerate(self.portValues):
            incrementalValues.append(self.portValues[item] - 1)
            
        self.portValues = dict(zip(self.portValues.keys(), incrementalValues))


    def get(self):
        return self.portValues