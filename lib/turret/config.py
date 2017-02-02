#!/usr/bin/python

import sys
import os
import logging
import yaml

defaults = { 'mongo': { 
    'host': 'localhost', 
    'port': 27017,
    'ssl': False,
    'user': None,
    'password': None,
    'database': 'turret'
    }
} 


class ConfigError(Exception):
    """
    Exception raised when the config is invalid.
    """


def load_config():
    turretyml = os.path.expanduser('~/.turret.yml')
    if not os.path.exists(turretyml):
        turretyml = "/etc/turret/turret.yml"

    try:
        with open(turretyml, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as error:
               raise ConfigError('Error parsing yaml: {}'.format(str(error)))
    except Exception as error:
        raise ConfigError('Error opening config: {}'.format(str(error)))
         
def getcnf(section, key):
    if section in cnf:
        if key in cnf[section]:
            return cnf[section][key]
    if section in defaults:
        if key in defaults[section]:
            return defaults[section][key]
    return None

try:
    cnf = load_config()
except Exception as error:
    logging.error(error)
    sys.exit(1)

if __name__ == "__main__":
    print cnf
