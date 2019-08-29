{% set i = inventory.parameters %}

# Welcome to the README!

Target *{{ i.target_name }}* is running:

* {{ i.nginx.replicas }} replicas of *nginx* running nginx image {{ i.nginx.image }}
* on cluster {{ i.cluster.name }}
