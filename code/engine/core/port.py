
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
        
        def _increment(d, value):
            incrementalValues = []
            for index, item in enumerate(d):
                incrementalValues.append(d[item] + value)
                
            d = dict(zip(d.keys(), incrementalValues))
            
            #HACK: iwdpPost is always 27753
            d['iwdpPort'] = 27753
            
            return d
        
        self.items = []
        self._portValuesBase = {'appiumPort': 4735, 'iwdpPort': 27752, 'chromedriverPort': 9515, 'bootstrapPort': 2250}
        for i in range(1,5):
            self.items.append(_increment(self._portValuesBase, i))     

    def isEmpty(self):
        return self.items == []
    
    def push(self, item):
        self.items.append(item)
    
    def pop(self):
        try:
            return self.items.pop()
        except IndexError as e:
            print str(e.message)
            return {}
            
    def peek(self):
        return self.items[len(self.items)-1]
    
    def size(self):
        return len(self.items)
    
    