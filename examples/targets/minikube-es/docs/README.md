# Elasticsearch Minikube

This is a specific version of Elasticsearch to run on a minikube instalation.

## Prerequisites

Elasticsearch is a resource hungry application, for this setup we require
that minikube is running with the above options:

```
$ minikube start --insecure-registry https://quay.io --memory=4096 --cpus=2
```

_If_ you have created the minikube VM previously, you will most likely need to 
delete the vm and recreate it with more memory/cpu. (i.e. 
```$ minikube delete```)

## Setting up

Assuming you're already running Minikube, setup for this target:

```
$ scripts/setup.sh
```

This will create a context in your minikube cluster called {{ target }}.


Apply the compiled manifests:

```
$ scripts/kubectl.sh apply -f manifests/
```

If the commands above did not error, you should be good to go. 

Let's confirm everything is up:

```
$ scripts/kubectl.sh get pods -w
```

## Connecting to Elasticsearch

List the elasticsearch service endpoints running in the cluster:

```
$ minikube service -n {{ inventory.parameters.namespace }}  elasticsearch --url
```

and curl the health endpoint, i.e.: 
```$ curl http://192.168.99.100:32130/_cluster/health?pretty```


## Deleting Elasticsearch

Deleting is easy (warning, this will remove _everything_):

```
$ scripts/kubectl.sh delete -f manifests/
```

