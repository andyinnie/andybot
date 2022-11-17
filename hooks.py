# hooks.py
from dataclasses import dataclass

from util import core

# {
#     'member_join': [{
#         id: 'wordleserver',
#         func: () => {},
#     },]
# }


@dataclass
class Hook:
    id: str
    func: callable


def load(_):
    def register_hook(name, id, func):
        print('registering a hook rn')
        hooks = core.exports.get('hooks')
        core.exports.put_if_none('hooks', {})

        if name not in hooks().keys():
            hooks()[name] = []

        # check to see if this id exists
        for hook_obj in hooks()[name]:
            if hook_obj.id == id:
                hook_obj.func = func
                return

        # otherwise just put it in
        hooks()[name].append(Hook(id, func))
    core.exports.put('register_hook', register_hook)
    print('Exported register_hook')
