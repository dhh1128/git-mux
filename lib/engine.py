import os, time, sys, fcntl, re, inspect

import config, ui

_LOCAL_DATA_REPO = os.path.join(config.DATA_FOLDER, '.git-mux-data')
_REPO_ROOT = config.DATA_FOLDER
_PROTECTED_BRANCHES = ['master', 'develop']
_COMPONENTS_FILE = 'components.json'
_SUPPRESS_GITFLOW_LINE_PAT = re.compile(r'^ +(init|version|support|git flow [a-z]+ (publish|track|checkout)) +.*?\n', re.MULTILINE)
_VALID_BRANCH_TYPES_PAT = re.compile('^(?:feature|release|hotfix)$')
_VALID_BRANCH_NAMES_PAT = re.compile('[a-z]+(?:[-a-z]*[a-z])?$')
_SCRATCH_BRANCH_NAME = 'scratch'

def die(problem):
    ui.eprintc(problem, ui.ERROR_COLOR)
    sys.exit(1)

try:
    import git as gitpython
except:
    die('Unable to import git support module. Please run "sudo easy_install gitpython" and retry.')

class Engine:

    def __init__(self, folder=None):
        if folder is None:
            folder = _LOCAL_DATA_REPO
        self._folder = folder
        self._git = None
        self._branches = None
        self._components = None
        self._last_update = 0

    def _find_component_by_name(self, name):
        which = [x for x in self.get_components() if x['name'] == name]
        if not which:
            raise Exception('Component "%s" is not recognized.' % (object_type, name))
        assert len(which) == 1
        return which[0]

    # Define a class that holds branches indexed 2 ways -- by branch name,
    # and by the name of the component that has the branch.
    class Branches:
        def __init__(self):
            self.by_component_name = {}
            self.by_branch_name = {}
        def add(self, branch_name, component_name):
            if component_name not in self.by_component_name:
                self.by_component_name[component_name] = []
            self.by_component_name[component_name].append(branch_name)
            if branch_name not in self.by_branch_name:
                self.by_branch_name[branch_name] = []
            self.by_branch_name[branch_name].append(component_name)

    def get_branches(self, filter_func=None):
        if self._branches is None:

            b = Engine.Branches()
            for c in self.get_components():
                component_name = c['name']
                git = self._get_git_instance_for_component(c['name'])
                stdout = git.branch()
                items = [x.strip() for x in stdout.strip().split('\n')]
                scratch_found = False
                for item in items:
                    if item.startswith('*'):
                        item = item[1:].lstrip()
                    if item == _SCRATCH_BRANCH_NAME:
                        scratch_found = True
                    else:
                        b.add(item, component_name)
                # As a precaution, we create a local branch named "scratch"
                # in our git-mux-cache version of each component. This branch
                # has no remote and is not based on anything. We leave
                # this as the active branch after all our operations, in
                # case our code misbehaves or someone accidentally issues a
                # direct git command without carefully setting up context.
                if not scratch_found:
                    git.branch(_SCRATCH_BRANCH_NAME)
                git.checkout(_SCRATCH_BRANCH_NAME)

            self._branches = b

        return self._branches

    def get_components(self):
        if self._components is None:
            c = []
            for i in config.cfg.items(config.MUXED_COMPONENTS_SECTION):
                c.append({'name': i[0], 'url': i[1]})
            c.sort(key=lambda x: x['name'])
            self._components = c
            print('Engine._components = %s' % str(self._components))
        return self._components

    def add_component_to_branch(self, component, branch):
        _find_by_name(self.get_components(), component, 'Component')
        _find_by_name(self.get_branches(), branch, 'Branch')
        print('to do: finish stub')

    def _get_git_instance_for_component(self, component_name):
        path = os.path.join(_REPO_ROOT, component_name)
        if not os.path.isdir(path):
            # Lookup component by component_name in our internal table.
            component = self._find_component_by_name(component_name)
            os.makedirs(path)
            sys.stderr.write('Fetching %s repo to %s for the first time...\n' % (component_name, path))
            git = gitpython.Git(path)
            git.clone(component['url'], '.')
            sys.stderr.write('Calling git flow init...\n')
            git.flow('init', '-d')
            # git flow assumes you'll have only local copies of feature
            # branches. We want to link ours to what's on the remote...
            remote_branches = [x.strip() for x in git.branch('-a').strip().split('\n')]
            remote_branches = [x[15:] for x in remote_branches if x.startswith('remotes/origin/') and '/' in x]
            remote_branches = [x for x in remote_branches if _VALID_BRANCH_TYPES_PAT.match(x[0:x.find('/')])]
            for rb in remote_branches:
                sys.stderr.write('Checking out remote branch %s...\n' % rb)
                git.checkout('-b', rb, 'origin/%s' % rb)

            git.branch(_SCRATCH_BRANCH_NAME)
        else:
            sys.stderr.write('Using %s in %s.\n' % (component_name, path))
            git = gitpython.Git(path)
        return git

    def _flow_list(self, state, component_name, git, *args):
        exit_code, stdout, stderr = git.flow(*args, with_extended_output=True, with_exceptions=False)
        return exit_code, stdout, stderr

    def _flow_start(self, state, component_name, git, *args):
        named_args, branch_type, branch_name, full_branch_name = _parse_flow_args(*args)

        if state.i == 0:
            if not _VALID_BRANCH_NAMES_PAT.match(branch_name):
                raise Exception('Branch names must consist entirely of lower-case letters and hyphens; "%s" is invalid.' % branch_name)
            state.components_with_branch = self.get_branches().by_branch_name.get(full_branch_name)
            if not state.components_with_branch:
                state.components_with_branch = []

        if component_name in state.components_with_branch:
            exit_code, stdout, stderr = None, 'Branch %s already started.' % full_branch_name, None
        else:
            exit_code, stdout, stderr = git.flow(*args, with_extended_output=True, with_exceptions=False)
            if not exit_code:
                stdout = 'Branch %s started.' % full_branch_name
                self.get_branches().add(full_branch_name, component_name)

        # Make sure remote repo has this same branch. (This command does approximately
        # the same thing as "git flow feature publish"; I'm using it because I got it
        # working this way after some experimentation, and don't want to fiddle anymore.
        # However, Git's syntax for this command changed from 1.7 to 1.8, and I'm using
        # the newer variant, so there is some possibility that we'll want to use
        # git flow's publish command instead: git.flow(branch_type, 'publish', branch_name).
        # If we do that, we should probably only do it when branches are created --
        # whereas the current impl is idempotent and can therefore repair disconnected
        # local branches.
        git.push('--set-upstream', 'origin', full_branch_name)

        return exit_code, stdout, stderr

    def _prep_for_existing_branch(self, state, *args):
        # Map args to "git flow" into variables. Remember them.
        state.named_args, state.branch_type, state.branch_name, state.full_branch_name = _parse_flow_args(*args)

        # Validate some input.
        branches = self.get_branches()
        if not state.full_branch_name in branches.by_branch_name:
            raise Exception('Branch "%s" is not recognized.' % ste.full_branch_name)

        # See which components use this branch.
        if state.i == 0:
            state.components_with_branch = branches.by_branch_name.get(state.full_branch_name)
            if not state.components_with_branch:
                state.components_with_branch = []

    def _flow_finish(self, state, component_name, git, *args):
        self._prep_for_existing_branch(state, *args)

        if component_name in state.components_with_branch:
            # Switch to the correct branch and run git flow's finish.
            git.checkout(state.full_branch_name)
            exit_code, stdout, stderr = git.flow(*args, with_extended_output=True, with_exceptions=False)
            if not exit_code:
                stdout = 'Branch %s finished.' % state.full_branch_name
                # At this point, we've merged the feature branch into local's copy of "develop",
                # and we've deleted the feature branch locally. We now need to delete the remote
                # version as well, and then push local develop to remote.
                # Git's quirky way to delete a remote branch is to push <nothing> (the empty string)
                # to the branch you want to delete on origin...
                git.push('origin', ':%s' % state.full_branch_name)
                git.push() # Active branch = "develop"; push that as well.
            return exit_code, stdout, stderr
        else:
            return None, None, None

    def _flow_pull(self, state, component_name, git, *args):
        # The git-flow pull command takes slightly different syntax than the others; it wants a
        # git remote before the named branch. To accommodate that but still use our
        # normal parsing logic, we have to do a little fiddling.
        args = list(args)
        named_args = [arg for arg in args if not arg.startswith('-')]
        if len(named_args) != 4:
            die('Expected "git mux flow <branch_type> pull [-r] <remote> <branchname>". Do you want the "origin" remote?')
        else:
            remote = named_args[2]
            args.remove(remote)
        self._prep_for_existing_branch(state, *args)

        if component_name in state.components_with_branch:
            git.checkout(state.full_branch_name)
            args.insert(2, remote)
            exit_code, stdout, stderr = git.flow(*args, with_extended_output=True)
            return exit_code, stdout, stderr

    def _flow_push(self, state, component_name, git, *args):
        named_args = [arg for arg in args if not arg.startswith('-')]
        if len(named_args) != 3:
            die('Expected "git mux flow <branch_type> push <branchname>". Push is always to origin.')

        self._prep_for_existing_branch(state, *args)

        if component_name in state.components_with_branch:
            git.checkout(state.full_branch_name)
            exit_code, stdout, stderr = git.push(with_extended_output=True)
            return exit_code, stdout, stderr

    def _flow_rebase(self, state, component_name, git, *args):
        self._prep_for_existing_branch(state, *args)

        if component_name in state.components_with_branch:
            git.checkout(state.full_branch_name)
            exit_code, stdout, stderr = git.flow(*args, with_extended_output=True)
            return exit_code, stdout, stderr

    def _flow_diff(self, state, component_name, git, *args):
        self._prep_for_existing_branch(state, *args)

        if component_name in state.components_with_branch:
            git.checkout(state.full_branch_name)
            exit_code, stdout, stderr = git.flow(*args, with_extended_output=True)
            return exit_code, stdout, stderr

    def _flow_help(self, *args):
        git = gitpython.Git()
        x = git.flow(*args, as_process=True)
        stdout, stderr = x.proc.communicate()
        # A few gitflow operations are not supported.
        stdout = _SUPPRESS_GITFLOW_LINE_PAT.sub('', stdout)
        # Tell users to call git flow through git mux.
        stdout = stdout.replace('git flow', 'git mux flow')
        # We don't allow usage where the branch name is omitted and
        # the active branch is implied. We also disallow just branch
        # prefixes. This is a safety precaution; when muxing, that's
        # important.
        stdout = stdout.replace('[<name|nameprefix>]', '<name>')
        # On the "pull" operation, we require name as well.
        stdout = stdout.replace('[<name>]', '<name>')
        print(stdout)

    def flow(self, *args):

        if not args:
            args = ['help']

        if args[-1] == 'help':
            self._flow_help(*args)
            return

        first = args[0]
        if first == 'version':
            print('unknown')
            return
        elif first == 'init':
            die("Can't mux an init across components; init is inherently a single-component operation.")
        else:
            if not _VALID_BRANCH_TYPES_PAT.match(first):
                die("Can't handle \"%s\" branches right now." % first)
            verb = args[1]
            try:
                func = getattr(self, '_flow_' + verb)
            except:
                die(ui.CMD_COLOR + 'git mux flow ' + first + ' ' + ui.PARAM_COLOR + verb + ui.ERROR_COLOR + ' is an invalid command.' + ui.NORMTXT)

            class State:
                def __init__(self):
                    self.i = 0

            state = State()
            for c in self.get_components():
                component_name = c['name']
                line_width = 30 - len(component_name)
                ui.printc('\n' + ui.PARAM_COLOR + component_name + ui.DELIM_COLOR + ' ' + '-'*line_width + ui.NORMTXT)
                git = self._get_git_instance_for_component(component_name)
                try:
                    result = func(state, component_name, git, *args)
                    if result:
                        exit_code, stdout, stderr = result
                        if exit_code:
                            if not stderr:
                                stderr = 'git flow command failed'
                            ui.eprintc(stderr, ui.ERROR_COLOR)
                        elif stdout:
                            print(stdout)
                    state.i += 1
                finally:
                    # For safety, always reset to scratch branch.
                    git.checkout(_SCRATCH_BRANCH_NAME)

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
            die('Branch "%s" is protected.' % branch)
        if branch not in [b['name'] for b in self.get_branches(lambda b: b['status'] == 'active')]:
            die('Branch "%s" is not active.' % branch)
        which['status'] = 'retired'
        with EngineLock():
            self._update_file(_BRANCHES_FILE, self._branches, 'retire %s branch' % branch)

    def revive(self, branch):
        which = _find_by_name(self.get_branches(), branch, 'Branch')
        if branch not in [b['name'] for b in self.get_branches(lambda b: b['status'] == 'retired')]:
            die('Branch "%s" is not retired.' % branch)
        which['status'] = 'active'
        with EngineLock():
            self._update_file(_BRANCHES_FILE, self._branches, 'revive %s branch' % branch)

    def refresh(self):
        which = _find_by_name(self.get_branches(), branch, 'Branch')
        if branch not in [b['name'] for b in self.get_branches(lambda b: b['status'] == 'retired')]:
            die('Branch "%s" is not retired.' % branch)
        which['status'] = 'active'
        with EngineLock():
            self._update_file(_BRANCHES_FILE, self._branches, 'revive %s branch' % branch)

def _parse_flow_args(*args):
    named_args = [arg for arg in args if not arg.startswith('-')]
    branch_type = named_args[0]
    # Require an explicitly named branch.
    branch_name = named_args[2]
    full_branch_name = '%s/%s' % (branch_type, branch_name)
    return named_args, branch_type, branch_name, full_branch_name

_engine = None
def get():
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine

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
        time.sleep(0.1)
        os.remove(self.path)

class EngineLock:
    # Allow _NamedSemaphore to be used in python's "with" block.
    def __init__(self, path=None):
        if not path:
            path = os.path.join(config.HOMEDIR, '.git-mux-lock')
        self.semaphore = _NamedSemaphore(path)
    def __enter__(self):
        self.semaphore.acquire()
    def __exit__(self, type, value, traceback):
        self.semaphore.release()

