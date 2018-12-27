from addict import Dict
from pprint import pprint

# maybe we can have self for root values and local for priv?
class BaseObj(object):
    def __init__(self, **kwargs):
        self.root = Dict()
        for k, v in kwargs.items():
            if k.startswith('_'):
                setattr(self, k, v)
            else:
                setattr(self.root, k, v)
        self.new()
        self.body()

    def need(self, key, msg):
        """
        requires that key is set in root
        errors with msg if key not set
        """
        err_msg ='{}: "{}": {}'.format(self.__class__.__name__, key, msg)
        if key.startswith('_') and not hasattr(self, key):
            raise Exception(err_msg)
        if key not in self.root:
            raise Exception(err_msg)

    def new(self):
        pass

    def body(self):
        pass

    def _to_dict(self, obj):
        if isinstance(obj, BaseObj):
            for k, v in obj.root.items():
                obj.root[k] = self._to_dict(v)
            # BaseObj needs to return to_dict()
            return obj.root.to_dict()
        elif isinstance(obj, list):
            obj = [self._to_dict(item) for item in obj]
            # list has no .to_dict, return itself
            return obj
        elif isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._to_dict(v)
            # dict has no .to_dict, return itself
            return obj

        # anything else, return itself
        return obj

    def to_dict(self):
        return self._to_dict(self)


class Deployment(BaseObj):
    def new(self):
        self.need('z', 'I need this')
        self.root['ola'] = 1
        self.root.ole = 2
        self.root.oli = {'x': BaseObj(a=1, b=2)}
        class MyThing(BaseObj):
            def body(self):
                self.root.yoda = 3
                class OtherThing(BaseObj):
                    def new(self):
                        self.need('stuff', 'got no stuff')
                    def body(self):
                        self.root.yada = 4
                self.root.otherthing = OtherThing(a=3, stuff=666)
        self.root.mything = MyThing()
        self.root.things = [MyThing(y=3), MyThing(u=9, f=[MyThing(p=9)])]


d = Deployment(a=2, z=3, _c=4, w={'a': 34})
pprint(d.to_dict())
f = Deployment(a=2, z=3, _c=4, w={'b': 34})
f.root.z = 69
pprint(f.to_dict())
