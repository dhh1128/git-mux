#!/usr/bin/env python

import os, sys, re, subprocess, traceback

from lib import help, engine, ui, cmd, config

def list(*args):
    show_all = False
    if args[0].lower() == 'all':
        show_all = True
        args = args[1:]
    eng = engine.get()
    which = args[0].lower()
    if 'branches'.startswith(which):
        by_branch_name = engine.get().get_branches().by_branch_name
        branch_names = sorted(by_branch_name.keys())
        for branch_name in branch_names:
            component_names = sorted(by_branch_name[branch_name])
            ui.writec(branch_name.ljust(20) + ui.NORMTXT + ' (%s)\n' % ', '.join(component_names), ui.PARAM_COLOR)
    elif 'components'.startswith(which):
        for b in eng.get_components():
            ui.writec(b['name'].ljust(20) + ui.NORMTXT + ' (%s)\n' % b['url'], ui.PARAM_COLOR)
    else:
        raise Exception('Expected "list [all] branches|components".')

def flow(*args):
    engine.get().flow(*args)

_HELP_SWITCHES = ['?','help']
def _parse_switches(args):
    bad = False
    show_help = False
    i = j = 0
    while i < len(args):
        arg = args[i]
        val = None
        if arg.startswith('--'):
            val = arg[2:]
        elif (i == 0 and arg.startswith('-')):
            val = arg[1:]
        elif (j == 0 and (arg.lower() in _HELP_SWITCHES)):
            val = arg
        if val:
            args.remove(arg)
            val = val.lower()
            if val in _HELP_SWITCHES:
                show_help = True
            elif val == 'no-color':
                ansi2.set_use_colors(False)
            elif val == 'auto-confirm':
                prompter.set_mode(prompt.AUTOCONFIRM_MODE)
            elif val == 'auto-abort':
                prompter.set_mode(prompt.AUTOABORT_MODE)
            else:
                # Normalize switch.
                args.insert(i, '--%s' % val)
                i += 1
        else:
            i += 1
        j += 1
    if show_help:
        help.show()
        sys.exit(0)
    elif bad:
        sys.exit(1)
    return args

def setup(*args):
    print('Run "python %s instead. Use --help for more info.' % os.path.join(config.BIN_FOLDER, 'setup.py'))

def dispatch(symbols, args):
    '''
    Given a bunch of symbols from the python locals() or globals() function,
    examine args and call the appropriate function. This dynamically connects
    verbs on 3po's command line to functions in the program.
    '''
    if not config.cfg.setup_has_succeeded():
        ui.eprintc('Run "sudo python %s/setup.py" first.' % config.BIN_FOLDER, ui.ERROR_COLOR)
        sys.exit(1)

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
                ui.eprintc('Unrecognized command "%s". Try "%s help" for syntax.' % (func, 'git mux help'), ui.ERROR_COLOR)
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
            ui.eprintc('%s' % traceback.format_exc(), ui.ERROR_COLOR)
            return 1

if __name__ == '__main__':
    err = 0
    symbols = locals()
    args = _parse_switches(sys.argv[1:])
    if not args:
        help.show()
    else:
        err = dispatch(symbols, args)
    sys.exit(err)
