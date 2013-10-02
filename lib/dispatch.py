import cmd
import error
from constants import *
from ansi import *
from colors import *

def dispatch(symbols, args):
    '''
    Given a bunch of symbols from the python locals() or globals() function,
    examine args and call the appropriate function. This dynamically connects
    verbs on 3po's command line to functions in the program.
    '''
    funcs = []
    for x in args[0].split(','):
        this_cmd = cmd.find_command(x)
        if this_cmd:
            funcs.append(this_cmd.verb)
        else:
            funcs.append(x)
    args = args[1:]
    if args:
        if args[0].startswith('lambda'):
            args[0] = eval(args[0])
    for func in funcs:
        # Look up the named function in our symbols and invoke it,
        # if found. Otherwise, display interactive menu.
        try:
            if func in symbols:
                err = symbols[func](*args)
                if err is None:
                    err = 0
                if err:
                    return err
            else:
                eprintc('Unrecognized command "%s". Try "%s help" for syntax.' % (func, APP_CMD), ERROR_COLOR)
                return 1
        except KeyboardInterrupt:
            # Allow CTRL+C to kill loop
            print('')
            break
        except SystemExit:
            # If one of the functions that we call invokes sys.exit(), accept
            # that function's judgment without comment.
            raise
        except Exception:
            # Generally, trap all other errors and report them.
            error.write()
            return 1
