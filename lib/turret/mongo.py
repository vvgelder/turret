#!/usr/bin/python
import sys
import logging
import yaml
import json
from bson.objectid import ObjectId

import config

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def objectid_representer(dumper, data):
    return dumper.represent_scalar("!ObjectId", str(data))

try:
    from pymongo.errors import ConnectionFailure
    from pymongo.errors import OperationFailure
    from pymongo.errors import DuplicateKeyError
    from pymongo import version as PyMongoVersion
    from pymongo import MongoClient
    from pymongo import cursor
except ImportError:
    try:  # for older PyMongo 2.2
        from pymongo import Connection as MongoClient
    except ImportError:
        sys.stderr.write('the python pymongo module is required')
        sys.exit(1)

class Format(object):
    def __init__(self, *args, **kwargs):
        # store arguments passed to the decorator
        self.args = args
        self.kwargs = kwargs

    def __call__(self, func):
        def formatoutput(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if isinstance(result, cursor.Cursor):
                r = [ v for v in result ]
            else:
                r = result

            if 'format' in kwargs and kwargs['format']:
                if self.outputformat=="JSON":
                    return json.dumps(r, indent=4)
                elif self.outputformat=="YAML":
                    yaml.SafeDumper.add_representer(str, str_presenter)
                    yaml.SafeDumper.add_representer(ObjectId, objectid_representer)
                    return yaml.safe_dump(r, indent=2, width=120, default_flow_style=False)
            else: 
                return r
        return formatoutput

class Mongo(object):
    
    def __init__(self, source='turret', logger=None):

        self.host = config.getcnf('mongo','host') 
        self.port = config.getcnf('mongo','port')
        self.replica_set = config.getcnf('mongo','replica_set')
        self.ssl = config.getcnf('mongo','ssl')
        self.user = config.getcnf('mongo','user')
        self.password = config.getcnf('mongo','password')
        self.database = config.getcnf('mongo','database')
        self.source = source

        self.logger = logger or logging.getLogger(__name__)
    
        try:
            if self.replica_set:
                self.client = MongoClient(self.host, int(self.port), replicaset=self.replica_set, ssl=self.ssl)
            else:
                self.client = MongoClient(self.host, int(self.port), ssl=self.ssl)

            if self.password is None or self.user is None:
                self.logger.error('when supplying login arguments, both user and password must be provided')

            if self.user is not None and self.password is not None:
                self.client.admin.authenticate(self.user, self.password, source=self.database)


        except ConnectionFailure, e:
            self.logger.error('unable to connect to database: %s' % str(e))


        self.db = self.client[self.database]
        self.templates = config.getcnf('pillbox','templates')
        self.outputformat = config.getcnf('pillbox','format')

    @Format()
    def format(self, data, format=False):
        return data


    # import json or yaml files
    def importFormat(self, f):
        with open(f, 'r') as s:
            try:
                if self.outputformat=="JSON":
                    return json.load(s)
                elif self.outputformat=="YAML":
                    return yaml.load(s)
            except:
                self.logger.error("Unable to import {} from file".format(self.outputformat))

    # deprecated, but still in use with ansible module
    def getKey(self, collection, name, key, format=False):
        return self.searchOneDoc(collection, { 'name': name }, { key: 1 })
    
    # deprecated, but still in use with ansible module
    def setKey(self, collection, name, key, value):
        return self.updateDoc(collection, { 'name': name }, { '$set': { key: value } })

    def insertDoc(self, collection, document={}):
        try:
            return self.db[collection].insert_one(document)
        except DuplicateKeyError:
            self.logger.warning("Document {} already exists in {}".format(str(document['_id']),collection))
        except OperationFailure as e:
            self.logger.warning("Error adding document {}. Error: {}".format(str(document['_id']), str(e))) 
        return False

    def deleteDoc(self, collection, search, multi=False):
        try:
            if multi:
                return self.db[collection].delete_many(search)
            else:
                return self.db[collection].delete_one(search)
        except OperationFailure as e:
            self.logger.warning("Error deleting document. Error: {}".format(str(e)))

    def updateDoc(self, collection, search, values, upsert=False, multi=False ):
        try:
            if multi:
                return self.db[collection].update_many(search, values, upsert=upsert)
            else:
                return self.db[collection].update_one(search, values, upsert=upsert)
        except OperationFailure as e:
            self.logger.error('Unable to update document in mongodb: %s' % str(e))
        return False

    def searchDoc(self, collection, search, projection=None):
        try:
            return self.db[collection].find(search, projection)
        except OperationFailure as e:
            self.logger.warning("Error finding object in {}. Error {}".format(collection,str(e)))
        return False

    def searchOneDoc(self, collection, search, projection=None):
        try:
            return self.db[collection].find_one(search, projection)
        except OperationFailure as e:
            self.logger.warning("Error finding object in {}. Error {}".format(collection,str(e)))
            return False

        

if __name__ == "__main__":
    t = Mongo()
