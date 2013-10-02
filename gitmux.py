#!/usr/bin/env python

import os, sys, re, subprocess

from lib import help, engine, dispatch, constants, ui
from lib.ansi import writec, printc, eprintc, NORMTXT
from lib.colors import *

def _get_data(args, i, prompt, lst):
    if args and len(args) > i:
        return args[i]
    else:
        for x in lst:
            writec('  ' + x['name'] + '\n', PARAM_COLOR)
        return ui.prompt(prompt)        

def branches(*args):
    eng = engine.get()
    for b in eng.get_branches():
        writec(b['name'] + LINENUM_COLOR + ' (%s)\n' % b['status'], PARAM_COLOR)

def components(*args):
    eng = engine.get()
    for b in eng.get_components():
        writec(b['name'] + LINENUM_COLOR + ' (%s)\n' % b['url'], PARAM_COLOR)
        
def graft(*args):
    eng = engine.get()
    if args:
        component = args[0]
    else:
        component = _get_data(args, 0, 'Component to graft?', eng.get_components())
        if not component:
            return
    if args and len(args) > 1:
        branch = args[1]
    else:
        branch = _get_data(args, 1, 'Branch to receive %s?' % component, eng.get_branches())
        if not branch:
            return
    eng.add_component_to_branch(component, branch)
    print('Grafted %s into %s.' % (component, branch))

def flow(*args):
    eng = engine.get()
    if args:
        branch = args[0]
        args = args[1:]
    else:
        branch = _get_data(args, 0, 'Branch to flow?', eng.get_branches())
        if not branch:
            return
    if not args:
        args = ui.prompt('Args to git flow?')
        if not args:
            return
    eng.flow(branch, args)
    
def retire(*args):
    eng = engine.get()
    if args:
        branch = args[0]
        args = args[1:]
    else:
        branch = _get_data(args, 0, 'Branch to flow?', eng.get_branches())
        if not branch:
            return
    eng.retire(branch)
    printc('Retired "%s" branch.' % branch)

def revive(*args):
    eng = engine.get()
    if args:
        branch = args[0]
        args = args[1:]
    else:
        branch = _get_data(args, 0, 'Branch to flow?', eng.get_branches())
        if not branch:
            return
    eng.revive(branch)
    printc('Revived "%s" branch.' % branch)

_HELP_SWITCHES = ['?','help']
def _parse_switches(args):
    bad = False
    show_help = False
    i = j = 0
    while i < len(args):
        arg = args[i]
        # Stop parsing args after 'do' keyword in foreach ... do construct.
        if arg == 'do':
            break
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
            elif val == 'test':
                config.test_mode = True
                config.sandbox_container_folder = TEST_SANDBOXES
                prompter.set_mode(prompt.AUTOCONFIRM_MODE)
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

if __name__ == '__main__':
    err = 0
    symbols = locals()
    args = _parse_switches(sys.argv[1:])
    if not args:
        help.show()
        sys.exit(0)
    else:
        err = dispatch.dispatch(symbols, args)
    sys.exit(err)
