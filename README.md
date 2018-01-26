# turret (deprecated, pillbox is going to replace this)

Turret is a cli tool to store the ansible inventory in mongodb instead of flat files.
It plugs right into ansible as dynamic inventory, see [Dynamic Inventory][ansdyn] and [Developing Dynamic Inventory Sources][ansdyndev].


### Install (ubuntu)

git clone https://github.com/vvgelder/turret.git

cd turret

sudo python setup.py install

create config ~/.turretrc
```sh
---
mongo:
    user: "inventory"
    password: "verysecretpassword"
    host: "127.0.0.1"
    port: 27017
    database: "inventory"
pillbox:
    meta: True
    format: "YAML"
```

Instal mongodb server 
> sudo apt-get install mongodb-server


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
$ turret -s new.hostname.nl --add

# edit host vars with your favorite editor defined in EDITOR environment variable:
$ turret -s new.hostname.nl -e

# show all hosts with data:
$ turret -s -m
- _id: new.hostname.nl
  groups: {}
  vars:
  - var: foo

# add alias
$ turret -s new.hostname.nl --add-alias new

# show all hosts
$ turret -S -m
- _id: new.hostname.nl
  alias:
  - new
  groups: {}
  vars:
  - var: foo

$ turret -s new.hostname.nl --add-group allnewservers

# show group
$ turret -g allnewservers

# show all groups
$ turret -G -m

# add child group
turret -g parent --add-child childgroup
```

### Mongo schema

Example host:

- name: server1.domain.com
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
- name: webservers
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
   
 
