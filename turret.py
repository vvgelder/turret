#!/usr/bin/env python

import logging
import pymongo
import json
import os
import sys
import yaml
from subprocess import call

MONGO_GROUPS = 'groups'
MONGO_VARS = 'vars'
MONGO_CHILDREN = 'children'
MONGO_ALIAS = 'alias'
DEFAULT_FORMAT = os.environ.get('TURRET_FORMAT', 'JSON')

class mongo:

    def __init__(self):

        self.logger = logging.getLogger('turret')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s')
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
#        fh = logging.FileHandler('/tmp/turret.log')
#        fh.setLevel(logging.DEBUG)
#        self.logger.addHandler(fh)

        mongourl = os.environ.get('TURRET_MONGOURL')
        
        try:
            self.mgc = pymongo.MongoClient(mongourl)
        except (pymongo.errors.AutoReconnect, pymongo.errors.OperationFailure, pymongo.errors.ConnectionFailure):
            self.logger.error('Unable to connect to mongodb')
            sys.exit(1)

        self.hosts = self.mgc.inventory.hosts
        self.groups = self.mgc.inventory.groups

    def close(self):
        self.mgc.close()


    ''' find host in mongodb '''
    def _find_host(self, hostname):
        try:
            return self.hosts.find_one({ "$or": [{'_id': hostname}, { MONGO_ALIAS: hostname  }]})
        except StandardError as e:
            self.logger.warning("Error finding host %s. Errno: #%s, Error: %s" % (hostname, e.errno, e.strerror))

    ''' update host in mongodb '''
    def _update_host(self, hostname, document):
        try:
            return self.hosts.update({ "$or": [{'_id': hostname}, { MONGO_ALIAS: hostname  }]}, {"$set": document})
        except StandardError as e:
            self.logger.warning("Unable to update host %s. Errno: #%s, Error: %s" % (hostname, e.errno, e.strerror))
       
    ''' return group from mongodb using query or _id''' 
    def _find_group(self, groupname=None, query={}):
        if groupname:
            query = {'_id': groupname}        
        try:
            return self.groups.find_one(query)
        except StandardError as e:
            self.logger.warning("Error finding group %s. Errno: #%s, Error: %s" % (hostname, e.errno, e.strerror))

    def _update_group(self, groupname, document):
        try:
            return self.groups.update({"_id": groupname}, {"$set": document})
        except StandardError as e:
            self.logger.warning("Unable to update group %s. Errno: #%s, Error: %s" % (hostname, e.errno, e.strerror))

    def _edit_vars(self, obj, newvars=None, filename=None, update=False, FORMAT="JSON"):

        v = self._in(newvars, filename, FORMAT=FORMAT)

        if v:
            if update:
                obj[MONGO_VARS].update(v)
            else:
                obj[MONGO_VARS] = v
        return obj

    def _in(self, newvars=None, filename=None, FORMAT="JSON"):
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    if FORMAT=="JSON":
                       return json.load(f)
                    elif FORMAT=="YAML":
                        return yaml.load(f)
            except:
                self.logger.error("Unable to import %s from file %s" % (FORMAT, filename))
        if newvars:
            try:
                if FORMAT=="JSON":
                    return json.loads(newvars)
                elif FORMAT=="YAML":
                    return yaml.load(newvars)
            except:
                self.logger.error("Unable to update vars from %s" % (FORMAT))

    ''' List function for ansible '''
    def list(self, meta=False, OUT="JSON"):
        try:
            g = self.groups.find()
            h  = self.hosts.find()
        except StandardError as e:
            print e
            return self.out({}, OUT)

        if os.environ.get('TURRET_METADEFAULT') in ('Yes','Y','YES','yes','y','True','true','TRUE', '1'):
            meta=True

        if meta:
            groups = {'_meta': {'hostvars':{}}} 
        else:
            groups = {}

        # loop groups 
        for itg in g:
            groups[itg['_id']] = { 'hosts': [], 'vars': {}, 'children': []}   

            if MONGO_VARS in itg:
                groups[itg['_id']]['vars'] = itg[MONGO_VARS]
    
            if MONGO_CHILDREN in itg:
                groups[itg['_id']]['children'] = itg[MONGO_CHILDREN]

        # loop hosts
        for ith in h:
            host = ith['_id']

            ''' workaround to support aliases for hosts '''
            ''' create aliasgroups from aliases, that only contain this host'''
            if MONGO_ALIAS in ith:
                for alias in ith[MONGO_ALIAS]:
                    ''' Warning: alias should not have the same name as group, maybe we should check cq prevent that? '''
                    groups[alias] = { 'hosts': [host] }
                    ''' append aliasgroup  as child to groups this host belongs to, thus inheriting the group variables '''
                    if MONGO_GROUPS in ith:
                        for group in ith[MONGO_GROUPS]:
                            if group in groups:
                                if 'children' not in groups[group]:
                                    groups[group]['children'] = []
                                groups[group]['children'].append(alias)


            if MONGO_GROUPS in ith:
                for group in ith[MONGO_GROUPS]:
                    if group in groups:
                        groups[group]['hosts'].append(host)
            if meta:
                groups['_meta']['hostvars'].update({host: ith[MONGO_VARS]})
                if MONGO_GROUPS in ith:
                    groups['_meta']['hostvars'][host].update({'turret_groups': ith[MONGO_GROUPS]})
                if MONGO_ALIAS in ith:
                    groups['_meta']['hostvars'][host].update({'turret_alias': ith[MONGO_ALIAS]})

        return self.out(groups, OUT)
        

    ''' add host to inventory '''
    def add_host(self, name, groups={}, vars={}):
        try:
            if self.hosts.insert({ '_id': name, MONGO_VARS: vars, MONGO_GROUPS: groups }):
                self.logger.info("Added host %s" % name)
        except pymongo.errors.DuplicateKeyError:
            self.logger.info("Host %s already exists" % name)
        except StandardError as e:
            self.logger.warning("Error adding host %s. Errno: #%s, Error: %s" % (name, e.errno, e.strerror))
   
    ''' remove host from inventory '''
    def remove_host(self, hostname):
        try:
            if self.hosts.remove({'_id': hostname}):
                self.logger.info("Removed host %s" % hostname)
        except:
            self.logger.warning("Unable to remove host %s" % hostname)
        
    ''' add group to inventory ''' 
    def add_group(self, name, children=[], vars={}):
        try:
            self.groups.insert({ '_id': name, MONGO_VARS: vars, MONGO_CHILDREN: children })
            return "Add group %s" % name
        except pymongo.errors.DuplicateKeyError:
            self.logger.warning("Group %s already exists" % name)
        except StandardError as e:
            self.logger.warning("Error adding group %s. Errno: #%s, Error: %s" % (name, e.errno, e.strerror))

    ''' remove group from inventory '''
    def remove_group(self, groupname):
        try:
            g = self.groups.remove({'_id': groupname})
            return "Removed group %s" % groupname
        except:
            return "Unable to remove group %s" % groupname
        
    ''' add host to group '''
    def host_add_group(self, hostname, groupname):
        """ lookup if groups exists in groups collection """
        
        h = self._find_host(hostname)

        if h:
            groups = set(h[MONGO_GROUPS])
            groups.add(groupname)
            h[MONGO_GROUPS] = list(groups)

            if self._update_host(hostname, h):
                self.logger.info("Add group %s to %s" % (groupname,hostname))

                """ if group not exist then automatic creation of group """
                g = self._find_group(groupname)
                if not g:
                    self.add_group(groupname)
        else:
            self.logger.info("Unable to find host %s" % hostname)
    
    ''' remove host from group ''' 
    def host_del_group(self, hostname, groupname):
        
        h = self._find_host(hostname)

        if h:
            groups = set(h[MONGO_GROUPS])
            groups.discard(groupname)
            h[MONGO_GROUPS] = list(groups)

            if self._update_host(hostname, h):
                self.logger.info("Remove group %s to %s" % (groupname,hostname))
        else:
            self.logger.info("Unable to find host %s" % hostname)
       
    ''' add alias to host ''' 
    def host_add_alias(self, hostname, alias):
        """ lookup if groups exists in groups collection """

        h = self._find_host(hostname)

        if h:
            if MONGO_ALIAS not in h:
                h[MONGO_ALIAS] = []
            aliases = set(h[MONGO_ALIAS])
            aliases.add(alias)
            h[MONGO_ALIAS] = list(aliases)

            if self._update_host(hostname, h):
                self.logger.info("Added alias %s to %s" % (alias, hostname))
        else:
            self.logger.info("Unable to find host %s" % hostname)

    ''' remove alias from host '''
    def host_del_alias(self, hostname, alias):
        
        h = self._find_host(hostname)

        if h:
            aliases = set(h[MONGO_ALIAS])
            aliases.discard(alias)
            h[MONGO_ALIAS] = list(aliases)

            if self._update_host(hostname, h):
                self.logger.info("Removed alias %s from %s" % (alias, hostname))
        else:
            self.logger.info("unable to find host %s" % hostname)

    def host_rename(self, hostname, newname):
        ''' rename host with new name '''
        h = self._find_host(hostname)
        
        h['_id'] = newname;

        try:
            if self.hosts.insert(h):
                if self.hosts.remove({'_id': hostname}):
                    self.logger.info("Rename host %s to %s" % (hostname,newname))
        except pymongo.errors.DuplicateKeyError:
            self.logger.warning("Host %s already exists" % newname)
        except StandardError as e:
            self.logger.warning("Error renaming host %s to %s. Errno: #%s, Error: %s" % (hostname, newname, e.errno, e.strerror))
        

    """ get hostvars for host, or with meta get all info for host """
    def hostvars(self, hostname, meta=False, filename=None, FORMAT="JSON"):
        
        h = self._find_host(hostname)

        if h:
            if meta:
                print self.out(h, FORMAT)
            else:
                if filename:
                    with open(filename, 'w') as f:
                        f.write(self.out(h[MONGO_VARS], FORMAT))
                    f.close()
                else:
                    print self.out(h[MONGO_VARS], FORMAT)
        else:
            self.logger.info("unable to find host %s" % hostname)

    """ update hostvars for host """
    def hostvars_update(self, hostname, newvars=None, filename=None, update=False, FORMAT="JSON"):

        h = self._find_host(hostname)

        h = self._edit_vars(h, newvars, filename, update, FORMAT=FORMAT)
        
        if h:
            if self._update_host(hostname, h):
                self.logger.warning("Vars updated for host %s " % (hostname))

    def hostvars_edit(self, hostname, FORMAT="JSON"):
        import tempfile

        EDITOR = os.environ.get('EDITOR','vi')
        
        ''' create tempfile and dump current vars in tempfile '''
        with tempfile.NamedTemporaryFile(suffix=".tmp") as tempfile:
            self.hostvars(hostname, filename=tempfile.name, FORMAT=FORMAT)
            tempfile.flush()
            call([EDITOR, tempfile.name])
            self.hostvars_update(hostname, filename=tempfile.name, FORMAT=FORMAT)

    ''' add child to group '''
    def group_add_child(self, name, child_name):
        """ lookup if groups exists in groups collection """
        g = self._find_group(name)

        if g:
            """ 
                create set to avoid duplicates 
                and convert back to list
            """
            children = set(g[MONGO_CHILDREN])
            children.add(child_name)
            g[MONGO_CHILDREN] = list(children)
        
            return self._update_group(name, g)
        else:
            self.logger.info("No such group %s" % name)
            
    ''' remove child from group ''' 
    def group_del_child(self, name, child_name): 
        """ lookup if groups exists in groups collection """
        g = self._find_group(name)

        if g:
            """ 
                create set so we can use the discard function 
                discard does not throw an error if child group not in set
                and then convert back to list
            """
            children = set(g[MONGO_CHILDREN])
            children.discard(child_name)
            g[MONGO_CHILDREN] = list(children)
        
            return self._update_group(name, g)
        else:
            self.logger.info("No such group %s" % name)
        
    def groupvars(self, groupname, meta=False, filename=None, FORMAT="JSON"):

        g = self._find_group(groupname)
        if g:
            if meta:
                g['hosts'] = []
                for  h in self.hosts.find({ MONGO_GROUPS: { "$in": [groupname]}}):
                    g['hosts'].append(h["_id"])
                print self.out(g, FORMAT)
            else:
                if filename:
                    with open(filename, 'w') as f:
                        f.write(self.out(g[MONGO_VARS], FORMAT))
                    f.close()
                else:
                    print self.out(g[MONGO_VARS], FORMAT)
        else:
            self.logger.info("No such group %s" % groupname)

    def groupvars_update(self, groupname, newvars=None, filename=None, update=False, FORMAT="JSON"):
        g = self._find_group(groupname)

        g = self._edit_vars(g, newvars, filename, update, FORMAT=FORMAT)
        
        if g:
            if self._update_group(groupname, g):
                self.logger.warning("Vars updated for group %s " % (groupname))

    def groupvars_edit(self, groupname, FORMAT="JSON"):
        import tempfile

        EDITOR = os.environ.get('EDITOR','vi')
        
        ''' create tempfile and dump current vars in tempfile '''
        with tempfile.NamedTemporaryFile(suffix=".tmp") as tempfile:
            self.groupvars(groupname, filename=tempfile.name, FORMAT=FORMAT)
            tempfile.flush()
            call([EDITOR, tempfile.name])
            self.groupvars_update(groupname, filename=tempfile.name, FORMAT=FORMAT)

    def group_rename(self, groupname, newname):
        ''' rename group and update groups in host with new name '''
        ''' TODO: rename groups in hosts '''
        g = self._find_group(groupname)
        
        g['_id'] = newname;

        try:
            if self.groups.insert(g):
                if self.groups.remove({'_id': groupname}):
                    self.logger.info("Rename group %s to %s" % (groupname,newname))
        except pymongo.errors.DuplicateKeyError:
            self.logger.warning("Group %s already exists" % newname)
        except StandardError as e:
            self.logger.warning("Error renaming group %s to %s. Errno: #%s, Error: %s" % (groupname, newname, e.errno, e.strerror))
        
    def listhosts(self, meta=False, OUT="JSON"):
        h  = self.hosts.find()
        
        hosts = []

        for host in h:
            if meta:
                hosts.append(host)    
            else:
                hosts.append(host["_id"])
        
        return self.out(hosts, OUT)


    def listgroups(self, meta=False, FORMAT="JSON"):
        g = self.groups.find()
        
        groups = []

        for group in g:
            if meta:
                group['hosts'] = []
                for  h in self.hosts.find({ MONGO_GROUPS: { "$in": [group["_id"]]}}):
                    group['hosts'].append(h["_id"])
                groups.append(group)    
            else:
                groups.append(group["_id"])
        
        print self.out(groups, FORMAT)

    ''' TODO: list groups in tree format '''
    def group_tree(self):
       # g = self.groups.find()
        
        groups = {}

        for itg in g:
            groups.update({itg['_id']:{}})
            if MONGO_CHILDREN in itg.keys():
                groups.update({itg['_id']:{'children': itg[MONGO_CHILDREN]}})
                for child in itg[MONGO_CHILDREN]:
                    groups.update({child:{'ancestor': itg['_id']}})
        
        print groups 
            
    def create_hostfile(self):
        h  = self.hosts.find()
        
        hosts = {}

        for host in h:
            if  MONGO_VARS in host:
                if 'ansible_ssh_host' in host[MONGO_VARS]:
                    hosts[host[MONGO_VARS]['ansible_ssh_host']] = []
                    hosts[host[MONGO_VARS]['ansible_ssh_host']].append(host['_id'])
                    if MONGO_ALIAS in host:
                        hosts[host[MONGO_VARS]['ansible_ssh_host']].extend(host[MONGO_ALIAS])
        
        for i in hosts:
            print i + " " + " ".join(hosts[i])
         
    def out(self, data, OUT="JSON"):
        if OUT=="JSON":
            return json.dumps(data, indent=4)
        elif OUT=="YAML":
            return  yaml.safe_dump(data, default_flow_style=False)
        else:
            return data
        
    def main(self):
        import argparse
        from argparse import RawDescriptionHelpFormatter

        # Argument parsing
        parser = argparse.ArgumentParser(description="Ansible dynamic inventory with mongodb", epilog="""
Show inventory list for ansible:
    turret --list [--meta] 

Show host variables for ansible (--meta for complete host object):
    turret --host <hostname> [--meta]

Show hosts/groups
    turret --hosts [--meta]
    turret --groups [--meta]

Add/Remove host:
    turret --host <hostname> --add
    turret --host <hostname> --remove

Add/Remove alias to host:
    turret --host <hostname> --add-alias <aliasname>
    turret --host <hostname> --del-alias <aliasname>

Add/Remove group to host:
    turret --host <hostname> --add-group <groupname>
    turret --host <hostname> --del-group <groupname>

Edit host/group vars:
    turret --host <hostname> --edit
    turret --group <groupname> --edit

Dump host/group vars as json:
    turret --host <hostname> --dump-json <filename>
    turret --group <groupname> --dump-json <filename>
     
Import host/group vars from json:
    turret --host <hostname> --import <filename>
    turret --group <groupname> --import <filename>

Update host/group vars from json:
    turret --host <hostname> --update <filename>
    turret --group <groupname> --update <filename>

Add/remove group:
    turret --group <groupname> --add
    turret --group <groupname> --remove

Add/Remove child from group:
    turret --group <groupname> --add-child <groupname>
    turret --group <groupname> --del-child <groupname>


        """, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("--list", action='store_true', help="list inventory", dest="inventory_list")
        parser.add_argument("--meta", action='store_true', default=False, help="also return meta data", dest="inventory_meta")
        parser.add_argument("--hosts", action='store_true', help="list hosts", dest="host_list")
        parser.add_argument("--groups", action='store_true', help="list groups", dest="group_list")


        parser.add_argument("--host", action='store', help="Ansible inventory of a particular host", dest="ansible_host")
        parser.add_argument("--host-file", action='store_true', help="create hostfile from inventory", dest="hostfile")
        parser.add_argument("--group", action='store', help="Ansible inventory of a particular group", dest="ansible_group")

        parser.add_argument("--add", action="store_true", help="Add host or group to inventory", dest="add")
        parser.add_argument("--remove", action="store_true", help="Remove host or group from inventory", dest="remove")
        parser.add_argument("--edit", action="store_true", help="Edit vars", dest="edit")
        parser.add_argument("--rename", action="store", help="rename host or group", dest="newname") 
        parser.add_argument("--add-child", action="store", help="Add group as child of other group", dest="add_childgroup")
        parser.add_argument("--del-child", action="store", help="Add group as child of other group", dest="del_childgroup")
        parser.add_argument("--add-group", action="store", help="Add group to host", dest="add_group")
        parser.add_argument("--del-group", action="store", help="Add group to host", dest="del_group")
        parser.add_argument("--add-alias", action="store", help="Add alias to host", dest="add_alias")
        parser.add_argument("--del-alias", action="store", help="Add alias to host", dest="del_alias")
        parser.add_argument("--dump", action="store", help="file to dump json to", dest="dump")
        parser.add_argument("--import", action="store", help="file to import json from", dest="overwrite")
        parser.add_argument("--update", action="store", help="file to update json from", dest="update")
        
        args = parser.parse_args()


        if args.inventory_list:
            print self.list(meta=args.inventory_meta, OUT="JSON")
        elif args.host_list:
            print self.listhosts(meta=args.inventory_meta, OUT=DEFAULT_FORMAT)
        elif args.group_list:
            self.listgroups(meta=args.inventory_meta, FORMAT=DEFAULT_FORMAT)
        elif args.hostfile:
            self.create_hostfile()
        elif args.ansible_host:
            if args.add:
                self.add_host(name=args.ansible_host)
            elif args.add_group:
                self.host_add_group(args.ansible_host,args.add_group)
            elif args.del_group:
                self.host_del_group(args.ansible_host,args.del_group)
            elif args.add_alias:
                self.host_add_alias(args.ansible_host,args.add_alias)
            elif args.del_alias:
                self.host_del_alias(args.ansible_host,args.del_alias)
            elif args.dump:
                self.hostvars(args.ansible_host, FORMAT=DEFAULT_FORMAT, meta=False, filename=args.dump)
            elif args.newname:
                self.host_rename(args.ansible_host,args.newname)
            elif args.overwrite:
                self.hostvars_update(args.ansible_host, FORMAT=DEFAULT_FORMAT, filename=args.overwrite)
            elif args.update:
                self.hostvars_update(args.ansible_host, FORMAT=DEFAULT_FORMAT, filename=args.update, update=True)
            elif args.edit:
                self.hostvars_edit(args.ansible_host, FORMAT=DEFAULT_FORMAT)
            elif args.remove:
                self.remove_host(args.ansible_host)
            else:
                self.hostvars(args.ansible_host, FORMAT=DEFAULT_FORMAT, meta=args.inventory_meta)
        elif args.ansible_group:
            if args.add:
                self.add_group(name=args.ansible_group)
            elif args.dump:
                self.groupvars(args.ansible_group, FORMAT=DEFAULT_FORMAT, meta=False, filename=args.dump)
            elif args.add_childgroup:
                self.group_add_child(args.ansible_group,args.add_childgroup)
            elif args.del_childgroup:
                self.group_del_child(args.ansible_group,args.del_childgroup)
            elif args.overwrite:
                self.groupvars_update(args.ansible_group, FORMAT=DEFAULT_FORMAT, filename=args.overwrite)
            elif args.update:
                self.groupvars_update(args.ansible_group, FORMAT=DEFAULT_FORMAT, filename=args.update, update=True)
            elif args.edit:
                self.groupvars_edit(groupname=args.ansible_group, FORMAT=DEFAULT_FORMAT)
            elif args.newname:
                self.group_rename(args.ansible_group,args.newname)
            elif args.remove:
                self.remove_group(args.ansible_group)
            else:
                self.groupvars(args.ansible_group, FORMAT=DEFAULT_FORMAT, meta=args.inventory_meta)


if __name__ == "__main__":
    t = mongo()
    t.main()
    t.close()


