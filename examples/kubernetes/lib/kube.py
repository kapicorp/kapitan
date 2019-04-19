from addict import Dict
from kapitan.inputs import kadet

inv = kadet.inventory()

# Returns array of [key, value] pairs from given object.  Does not include hidden fields.
def objectItems(o):
    return o.items()
# Replace all occurrences of `_` with `-`.
def hyphenate(o):
    return o.replace('-','_')

# Convert {foo: {a: b}} to [{name: foo, a: b}]
def mapToNamedList(o):
    items = []
    for k,v in objectItems(o):
        if type(v) is dict:
            tmp = {'name':k}
            tmp.update(v)
            items.append(tmp)
    return items

# Convert from SI unit suffixes to regular number
def siToNum(n):
    _prefix = { 'm': 1e-3,
               'c': 1e-2,
               'd': 1e-1,
               'k': 1e3,
               'M': 1e6,
               'G': 1e9,
               'T': 1e12,
               'P': 1e15,
               'E': 1e18,
               'Ki': 2e10,
               'Mi': 2e20,
               'Gi': 2e30,
               'Ti': 2e40,
               'Pi': 2e50,
               'Ei': 2e60,
               }
    if n[-1] not in _prefix:
        raise Exception('Unknown numerical suffix in '+n)
    return int(n[:-1])*_prefix(n[-1])

def object(apiVersion,kind,name):
    obj,metadata = Dict(),Dict()

    obj.apiVersion = apiVersion
    obj.kind = kind

    metadata.name = name
    metadata.labels = {'name':name}
    metadata.namespace = inv.parameters.namespace
    metadata.annotation = {}

    obj.metadata = metadata
    return obj

class Endpoints(object):
    def __init__(self,name):
        self._object = Object("v1","endpoint",name)
        self._object.subsets = []

    def _ip(self,address):
        self._object.ip = address
        return {'ip':address}

    def _port(self,number):
        self._object.port = number
        return {'port':number}

    def subsets(self):
        return self._object.subsets

    def __repr__(self):
        return repr( self._object )

    def __call__(self):
        return self._object
