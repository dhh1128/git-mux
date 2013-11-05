from ui import *

def show():
    printc('\n' + TITLE_COLOR + 'git mux action'
              + NORMTXT + ' [' + PARAM_COLOR + 'parameters' + NORMTXT + ']')

    printc('''
Possible actions and their parameters include:
''')
    menu = '  ' + MENU.replace('\n', '\n  ')
    printc(menu)
    printc(
'The ' + PARAM_COLOR + 'b|c' + NORMTXT + ' notation in parameters indicates that the key word ' + PARAM_COLOR + 'branch' + NORMTXT + ''' or the key
word ''' + PARAM_COLOR + 'component' + NORMTXT + ''' (or any short form thereof) is required. Action names may also
be abbreviated to any length that remains unambiguous.

Runs in scripted mode if it receives a logically complete command line.
Otherwise, it prompts to gather parameters.

Examples:

    ''' + CMD_COLOR + 'git mux flow feature '
        + PARAM_COLOR + ' coolfeature ' + CMD_COLOR + 'start' + NORMTXT + '''
        Create a "coolfeature" branch from the latest rev of all components on trunk.

    ''' + CMD_COLOR + 'git mux flow feature '
        + PARAM_COLOR + ' coolfeature' + CMD_COLOR + 'finish' + NORMTXT + '''
        Retire the "coolfeature" branch.
''')

if __name__ == '__main__':
    show()