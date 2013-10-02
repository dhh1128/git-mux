import os, json, time, sys, fcntl

import constants

_DATA_REPO = 'springville:/home/dhardman/gitrepos/git-mux-data.git'
_LOCAL_DATA_REPO = os.path.join(constants.HOMEDIR, '.git-mux-data')
_PROTECTED_BRANCHES = ['master', 'develop']
_BRANCHES_FILE = 'branches.json'
_COMPONENTS_FILE = 'components.json'

try:
    import git as gitpython
except:
    eprintc('Unable to import git support module. Please run "sudo easy_install gitpython" and retry.')
    
class Engine:
    def __init__(self, folder=None):
        if folder is None:
            folder = _LOCAL_DATA_REPO
        self._folder = folder
        self._git = None
        self._branches = None
        self._components = None
        self._last_update = 0

    def _update_local_data_repo(self):
        # Don't let any other thread, or any other sibling process, interact
        # with my machine-wide data at the same time.
        with EngineLock():
            try:
                if not os.path.isdir(os.path.join(self._folder, '.git')):
                    if not os.path.isdir(self._folder):
                        os.makedirs(self._folder)
                    self._git = gitpython.Git(working_dir=self._folder)
                    self._git.clone(_DATA_REPO, '.')
                else:
                    # Don't update more than once every few secs
                    now = time.time()
                    if now - self._last_update < 10:
                        return
                    self._git = gitpython.Git(working_dir=self._folder)
                self._last_update = time.time()
                self._git.pull()
            except:
                raise Exception('Unable to pull latest 3po data into %s. %s.' % (self._folder, sys.exc_info()[1]))

    def _read_json(self, fname):
        self._update_local_data_repo()
        try:
            path = os.path.join(self._folder, fname)
            f = open(path, 'r')
            txt = f.read()
            f.close()
            return json.loads(txt)
        except:
            raise Exception('Could not parse %s. %s.' % (path, sys.exc_info()[1]))

    def get_branches(self, filter_func=None):
        if self._branches is None:
            self._branches = self._read_json(_BRANCHES_FILE)
            self._branches.sort(key=lambda x: x['name'])
        if filter_func:
            return [b for b in self._branches if filter_func(b)]
        return self._branches

    def get_components(self):
        if self._components is None:
            self._components = self._read_json(_COMPONENTS_FILE)
            self._components.sort(key=lambda x: x['name'])
        return self._components
    
    def add_component_to_branch(self, component, branch):
        _find_by_name(self.get_components(), component, 'Component')
        _find_by_name(self.get_branches(), branch, 'Branch')
        print('to do: finish stub')

    def flow(self, branch, args):
        _find_by_name(self.get_branches(), branch, 'Branch')
        print('git flow %s' % args)
        print('to do: finish stub')
        
    def _update_file(self, fname, object_for_json, msg):
        txt = json.dumps(object_for_json, indent=2, separators=(',', ': '))
        path = os.path.join(self._folder, fname)
        with open(path, 'w') as f:
            f.write(txt)
        self._git.add(path)
        self._git.commit('-m', msg)
        self._git.push()
        
    def retire(self, branch):
        which = _find_by_name(self.get_branches(), branch, 'Branch')
        if branch in [b['name'] for b in self.get_branches(lambda b: b['name'] in _PROTECTED_BRANCHES)]:
            raise Exception('Branch "%s" is protected.' % branch)
        if branch not in [b['name'] for b in self.get_branches(lambda b: b['status'] == 'active')]:
            raise Exception('Branch "%s" is not active.' % branch)
        which['status'] = 'retired'
        with EngineLock():
            self._update_file(_BRANCHES_FILE, self._branches, 'retire %s branch' % branch)
     
    def revive(self, branch):
        which = _find_by_name(self.get_branches(), branch, 'Branch')
        if branch not in [b['name'] for b in self.get_branches(lambda b: b['status'] == 'retired')]:
            raise Exception('Branch "%s" is not retired.' % branch)
        which['status'] = 'active'
        with EngineLock():
            self._update_file(_BRANCHES_FILE, self._branches, 'revive %s branch' % branch)

_engine = None
def get():
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine

def _find_by_name(lst, name, object_type):
    which = [x for x in lst if x['name'] == name]
    if not which:
        raise Exception('%s "%s" is not recognized.' % (object_type, name))
    assert len(which) == 1
    return which[0]

class _NamedSemaphore:
    # Python's multiprocess.Lock() class ought to be what we want here--
    # something that any number of processes can attempt to acquire
    # independently, but that only one process can hold at a time. However,
    # it's implemented in such a way that you can't pass a name to it,
    # which sort of defeats the whole purpose. fcntl works.
    def __init__(self, path):
        self.path = path
    def acquire(self):
        self.handle = open(self.path, 'w')
        fcntl.flock(self.handle, fcntl.LOCK_EX)
    def release(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()
    
class EngineLock:
    # Allow _NamedSemaphore to be used in python's "with" block.
    def __init__(self, path=None):
        if not path:
            path = os.path.join(constants.HOMEDIR, '.git-mux-lock')
        self.semaphore = _NamedSemaphore(path)
    def __enter__(self):
        self.semaphore.acquire()
    def __exit__(self, type, value, traceback):
        self.semaphore.release()        
    
