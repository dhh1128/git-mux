import os, subprocess, time, traceback, sys

from lib import ui, config

REQUIRED_LAYOUT_EXPLANATION = '''
This app is designed to be used with the following folder layout:

$APP_ROOT/bin   -- all the code for the app; where $MAIN_MODULE resides.
$APP_ROOT/repos -- all the repos that we'll work with.
$APP_ROOT/etc   -- config files.
'''

INSTALLATION_INSTRUCTIONS = '''
Installation instructions:

1. Make a folder named "$APP_NAME" in any convenient location. The folder
   should have the capacity to store git repos. The fully qualified
   path to this folder becomes $APP_ROOT. The path should be writable by
   your non-root user.
2. In a shell, cd to $APP_ROOT
2.   git clone $CODE_HOME_REPO bin
3.   sudo python bin/$MAIN_MODULE setup
4. Answer the prompts.
'''

_non_root_user = None
def get_non_root_user():
    global _non_root_user
    if _non_root_user is None:
        _non_root_user = do_or_die('stat -c %%U %s' % config.APP_ROOT, explanation='Need to be able to figure out non-root user.').strip()
        if _non_root_user == 'root':
            die('%s is owned by root. Needs to be owned by ordinary user.' % config.APP_ROOT)
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
    ui.eprintc(msg, ui.ERROR_COLOR)
    sys.exit(1)

def do(cmd, as_user=None):
    if as_user:
        cmd = 'runuser -l %s %s' % (as_user, cmd)
    print(cmd)
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
    ui.printc('Checking folder layout...', ui.PARAM_COLOR)
    if not config.BIN_FOLDER.endswith('/bin'):
        msg = '%s is not a valid location for $APP_ROOT/bin.\n' % config.BIN_FOLDER + \
            REQUIRED_LAYOUT_EXPLANATION + INSTALLATION_INSTRUCTIONS
        msg = msg.replace('$APP_NAME', config.APP_NAME)
        msg = msg.replace('$BIN_FOLDER', config.BIN_FOLDER)
        msg = msg.replace('$CODE_HOME_REPO', config.CODE_HOME_REPO)
        msg = msg.replace('$MAIN_MODULE', config.MAIN_MODULE)
        msg = msg.strip()
        if audit_only:
            eprintc(msg, ui.ERROR_COLOR)
            return False
        else:
            die(msg)
    else:
        print('Folder layout is correct.')
    return True

def setup_writable_app_folder(audit_only=False):
    ui.printc('Checking for writable app folder...', ui.PARAM_COLOR)
    nru = _get_non_root_user()
    tmp_path = os.path.join(APP_FOLDER, ".tmp" + str(time.time()))
    exit_code, stdout, stderr = do('touch %s' % tmp_path, as_user=nru)
    try:
        if exit_code:
            msg = '%s is not writable by %s.' % (config.APP_FOLDER, nru)
            if audit_only:
                eprintc(msg, ui.ERROR_COLOR)
                return False
            else:
                die(msg)
        else:
            print('%s is writable by %s.' % (config.APP_FOLDER, nru))
    finally:
        os.remove(tmp_path)

def setup_app_cloned(audit_only=False):
    ui.printc('Checking app to see if it was installed by cloning a git repo...', ui.PARAM_COLOR)
    if not os.path.isdir(os.path.join(config.BIN_FOLDER, '.git')):
        msg = '''
%s has not been installed with a git clone command. This will prevent it
from updating itself.
''' % config.APP_TITLE + config.INSTALLATION_INSTRUCTIONS
        if audit_only:
            eprintc(msg, ui.ERROR_COLOR)
            return False
        else:
            die(msg)
    else:
        print('%s was cloned correctly.' % config.APP_TITLE)
    return True

def setup_git(audit_only=False):
    ui.printc('Checking git...', ui.PARAM_COLOR)
    exit_code, stdout, stderr = do('git --version', as_user=get_non_root_user())
    if exit_code:
        if audit_only:
            eprintc('Git is not installed.', ui.ERROR_COLOR)
            return False
        else:
            print('Installing git.')
            do_or_die('%s install git /y' % get_installer(), 'Need git to be installed.')
            print('Try setup again, now that git is installed.')
            sys.exit(1)
    else:
        print('Git is installed.')
    return True

def setup_git_python(audit_only=False):
    ui.printc('Checking gitpython...', ui.PARAM_COLOR)
    try:
        import git as gitpython
        print('Gitpython is installed.')
    except:
        if audit_only:
            eprintc('Gitpython is not installed.', ui.ERROR_COLOR)
            return False
        else:
            print('Installing gitpython.')
            do_or_die('easy_install gitpython', explanation='Need gitpython to be installed.')
    return True

def setup_git_flow(audit_only=False):
    ui.printc('Checking git-flow...', ui.PARAM_COLOR)
    exit_code, stdout, stderr = do('which git-flow')
    if exit_code:
        if audit_only:
            eprintc('Git-flow is not installed.', ui.ERROR_COLOR)
            return False
        else:
            print('Installing git-flow.')
            installer = get_installer()
            pkg = 'gitflow'
            if installer == 'apt-get':
                pkg = 'git-flow'
            do_or_die('%s install %s /y' % (installer, pkg), explanation='Need git-flow to be installed.')
    else:
        print('Git-flow is installed.')
    return True

def run(audit_only=False):
    # Only run this as root. This is a backup check; it's also enforced
    # in gitmux.setup().
    assert os.getuid() == 0
    ui.printc('Checking user context...', ui.PARAM_COLOR)
    get_non_root_user()
    try:
        setup_git()
        setup_git_python()
        setup_git_flow()
        setup_folder_layout()
        setup_app_cloned()
        setup_writable_app_folder()
    except KeyboardInterrupt:
        eprintc('\n\nConfiguration not saved.\n', WARNING_COLOR)
        pass
    except SystemExit:
        pass
    except:
        traceback.print_exc()

if __name__ == '__main__':
    audit_only = len(sys.argv) > 1 and sys.argv[1].lower().find('audit') > -1
    run(audit_only)