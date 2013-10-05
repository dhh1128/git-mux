'''
Provide the ability to configure the app.
'''

import os, ConfigParser, sys

APP_TITLE = 'Git Muxer'
APP_NAME = 'git-mux'
MAIN_MODULE = os.path.split(sys.argv[0])[1]
APP_VERSION = '1.0'

CODE_HOME_REPO = 'git@github.com:dhh1128/git-mux.git'
SHARED_CFG_REPO_NAME = 'shared-cfg'
BIN_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')).replace('\\', '/')

# Verify that this code is running from an environment that
# matches our assumptions...
if BIN_FOLDER.endswith('/'):
    BIN_FOLDER = BIN_FOLDER[0:-1]

GMUX_ROOT = os.path.abspath(os.path.join(BIN_FOLDER, '..')).replace('\\', '/')
if GMUX_ROOT.endswith('/'):
    GMUX_ROOT = GMUX_ROOT[0:-1]

CONFIG_FOLDER = os.path.join(GMUX_ROOT, 'etc')
CONFIG_FNAME = '%s.cfg' % APP_NAME
SHARED_CONFIG_FNAME = 'shared.cfg'
CONFIG_FQPATH = os.path.join(CONFIG_FOLDER, CONFIG_FNAME)

CYGWIN = False
if os.name == 'nt':
    HOMEDIR = os.path.join(os.getenv("HOMEDRIVE"), os.getenv("HOMEPATH"))
else:
    HOMEDIR = os.path.abspath(os.getenv("HOME"))
if HOMEDIR.find('cygwin') > -1:
    HOMEDIR = os.getenv("USERPROFILE")
    CYGWIN = True

class MyConfigParser(ConfigParser.SafeConfigParser):
    def __init__(self, path=None):
        ConfigParser.SafeConfigParser.__init__(self)
        if not path:
            path = CONFIG_FQPATH
        self.path = path
        if os.path.isfile(self.path):
            self.read(self.path)
    def add_section_if_missing(self, section):
        if not self.has_section(section):
            self.add_section(section)
    def set_all(self, section, key, value):
        self.add_section_if_missing(section)
        self.set(section, key, value)
    def save(self):
        with open(self.path, 'w') as f:
            self.write(f)
    def try_get(self, section, key, default=None):
        if self.has_option(section, key):
            return self.get(section, key)
        return default

cfg = MyConfigParser()