'''
Provide the ability to configure the app.
'''

import os, ConfigParser, sys

APP_TITLE = 'Git Muxer'
APP_NAME = 'git-mux'
MAIN_MODULE = os.path.split(sys.argv[0])[1]
APP_VERSION = '1.0'

CODE_HOME_REPO = 'git@github.com:dhh1128/git-mux.git'
print(os.path.abspath(sys.argv[0]))
print(__file__)
print(os.path.abspath(__file__))
BIN_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')).replace('\\', '/')

# Verify that this code is running from an environment that
# matches our assumptions...
if BIN_FOLDER.endswith('/'):
    BIN_FOLDER = BIN_FOLDER[0:-1]

APP_ROOT = os.path.abspath(os.path.join(BIN_FOLDER, '..')).replace('\\', '/')
if APP_ROOT.endswith('/'):
    APP_ROOT = APP_ROOT[0:-1]

CONFIG_FOLDER = os.path.join(APP_ROOT, 'etc')
CONFIG_FNAME = '%s.cfg' % APP_NAME
CONFIG_FQPATH = os.path.join(CONFIG_FOLDER, CONFIG_FNAME)

CYGWIN = False
if os.name == 'nt':
    HOMEDIR = os.path.join(os.getenv("HOMEDRIVE"), os.getenv("HOMEPATH"))
else:
    HOMEDIR = os.path.abspath(os.getenv("HOME"))
if HOMEDIR.find('cygwin') > -1:
    HOMEDIR = os.getenv("USERPROFILE")
    CYGWIN = True

config = ConfigParser.SafeConfigParser()
if os.path.isfile(CONFIG_FQPATH):
    config.read(CONFIG_FQPATH)