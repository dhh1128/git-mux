class Command:
    def __init__(self, syntax, descrip, tags=''):
        self.syntax = syntax
        self.descrip = descrip
        self.tags = tags.split(' ')
        i = syntax.find(' ')
        if i >= 1:
            self.verb = syntax[0:i]
        else:
            self.verb = self.syntax
        self.abbrev = self.verb
    def __str__(self):
        return self.verb

_CMDS = [
    Command('list [all] b|c',        'List muxed (or all) branches/components.'),
    Command('flow type action name', 'Run git flow on my components.'),
    ]

def _calc_abbrevs():
    global _CMDS
    # Figure out the shortest unique name for each command.
    for cmd in _CMDS:
        # How many chars does this command have in common with any others?
        max_common_char_count = 0
        others = [x for x in _CMDS if x != cmd]
        for other in others:
            common_char_count = 0
            # Which verb is shorter? We only have to compare that many chars...
            end = min(len(cmd.verb), len(other.verb))
            for k in range(end):
                if cmd.verb[k] != other.verb[k]:
                    #print('%s and %s have %d letters in common' % (verb, otherVerb, common_char_count))
                    break
                common_char_count += 1
            if max_common_char_count < common_char_count:
                max_common_char_count = common_char_count
        abbrev = cmd.verb[0:max_common_char_count+1]
        #print("%s = %s" % (verb, abbrev))
        cmd.abbrev = abbrev

_abbrevs_calculated = False

def commands():
    '''
    Return a list of all 3po Command objects.
    '''
    global _CMDS
    if not _abbrevs_calculated:
        _calc_abbrevs()
    return _CMDS

def find_command(partial_name):
    '''
    Given a possibly abbreviated name for a command, return the corresponding
    Command object.
    '''
    partial_name = partial_name.lower()
    for cmd in commands():
        # The easy algorithm is to just find the first (and only) command that
        # has an abbrev that's a subset of partial_name. However, this can give
        # false positives. Suppose user types "startle" (a word that's not a
        # true 3po command) and cmd.abbrev is "sta" (derived from "start")...
        if partial_name.startswith(cmd.abbrev):
            if cmd.verb.startswith(partial_name):
                return cmd
    return None

