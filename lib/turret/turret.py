#!/usr/bin/python
import os
from datetime import datetime
from time import strftime,time

import re
import mongo

class Turret(mongo.Mongo):

    # create output for ansible inventory list
    @mongo.Format()
    def ansibleList(self, meta=False, format=False):
        
        g = self.searchDoc('groups', {}, {"name": 1, "vars": 1, "children": 1})
        h = self.searchDoc('hosts', {}, { "name": 1, "vars": 1, "alias": 1, "groups": 1 })
        
        if meta:
            groups = {'_meta': {'hostvars':{}}} 
        else:
            groups = {}

        # loop groups
        for itg in g:
            groups[itg['name']] = { 'hosts': [], 'vars': {}, 'children': []}

            if 'vars' in itg:
                groups[itg['name']]['vars'] = itg['vars']

            if 'children' in itg:
                groups[itg['name']]['children'] = itg['children'] 

        # loop hosts
        for ith in h:
            host = ith['name']

            if 'groups' in ith:
                for group in ith['groups']:
                    if group in groups:
                        if 'children' not in groups[group]:
                            groups[group]['children'] = []
                        groups[group]['hosts'].append(host)
            else:
                # if no group set in all group
                groups['all']['hosts'].append(host)

            ''' workaround to support aliases for hosts '''
            ''' create aliasgroups from aliases, that only contain this host'''
            if 'alias' in ith:
                for alias in ith['alias']:
                    ''' Warning: alias should not have the same name as group, maybe we should check cq prevent that? '''
                    groups[alias] = { 'hosts': [host] }
                    ''' append aliasgroup  as child to groups this host belongs to, thus inheriting the group variables '''
                    if 'groups' in ith:
                        for group in ith['groups']:
                            groups[group]['children'].append(alias)

            if meta:
                groups['_meta']['hostvars'].update({host: ith['vars']})
                # add `magic_vars` turret_groups and turret_alias
                if 'groups' in ith:
                    groups['_meta']['hostvars'][host].update({'turret_groups': ith['groups']})
                if 'alias' in ith:
                    groups['_meta']['hostvars'][host].update({'turret_alias': ith['alias']})
        return groups

    # changemanagement log
    def cmlogHost(self, hostname, logentry, source='turret', tags={}):
        h = self.findHost(hostname, {"name": 1})
        if h:
            return self.cmlog(h, logentry, source, tags)
        return False

    def cmlog(self, h, logentry, source='turret', tags={}):
        return self.insertDoc('changemanagement', document={ 'hostid': h['_id'], 'hostname': h['name'], 'message': logentry, 'source': source, 'tags': tags, 'date': datetime.now().isoformat()})


    def hostAdd(self, hostname, doc = {'vars': {}, 'groups': [], 'alias': []}):

        # search if host with hostname exist
        h = self.findHost(hostname, {"name": 1})

        if h:
            # warn hostname exists
            self.logger.warn("Hostname {} already exists".format(h['name']))
            return False
        else:
            # add hostname 
            
            # set document name           
            doc['name'] = hostname
             
            r = self.insertDoc('hosts', doc)
            if r:
                self.logger.info("Add host {}".format(hostname))

                # log to changemanagement
                self.cmlog(r, 'Host {} added to inventory'.format(h['name']))
            return r

    def hostDel(self, hostname):
        h = self.findHost(hostname, {"name": 1})

        if h:
            r = self.deleteDoc('hosts', { '_id': h['_id'] })
            if r:
                self.logger.info("Remove host {}".format(h['name']))
                self.cmlog(h, 'Removed {} from inventory'.format(h['name']))
            return r
        return h

    def hostClone(self, hostname, newhostname):
        h = self.findHost(hostname, {})

        if h:
            # remove _id
            del h['_id']
            
            return self.hostAdd(newhostname, h)
                
    def hostRename(self, hostname, newhostname):
        h = self.findHost(hostname, {})

        if h:
            return self.updateDoc('hosts', { '_id': h['_id'] }, { 'name': newhostname}) 
            
    @mongo.Format()
    def hostList(self, search={}, projection={ 'name': 1, 'vars': 1, 'groups': 1, 'alias': 1}, format=False):
        
        result = self.searchDoc('hosts', search, projection)
        
        return result

    ''' add host to group '''
    def hostGroupAdd(self, hostname, groupname):
        
        if groupname:

            # search host with hostname
            h = self.findHost(hostname, {"name": 1})

            if h:
                # check if there's no alias with same name as group to avoid conflicts
                a = self.findAlias(groupname)
                if not a:
                    self.logger.info("Add group {} to {}".format(groupname,hostname))
                    self.updateDoc('hosts', { 'name': h[u'name'] }, { '$addToSet': { 'groups': groupname } } )
                    
                    """ if group not exist then automatic creation of group """
                    g = self.findGroup(groupname)
                    if not g:
                        self.logger.info("Auto create group {}".format(groupname))
                        self.groupAdd(groupname)
                else:
                    self.logger.error("Alias with name {} already exists".format(groupname))
            else:
                self.logger.warning("Unable to find host {}".format(hostname))

    def hostGroupDel(self, hostname, groupname):
        
        # lookup host first
        h = self.findHost(hostname, {"name": 1})

        if h:
            self.logger.info("Remove group {} from {}".format(groupname,hostname))
            self.updateDoc('hosts', { 'name': h['name'] }, { '$pull': { 'groups': groupname } } )

    ''' add alias to Host '''
    def hostAliasAdd(self, hostname, aliasname):
        
        # lookup host first
        h = self.findHost(hostname, {"name": 1})

        if h:
            # check if there's no group with same name as alias to avoid conflicts
            g = self.findGroup(aliasname)
            if not g:
                self.logger.info("Add alias {} to {}".format(aliasname,hostname))
                self.updateDoc('hosts', { 'name': h['name'] }, { '$AddToSet': { 'alias': aliasname } } )
            else:
                self.logger.error("Group with name {} already exists".format(aliasname))
        else:
            self.logger.warning("Unable to find host {}".format(hostname))

    def hostAliasDel(self, hostname, aliasname):
        
        # lookup host first
        h = self.findHost(hostname, {"name": 1})

        if h:
            self.logger.info("Remove alias {} from {}".format(aliasname, hostname))
            self.updateDoc('hosts', { 'name': h['name'] }, { '$pull': { 'alias': aliasname } } )

    def hostSetVars(self, hostname, vars):
        # lookup host first
        h = self.findHost(hostname, {"name": 1})

        if h:
            return self.updateDoc('hosts', { 'name': h['name'] }, { '$set': {'vars': vars}})

    def hostSetVar(self, hostname, key, value):
        # lookup host first
        h = self.findHost(hostname, {"name": 1})

        if h:
            return self.updateDoc('hosts', { 'name': h['name'] }, { '$set': { 'vars.{}'.format(key): value } })


    def groupAdd(self, groupname, doc={ 'children': [], 'vars': {}}):
        # check if there's no alias with same name as group to avoid conflicts
        a = self.findAlias(groupname)
        # check if group does not already exist
        g = self.findGroup(groupname)

        if a:
            self.logger.error("Alias with name {} already exists".format(groupname))
            if g: 
                self.logger.error("Group with name {} already exists".format(groupname))
            else:
                doc['name'] = groupname
                if self.insertDoc('groups', doc):
                    self.logger.info("Added group {} to inventory".format(groupname))


    def groupDel(self, groupname):
        # remove group from hosts
        if self.updateDoc('hosts', { 'groups': groupname }, { '$pull': { 'groups': groupname } }, multi=True ):
            # remove group itself
            if self.deleteDoc('groups', { 'name': groupname }):
                self.logger.info("Removed group {}".format(groupname))
            else:
                self.logger.warning("Unable to remove group {}".format(groupname))

    def groupChildAdd(self, groupname, childname):
        g = self.findGroup(groupname)
        c = self.findGroup(childname)
        if g:
            if c:
                self.updateDoc('groups', { 'name': g[u'name'] }, { '$addToSet': { 'children': c[u'name'] } } )
                self.logger.info("Child group {} added to group {}".format(c[u'name'], g[u'name']))
            else:
                self.logger.error("Child group {} does not exist".format(childname))
        else:
            self.logger.error("Group {} does not exist".format(groupname))
        

    # Return list of groups
    # supports hidden groups starting with '_'
    # meta return vars and list of hosts in group
    @mongo.Format()
    def groupList(self, search={}, projection={'vars': 1}, hidden=False, format=False):
        result = self.searchDoc('groups', search, projection)

        if result:
            groups = []

            for group in result:
                if hidden or not group["name"].startswith('_'):
                    if 'hosts' in projection:
                        group['hosts'] = []
                        for  h in self.searchDoc('hosts', {'groups': group["name"]},{"name": 1}):
                            group['hosts'].append(h["name"])
                        groups.append(group)
                    else:
                        groups.append(group["name"])

            return groups
        return False

    def findHostsForAutocomplete(self, prefix, projection={ 'name': 1, 'alias': 1 }, format=False):
        regex = re.compile('^%s.*' % prefix, re.IGNORECASE)
        search = { "$or": [{'name': { '$regex': regex }}, { 'alias': {'$regex': regex }}]}
        #search = {'name': { '$regex': regex }}
        result =  self.searchDoc('hosts', search, projection)

        # combine name and alias in list
        for n in result:
            x = [n['name']]
            x.extend(n['alias'])
            for r in x:
                if regex.search(r): 
                    yield r

    @mongo.Format()
    def findHost(self, name, projection={}, format=False):
        search = { "$or": [{'name': name}, { 'alias': name }]}
        return self.searchOneDoc('hosts', search, projection)

    @mongo.Format()
    def findHosts(self, search=False, projection={}, format=False):
        if not search:
            search = {}
        elif not isinstance(search, dict):
            search = { "$or": [{'name': search}, { 'alias': search }]}
        return self.searchDoc('hosts', search, projection)

    @mongo.Format()
    def findAlias(self, name, projection={}, format=False):
        return self.searchOneDoc('hosts', { 'alias': name  }, projection)

    @mongo.Format()
    def findGroup(self, search=False, projection={}, format=False):
        if not search:
            search = {}
        elif not isinstance(search, dict):
            search = {'name': search}
        group = self.searchOneDoc('groups', search, projection)
        if 'hosts' in projection:
            group['hosts'] = []
            for  h in self.searchDoc('hosts', {'groups': group["name"]},{"name": 1}):
                group['hosts'].append(h["name"])
        return group

    @mongo.Format()
    def hostvars(self, name, format=False):
        search = {'name': name}
        return self.searchOneDoc('hosts', search, { 'vars': 1 })

    @mongo.Format()
    def inventory(self, search=False, format=False):
        if not search:
            search = {}
        elif not isinstance(search, dict):
            search = { "$or": [{'name': search}, { 'alias': search }]}
        return self.searchDoc('hosts', search, { 'inventory': 1 })

if __name__ == "__main__":
    t = Turret()
    print t.ansibleList()
    
 
