#!/usr/bin/python
import os

import mongo

class Subnets(mongo.Mongo):

    @mongo.Format()
    def subnetList(self, projection = { 'hosts': 0 }, format=False):
        return self.searchDoc('subnets', {}, projection)

    @mongo.Format()
    def subnetAdd(self, subnet, description='', discovery=True, discoveryhost='localhost', discoveryinterface='eth0', gateway='', vlan=1, nameservers=['8.8.8.8','4.4.4.4'] ):
        self.logger.info("Add subnet %s" % subnet)
        return self.insertDoc('subnets', subnet, { 'description': description, 'discovery': discovery, 'discoveryhost': discoveryhost, 'discoveryinterface': discoveryinterface, 'gateway': gateway, 'nameservers': nameservers, 'vlan': vlan })
    
    def subnetDel(self, subnet):
        self.logger.info("Delete subnet %s" % subnet)
        self.deleteDoc('subnets', { '_id': subnet })

    @mongo.Format()
    def subnet(self, subnet, projection = { 'hosts': 0 }, format=False):
        return self.searchOneDoc('subnets', { '_id': subnet }, projection)

if __name__ == "__main__":
    t = Subnets()
