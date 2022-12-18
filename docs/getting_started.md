# :kapitan-logo: **Getting started with Kapitan**

## Initial Setup for `Kapitan`

### Setup your repository

```shell
git clone git@github.com:kapicorp/kapitan-reference.git kapitan-templates
cd kapitan-templates
```

### Run `kapitan compile`

```shell
./kapitan compile
```

```text
Compiled postgres-proxy (1.51s)
Compiled tesoro (1.70s)
Compiled echo-server (1.64s)
Compiled mysql (1.67s)
Compiled gke-pvm-killer (1.17s)
Compiled prod-sockshop (4.74s)
Compiled dev-sockshop (4.74s)
Compiled tutorial (1.68s)
Compiled global (0.76s)
Compiled examples (2.60s)
Compiled pritunl (2.03s)
Compiled sock-shop (4.36s)
```

### Create a new target

```shell
cat << EOF > targets/nginx.yml
--8<-- "kubernetes/inventory/targets/minikube-nginx-helm.yml"
EOF
```


## Credits

* [Jsonnet](https://github.com/google/jsonnet)
* [Jinja2](http://jinja.pocoo.org/docs/2.9/)
* [reclass](https://github.com/salt-formulas/reclass)
