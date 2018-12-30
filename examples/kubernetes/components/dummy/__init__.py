from kapitan.inputs import kadet
from .testmodule import b
# from kadet.search_paths.lib import kube # TODO go through --search_paths?
# from kadet import inventory # TODO as addict

a = {'name': __file__}

class Dummy(kadet.BaseObj):
    def new(self):
        self.need('name')

    def body(self):
        self.root.namespace = self.root.name+'_namespace'

a = {'name': __file__}

# every module requires a main() function returning a kadet.BaseObj()
def main():
    output = kadet.BaseObj()
    output.root.dummy = Dummy(name='dummy')
    return output
