from addict import Dict
import json
import yaml
from pprint import pprint


class BaseObj(object):
    def __init__(self, init_as={}, **kwargs):
        """
        returns a BaseObj
        set init_as to initialise self.root
        use kwargs to set values in self (starting with _)
        use kwargs to set values in self.root
        values in self.root are returned as dict via self.to_dict()
        """
        self.root = Dict(init_as)
        self._parse_kwargs(kwargs)
        self.new()
        self.body()

    @classmethod
    def from_json(cls, file_path, **kwargs):
        """
        returns a BaseObj initialised with json content
        from file_path
        """
        with open(file_path) as fp:
            json_obj = json.load(fp)
            return cls(init_as=json_obj, **kwargs)

    @classmethod
    def from_yaml(cls, file_path, **kwargs):
        """
        returns a BaseObj initialised with yaml content
        from file_path
        """
        with open(file_path) as fp:
            yaml_obj = yaml.safe_load(fp)
            return cls(init_as=yaml_obj, **kwargs)

    def _parse_kwargs(self, kwargs):
        """
        sets priv and root values from kwargs
        kwargs keys starting with _ are private
        any other keys are set in self.root
        """
        for k, v in kwargs.items():
            if k.startswith('_'):
                setattr(self, k, v)
            else:
                setattr(self.root, k, v)

    def need(self, key, msg="key and value needed"):
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
        """
        initialise need()ed keys for
        a new BaseObj
        """
        pass

    def body(self):
        """
        set values/logic for self.root
        """
        pass

    def _to_dict(self, obj):
        """
        recursively update obj should it contain other
        BaseObj values
        """
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
        """
        returns object dict
        """
        return self._to_dict(self)

# XXX TEST TEST
# TODO move this to proper tests
if __name__ == '__main__':
    class Deployment(BaseObj):
        def new(self):
            self.need('z')
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
    b = BaseObj.from_json("test.json", andthis="also")
    pprint(b.to_dict())
    b = BaseObj.from_yaml("test.yaml", andthis="too")
    pprint(b.to_dict())
