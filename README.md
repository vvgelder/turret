# turret

Turret is a cli tool to store the ansible inventory in mongodb instead of flat files.
It plugs right into ansible as dynamic inventory, see [Dynamic Inventory][ansdyn] and [Developing Dynamic Inventory Sources][ansdyndev].


### Install 
Instal mongodb server (on ubuntu in this case) 
> sudo apt-get install mongodb-server

Let ansible use turret:
> export ANSIBLE_HOSTS=/home/user/bin/turret.py

Connection url for turret:
> export TURRET_MONGOURL=mongodb://127.0.0.1:27017/inventory

Set to yes to disable additional host lookups by ansible
> export TURRET_METADEFAULT=Yes

Choose YAML or JSON output to taste (argument --list always outputs in JSON, because that's what ansible expects)
> export TURRET_FORMAT=YAML


### text indexes in mongodb
```sh
db.hosts.createIndex({"$**": "text" }, { name: "hostIndex", background: true } )
db.groups.createIndex({"$**": "text" }, { name: "groupIndex", background: true } )
```

### show output for ansible: 
```sh
 turret --list
 {}
```
### basic commands

```sh
# add new host:
$ turret.py --host new.hostname.nl --add

# edit host vars with your favorite editor defined in EDITOR environment variable:
$ turret.py --host new.hostname.nl --edit

# show all hosts with data:
$ turret.py --hosts --meta
- _id: new.hostname.nl
  groups: {}
  vars:
  - var: foo

$ turret.py --host new.hostname.nl --add-alias new


$ ./turret.py --hosts --meta
- _id: new.hostname.nl
  alias:
  - new
  groups: {}
  vars:
  - var: foo

$ ./turret.py --host new.hostname.nl --add-group allnewservers

$ ./turret.py --hosts --meta
- _id: new.hostname.nl
  alias:
  - new
  groups:
  - allnewservers
  vars:
  - var: foo
```

### Mongo schema

Example host:

_id: server1.domain.com
  alias:
  - server1
  groups:
  - directadmin
  - vps
  vars:
    ansible_ssh_host: 10.0.1.23
    ansible_ssh_port: 22
    ansible_ssh_user: root
    directadmin_port: '2222'
    nagios_description: 'server1'
    nagios_parents: 'node1.domain.com'
    varnish_backend_ip: 127.0.0.1
    varnish_backend_port: 80
    varnish_listen_ip: 10.0.1.23
    varnish_listen_port: 6081

Example group:
- _id: webservers
  children:
  - wordpress
  - magento
  - shared
  vars:
    collectd_plugins_apache: true
    nagios_check_disk_c: 3%
    nagios_check_disk_dev: /dev/vda
    nagios_check_disk_w: 5%



### Contribution

I'm not a experienced programmer, so suggestions and contributions are very welcome.



### License

Apache


**Free Software, please contribute!**

   [ansdyn]: http://docs.ansible.com/ansible/intro_dynamic_inventory.html
   [ansdyndev]: http://docs.ansible.com/ansible/developing_inventory.html
   
 
