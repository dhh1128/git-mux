import os, re, sys

_x = os.path.dirname(os.path.abspath(__file__))
APP_FOLDER = os.path.abspath(os.path.join(_x, '..'))
del(_x)

APP_FNAME = 'gitmux.py'
APP_PATH = os.path.join(APP_FOLDER, APP_FNAME)
APP_CMD = os.path.splitext(APP_FNAME)[0]
APP_TITLE = 'git muxer'
FQPYTHON = sys.executable
if FQPYTHON.find(' ') > -1:
    FQPYTHON = '"%s"' % FQPYTHON
APP_INVOKE = '%s "%s"' % (FQPYTHON, APP_PATH)
APP_VERSION = '2.0'

if os.name == 'nt':
    EOL = '\r\n'
else:
    EOL = '\n'
    # On RHEL and CentOS, we need to invoke 3po differently in the scheduler,
    # due to the way the environment is configured when cron runs.
    import platform
    x = platform.uname()
    if x[0] == 'Linux' and x[2].find('.el') > -1:
        APP_INVOKE = 'bash -l "%s"' % APP_PATH[0:-3]

INDENT = '    '

if os.name == 'nt':
    HOMEDIR = os.path.join(os.getenv("HOMEDRIVE"), os.getenv("HOMEPATH"))
else:
    HOMEDIR = os.path.abspath(os.getenv("HOME"))
if HOMEDIR.find('cygwin') > -1:
    HOMEDIR = os.getenv("USERPROFILE")
    CYGWIN = True

STRING_TYPE = type('')
LIST_TYPE = type([])
BOOL_TYPE = type(True)
