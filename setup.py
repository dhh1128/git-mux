import os, subprocess, time, traceback, sys, re, ConfigParser

from lib import ui, config

REQUIRED_LAYOUT_EXPLANATION = '''
This app is designed to be used with the following folder layout:

$GMUX_ROOT/bin   -- all the code for the app; where $MAIN_MODULE resides.
$GMUX_ROOT/repos -- all the repos that we'll work with.
$GMUX_ROOT/etc   -- config files.
'''

INSTALLATION_INSTRUCTIONS = '''
Installation instructions:

1. Make a folder named "$APP_NAME" in any convenient location. The folder
   should have the capacity to store git repos. The fully qualified
   path to this folder becomes $GMUX_ROOT. The path should be writable by
   your non-root user.
2. In a shell, cd to $GMUX_ROOT
2.   git clone $CODE_HOME_REPO bin
3.   sudo python bin/setup.py
4. Answer the prompts.
'''

def report_step(step):
    ui.printc('\n%s...' % step, ui.STEP_COLOR)

def complain(problem):
    ui.eprintc(problem, ui.ERROR_COLOR)
    return 1 # return an exit code that implies an error

_owner = None
def check_ownership(report=False):
    # This function can be called indirectly (when running as root and needing
    # to figure out who our non-root user ought to be). Or it can be called
    # explicitly, when auditing setup. We only want to report it as a discrete
    # step when we're auditing. Complicating this, we may call the function several
    # times in a single run of the program, and we need to have different return
    # values depending on our modes. Sorry to be messy.
    global _owner
    if _owner is None:
        if report:
            report_step('owner of %s' % config.GMUX_ROOT)
        _owner = do_or_die('stat -c %%U %s' % config.GMUX_ROOT, explanation='Need to check owner of GMUX_ROOT.').strip()
        if report:
            if _non_root_user == 'root':
                die('%s is owned by root instead of ordinary user' % config.GMUX_ROOT)
            else:
                print('%s is owned by %s, as it should be' % (config.GMUX_ROOT, _owner))
                return 0
    return _owner

_non_root_user = None
def get_non_root_user():
    global _non_root_user
    if _non_root_user is None:
        if os.getegid() == 0:
            report_step('identify non-root user')
            _non_root_user = check_ownership()
            if _non_root_user == 'root':
                die('%s is owned by root instead of ordinary user.' % config.GMUX_ROOT)
        else:
            import getpass
            _non_root_user = getpass.getuser()
    return _non_root_user

_installer = None
def get_installer():
    global _installer
    if _installer is None:
        exit_code, stdout, stderr = do('which yum')
        if exit_code:
            do_or_die('which apt-get')
            _installer = 'apt-get'
        else:
            _installer = 'yum'
    return _installer

def die(msg):
    complain(msg)
    sys.exit(1)

def do(cmd, as_user=None):
    if as_user:
        if os.getegid() == 0:
            cmd = 'su %s -c "%s"' % (as_user, cmd.replace('"', '\\"'))
    ui.printc(cmd, ui.SUBTLE_COLOR)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr

def do_or_die(cmd, as_user=None, explanation=None):
    x = as_user
    exit_code, stdout, stderr = do(cmd, as_user=x)
    if exit_code:
        if not stderr:
            stderr = stdout
        if explanation:
            stderr = explanation.strip() + '\n\n' + stderr
        die(stderr)
    return stdout

def setup_folder_layout(audit_only=False):
    report_step('folder layout')
    if not config.BIN_FOLDER.endswith('/bin'):
        msg = '%s is not a valid location for $GMUX_ROOT/bin.\n' % config.BIN_FOLDER + \
            REQUIRED_LAYOUT_EXPLANATION + INSTALLATION_INSTRUCTIONS
        msg = msg.replace('$APP_NAME', config.APP_NAME)
        msg = msg.replace('$BIN_FOLDER', config.BIN_FOLDER)
        msg = msg.replace('$CODE_HOME_REPO', config.CODE_HOME_REPO)
        msg = msg.replace('$MAIN_MODULE', config.MAIN_MODULE)
        msg = msg.strip()
        if audit_only:
            return complain(msg)
        die(msg)
    else:
        print('layout is correct')
    return 0

def setup_app_cloned(audit_only=False):
    report_step('app is git clone')
    if not os.path.isdir(os.path.join(config.BIN_FOLDER, '.git')):
        msg = '''
%s has not been installed with a git clone command. This will prevent it
from updating itself.
''' % config.APP_NAME + config.INSTALLATION_INSTRUCTIONS
        if audit_only:
            return complain(msg)
        die(msg)
    else:
        print('%s was cloned correctly' % config.APP_NAME)
    return 0

def setup_git(audit_only=False):
    report_step('git')
    exit_code, stdout, stderr = do('git --version', as_user=get_non_root_user())
    if exit_code:
        if audit_only:
            return complain('git is not installed')
        print('installing git.')
        do_or_die('%s -y install git' % get_installer(), 'Need git to be installed.')
        print('Try setup again, now that git is installed.')
        sys.exit(1)
    else:
        print('git is installed')
    return 0

def setup_git_python(audit_only=False):
    report_step('gitpython')
    try:
        import git as gitpython
        print('gitpython is installed.')
    except:
        if audit_only:
            return complain('gitpython is not installed')
        print('installing gitpython')
        do_or_die('easy_install gitpython', explanation='Need gitpython to be installed.')
    return 0

def setup_git_flow(audit_only=False):
    report_step('git-flow')
    exit_code, stdout, stderr = do('which git-flow')
    if exit_code:
        if audit_only:
            return complain('git-flow is not installed')
        print('installing git-flow')
        installer = get_installer()
        pkg = 'gitflow'
        if installer == 'apt-get':
            pkg = 'git-flow'
        do_or_die('%s -y install %s' % (installer, pkg), explanation='Need git-flow to be installed.')
    else:
        print('git-flow is installed')
    return 0

def get_shared_cfg_repo_from_code_repo(code_repo):
    return code_repo[0:code_repo.rfind('/') + 1] + '%s-shared-cfg.git' % config.APP_NAME

_code_remote = None
def get_code_remote():
    global _code_remote
    if _code_remote is None:
        with WorkingDir(config.BIN_FOLDER):
            remotes = do_or_die('git remote -v', as_user=get_non_root_user()).strip().split('\n')
            _code_remote = re.split('\s+', remotes[0])[1]
    return _code_remote

def remote_to_local(repo):
    local = repo[repo.rfind('/') + 1:]
    if local.endswith('.git'):
        local = local[0:-4]
    return local

def define_branches():
    report_step('define branches')
    print('''Large software engineering teams may have many active branches, but only a few
may be interesting to any given branch maintainer. By default, %s will operate
on master, develop, and any git-flow branches that you create on this machine.
It doesn't pull down extra branches unless you say to do so, because this
wastes disk space and slows down maintenance. However, if you'd like to manage
branches that someone created elsewhere, just add them here. For example:

  feature/fancy-dashboard, hotfix/acme-corp -- adds 2 branches of interest.

You may also use the keyword "all" to manage all git-flow style branches, or
"mine" for just ones you create in the future.
''' % config.APP_NAME)
    cfg = config.cfg
    SECTION = 'muxed branches'
    KEY = 'selected'
    muxed_branches = cfg.try_get(SECTION, KEY, 'mine')
    while True:
        # Prompt. Then apply various filters and see if user gave us anything usable.
        selected = ui.prompt('Branches to manage -- "mine", "all", or list?', default=muxed_branches)
        if selected:
            selected = [x.strip() for x in selected.split(',')]
            selected = [x for x in selected if x not in ['master', 'develop']]
            if selected:
                non_gitflow = [x for x in selected if x.find('/') == -1 and x != 'mine' and x != 'all']
                if non_gitflow:
                    ui.eprintc('Only git-flow branches are muxable; %s not supported.' % ', '.join(non_gitflow), ui.ERROR_COLOR)
                else:
                    break

    if 'all' in selected:
        selected = 'all'
    elif 'mine' in selected and len(selected) == 1:
        selected = 'mine'
    cfg.set_all(SECTION, KEY, selected)

def define_components(nru):
    report_step('define components')
    try_initial_fetch = False

    # Figure out where data ought to reside, remotely and locally.
    data_folder = os.path.join(config.GMUX_ROOT, 'data')
    default_shared_cfg_repo = get_shared_cfg_repo_from_code_repo(get_code_remote())

    cfg = config.cfg
    SECTION = 'misc'
    KEY = 'shared cfg repo'
    shared_cfg_repo = cfg.try_get(SECTION, KEY, default_shared_cfg_repo)
    local_shared_cfg_folder = os.path.join(data_folder, config.SHARED_CFG_REPO_NAME)

    if not os.path.isdir(data_folder):
        do_or_die('mkdir -p %s' % data_folder, as_user=nru)

    repeat = True
    while repeat:
        repeat = False
        shared_cfg_repo = ui.prompt('Repo where components are defined, or "none"?', default=shared_cfg_repo)
        cfg.set_all('misc', 'shared cfg repo', shared_cfg_repo)
        if shared_cfg_repo.lower() != 'none':
            if os.path.isdir(os.path.join(local_shared_cfg_folder, '.git')):
                with WorkingDir(local_shared_cfg_folder):
                    do_or_die('git pull', as_user=nru)
            else:
                # Can't clone into a non-empty folder. Make sure we don't have
                # that case.
                if os.path.isdir(local_shared_cfg_folder):
                    if os.listdir(local_shared_cfg_folder):
                        die('%s is not empty; unsafe to store git clone. Clean out and retry.' % local_shared_cfg_folder)
                    os.rmdir(local_shared_cfg_folder)

                with WorkingDir(data_folder):
                    exit_code, stdout, stderr = do('git clone %s %s' % (shared_cfg_repo, config.SHARED_CFG_REPO_NAME), as_user=nru)
                    if exit_code:
                        stderr = re.sub('\n{2,}', '\n', stderr.strip())
                        ui.eprintc('Unable to clone %s.\n%s' % (shared_cfg_repo, stderr), ui.ERROR_COLOR)
                        repeat = True

    # Now ask the user which components they want to work with.
    muxed = ''
    SECTION = 'muxed components'
    if cfg.has_section(SECTION):
        muxed_items = cfg.items(SECTION)
        if muxed_items:
            muxed = ', '.join([pair[0] for pair in muxed_items])
    else:
        muxed_items = []

    defined = muxed
    defined_items = []
    if shared_cfg_repo:
        components_file = os.path.join(local_shared_cfg_folder, config.SHARED_CONFIG_FNAME)
        if os.path.isfile(components_file):
            cfg2 = ConfigParser.SafeConfigParser()
            cfg2.read(components_file)
            SECTION2 = 'defined components'
            if cfg2.has_section(SECTION2):
                defined_items = cfg2.items(SECTION2)
            if defined_items:
                defined += ', '.join([pair[0] for pair in defined_items])
    defined_names = [x[0] for x in defined_items]

    if defined:
        print('\nThe following components are defined:')
        for item in defined_items:
            ui.printc('  ' + ui.PARAM_COLOR + item[0] + ui.NORMTXT + ' = ' + item[1])
    else:
        print('\nNo components are defined.')

    if muxed:
        sys.stdout.write('\nThe following components are currently muxed:\n  ')
        ui.printc(', '.join([item[0] for item in muxed_items]), ui.PARAM_COLOR)
    else:
        print('\nNo components are currently muxed.')
        # If they haven't yet chosen any list, assume they'll want to pick everything.
        muxed = defined
    print('''
In ordinary use, %s muxes (or multiplexes) commands across a set of
components (git repos) to make branch management consistent and easy when
pieces of a stack or suite need the same feature/hotfix/release branch. The
list of muxed components governs the scope of operations. You can edit the
names in the component list, and define new components by adding items
in the form "name=url".
''' % config.APP_NAME)

    selected = []
    while True:
        selected = [x.strip() for x in ui.prompt('List of components to mux?', default=muxed).split(',')]
        unrecognized = [x.strip() for x in selected if x.find('=') == -1 and x not in defined_names]
        if unrecognized:
            ui.eprintc('Unrecognized components: %s' % ', '.join(unrecognized), ui.ERROR_COLOR)
        else:
            if selected:
                for item in selected:
                    pair = None
                    i = item.find('=')
                    if i > -1:
                        pair = item[0:i].rstrip(), item[i+1:].lstrip()
                    else:
                        for x in defined_items:
                            if x[0] == item:
                                pair = x
                                break
                    assert(pair)
                    cfg.set_all(SECTION, pair[0], pair[1])
                break
            else:
                ui.eprintc('You must define some components to mux across.', ui.ERROR_COLOR)

def check_components():
    report_step('check components')
    try:
        items = config.cfg.items('muxed components')
        if items:
            print('muxing on %s' % ', '.join([x[0] for x in items]))
            return 0
    except:
        pass
    return complain('components for muxing are undefined')

def setup_path(audit_only=False):
    report_step('%s is in path' % config.APP_NAME)
    if audit_only:
        # Right now I can't figure out how to test the path of the non-root user.
        # Every experiment I attempt fails. I've tried os.setuid(), su <user> -c which,
        # runuser, etc...
        if os.getegid() != 0:
            do_or_die('which %s' % config.APP_NAME)
    else:
        # We unconditionally remove any old symlink that's laying around,
        # to guarantee that every time we run setup, we end up with the
        # current version of the program being the one that will subsequently
        # run.
        symlink = '/usr/local/bin/%s' % config.APP_NAME
        if os.path.isfile(symlink):
            os.remove(symlink)
        do_or_die('ln -s %s/%s %s' % (config.BIN_FOLDER, config.APP_NAME, symlink))
    print('path checks out')
    return 0

class WorkingDir:
    '''
    A class that changes directory for the duration of a Python "with" statement.
    '''
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.restore_path = os.getcwd()
    def __enter__(self):
        os.chdir(self.path)
        return self
    def __exit__(self, type, value, traceback):
        os.chdir(self.restore_path)

def update_app(nru):
    report_step('check for out-of-date %s' % config.APP_NAME)
    import git as gitpython
    git = gitpython.Git(config.BIN_FOLDER)
    stdout = git.status()
    # See if we have changed the app locally.
    if stdout.find('nothing to commit') == -1:
        ui.eprintc('Reminder: you have uncommitted local changes to %s.' % config.APP_NAME, ui.WARNING_COLOR)
    else:
        if stdout.find('ahead of origin') > -1:
            ui.eprintc('Reminder: you have changes to %s that need to be pushed.' % config.APP_NAME, ui.WARNING_COLOR)
        # Safe to pull. Can't use "git pull" here because we're running as root and
        # we want to pull as normal user.
        with WorkingDir(config.BIN_FOLDER):
            exit_code, stdout, stderr = do('git pull', as_user=nru)
            if stdout.find('lready up-to-date') == -1:
                print(stdout)
                die('%s was out of date; re-run setup with new version.' % config.APP_NAME)
    print('no remote changes to worry about')

def run(audit_only=False):
    exit_code = 0
    try:
        # Check basic prerequisites, and fix them if appropriate.

        # Verify correct security context.
        as_root = os.getegid() == 0
        if as_root:
            # This call will cause us to exit if we have problems.
            nru = get_non_root_user()
        else:
            if audit_only:
                exit_code += check_ownership(report=True)
            else:
                die('Must run setup as root user.')

        exit_code += setup_git(audit_only)

        # Only check gitpython and git-flow if git's working.
        if not exit_code:
            exit_code += setup_git_python(audit_only)
            exit_code += setup_git_flow(audit_only)

        exit_code += setup_folder_layout(audit_only)
        exit_code += setup_app_cloned(audit_only)
        exit_code += setup_path(audit_only)

        if audit_only:
            exit_code += check_components()
        else:

            # We need to do the rest of the setup as the unprivileged user
            # instead of as root. But we need to have a config file that's
            # owned by the non-root user.
            if not os.path.isdir(config.CONFIG_FOLDER):
                do_or_die('mkdir -p %s' % config.CONFIG_FOLDER, as_user=nru)
            if not os.path.isfile(config.CONFIG_FQPATH):
                do_or_die('touch %s' % config.CONFIG_FQPATH, as_user=nru)

            update_app(nru)
            define_components(nru)
            define_branches()
            config.cfg.save()

        # Summarize what happened.
        operation = 'Setup'
        if audit_only:
            operation = 'Setup audit'
        if exit_code:
            ui.eprintc('\n%s failed.\n' % operation, ui.ERROR_COLOR)
        else:
            ui.eprintc('\n%s succeeded.\n' % operation, ui.SUCCESS_COLOR)

        return exit_code

    except KeyboardInterrupt:
        ui.eprintc('\nSetup interrupted.\n', ui.ERROR_COLOR)
        pass
    except SystemExit:
        pass
    except:
        traceback.print_exc()

if __name__ == '__main__':
    show_help = False
    audit = False
    if len(sys.argv) > 2:
        show_help = True
    else:
        if len(sys.argv) == 2:
            if sys.argv[1].lower().find('audit') > -1:
                audit = True
            else:
                show_help = True

    # Take care of "help" mode inline.
    if show_help:
        print('''
sudo python setup.py   -- run setup
python setup.py audit  -- verify that setup is correct
''')
        sys.exit(0)

    sys.exit(run(audit_only=audit))