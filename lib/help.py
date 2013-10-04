from constants import APP_CMD, APP_TITLE
from colors import CMD_COLOR, TITLE_COLOR, PARAM_COLOR, DELIM_COLOR
from ansi import printc, NORMTXT
import ui

def show():
    printc('\n' + TITLE_COLOR + 'git mux' + NORMTXT + ' [' + PARAM_COLOR
              + 'switches' + NORMTXT + '] ' + CMD_COLOR + 'action'
              + NORMTXT + ' [' + PARAM_COLOR + 'parameters' + NORMTXT + ']')

    printc('''
Possible actions and their parameters include:
''')
    menu = '  ' + ui.MENU.replace('\n', '\n  ')
    printc(menu)
    printc(
'The ' + PARAM_COLOR + 'b|c' + NORMTXT + ' notation in parameters indicates that the key word ' + PARAM_COLOR + 'branch' + NORMTXT + ''' or the key
word ''' + PARAM_COLOR + 'component' + NORMTXT + ''' (or any short form thereof) is required. Action names may also
be abbreviated to any length that remains unambiguous.

Runs in scripted mode if it receives a logically complete command line.
Otherwise, it prompts to gather parameters.

Switches include:

  '''
             + PARAM_COLOR + '--auto-abort' + NORMTXT
             + '''             - Abort any time a prompt is needed after an
                             action is invoked. This guarantees scripted
                             mode, and prevents the program from doing
                             dangerous things without confirmation. If
                             actions are launched from the menu, this flag
                             is ignored.
  '''
             + PARAM_COLOR + '--auto-confirm' + NORMTXT
             + '''           - Answer 'y' to any yes/no question after an
                             action is invoked. Like --auto-abort, this
                             guarantees scripted mode. However, it is more
                             dangerous and should not be used casually.

Examples:

    ''' + CMD_COLOR + 'git mux branch'
        + PARAM_COLOR + ' trunk coolfeature' + NORMTXT + '''
        Create a "coolfeature" branch from the latest rev of all components on trunk.

    ''' + CMD_COLOR + 'git mux retire'
        + PARAM_COLOR + ' coolfeature' + NORMTXT + '''
        Retire the "coolfeature" branch.
''')

if __name__ == '__main__':
    show()