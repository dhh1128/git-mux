import os, re, sys

# Define our colors.
def c(x,y):
    return chr(27) + '[' + str(x) + ';' + str(y) + 'm'

NORMTXT = chr(27) + '[0m'
BLACK = c(0,30)
DARK_GRAY = c(1,30)
RED = c(0,31)
BOLD_RED = c(1,31)
GREEN = c(0,32)
BOLD_GREEN = c(1,32)
YELLOW = c(0,33)
BOLD_YELLOW = c(1,33)
BLUE = c(0,34)
BOLD_BLUE = c(1,34)
PURPLE = c(0,35)
BOLD_PURPLE = c(1,35)
CYAN = c(0,36)
BOLD_CYAN = c(1,36)
LIGHT_GRAY = c(0,37)
WHITE = c(1,37)

# Don't need c() anymore; remove it from global symbols
del(c)

COLORS = [BLACK,RED,GREEN,YELLOW,BLUE,PURPLE,CYAN,LIGHT_GRAY,
DARK_GRAY,BOLD_RED,BOLD_GREEN,BOLD_YELLOW,BOLD_BLUE,BOLD_PURPLE,BOLD_CYAN,WHITE]
COLOR_NAMES = str('BLACK,RED,GREEN,YELLOW,BLUE,PURPLE,CYAN,LIGHT_GRAY,'
    + 'DARK_GRAY,BOLD_RED,BOLD_GREEN,BOLD_YELLOW,BOLD_BLUE,BOLD_PURPLE,BOLD_CYAN,WHITE').split(',')

_SEQ = chr(27) + '['
_COLOR_PAT = re.compile('(' + chr(27) + r'\[([01]);3([0-7])m).*')
_LEN_NORMTXT = len(NORMTXT)
_LEN_SEQ = len(_SEQ)

def _should_colorize(handle):
    if handle == sys.stdout:
        return sys.stdout.isatty()
    elif handle == sys.stderr:
        return sys.stderr.isatty()
    return False

def _writec(handle, txt):
    # Read text that has embedded ANSI escape sequences, and write it to the
    # specified handle, taking into account our current settings regarding
    # use of color. On platforms that support ANSI escape sequences directly,
    # this function still matters, because it turns off colorization when
    # writing to a redirected file.
    colorize = _should_colorize(handle)
    while txt:
        i = txt.find(_SEQ)
        if i == -1:
            handle.write(txt)
            break
        else:
            if i > 0:
                handle.write(txt[0:i])
                txt = txt[i:]
            if txt.startswith(NORMTXT):
                if colorize:
                    _resetc(handle)
                txt = txt[_LEN_NORMTXT:]
            else:
                m = _COLOR_PAT.match(txt)
                if m:
                    if colorize:
                        _changec(handle, m)
                    txt = txt[m.end(3)+1:]
                else:
                    handle.write(_SEQ)
                    txt = txt[_LEN_SEQ:]

# Platform-specific stuff.
if os.name == 'nt':
    from ctypes import windll, Structure, c_short, c_ushort, byref

    SHORT = c_short
    WORD = c_ushort

    class COORD(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("X", SHORT),
          ("Y", SHORT)]

    class SMALL_RECT(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("Left", SHORT),
          ("Top", SHORT),
          ("Right", SHORT),
          ("Bottom", SHORT)]

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
          ("dwSize", COORD),
          ("dwCursorPosition", COORD),
          ("wAttributes", WORD),
          ("srWindow", SMALL_RECT),
          ("dwMaximumWindowSize", COORD)]

    # winbase.h
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # On Windows, we need to write to a python-style handle, but call the OS
    # with a numeric pseudo-file-handle to modify console tributes. On other
    # platforms, the second handle is unnecessary. However, to keep our code
    # uniform, create a class that encapsulates this complexity.
    class _Handle:
        def __init__(self, file, console):
            self.file = file
            self.console = console
        def write(self, txt):
            self.file.write(txt)

    _STDOUT = _Handle(sys.stdout, windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE))
    _STDERR = _Handle(sys.stderr, windll.kernel32.GetStdHandle(STD_ERROR_HANDLE))

    # Don't need our constants anymore; remove from namespace.
    del(STD_OUTPUT_HANDLE)
    del(STD_ERROR_HANDLE)

    # wincon.h
    _FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

    def _get_text_attr(handle):
        """Returns the character attributes (colors) of the console screen
        buffer."""
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        windll.kernel32.GetConsoleScreenBufferInfo(handle.console, byref(csbi))
        return csbi.wAttributes

    _NORMTXT_ATTRIBUTES = _get_text_attr(_STDOUT)

    def _set_text_attr(handle, color):
        """Sets the character attributes (colors) of the console screen
        buffer. Color is a combination of foreground and background color,
        foreground and background intensity."""
        windll.kernel32.SetConsoleTextAttribute(handle.console, color)

    # Convert from ANSI color constants to Windows color constants.
    def _mapc(color):
        if color == 1:
            return 4
        if color == 6:
            return 3
        if color == 3:
            return 6
        if color == 4:
            return 1
        return color

    # Change the active color for a handle.
    def _changec(handle, m):
        attr = _mapc(int(m.group(3)))
        if m.group(2) == '1':
            attr |= _FOREGROUND_INTENSITY
        _set_text_attr(handle, attr)

    def _resetc(handle):
        _set_text_attr(handle, _NORMTXT_ATTRIBUTES)

else:
    _STDOUT = sys.stdout
    _STDERR = sys.stderr

    def _changec(handle, m):
        handle.write(m.group(1))

    def _resetc(handle):
        handle.write(NORMTXT)

def cwrap(txt, begin_color, end_color = NORMTXT, handle=_STDOUT):
    # Wrap text in a begin color and end color, if colors are active.
    if _should_colorize(handle):
        if begin_color:
            txt = begin_color + txt
        if begin_color and (end_color and end_color != begin_color):
            txt = txt + end_color
    return txt

def writec(txt, begin_color = None, end_color = NORMTXT):
    # Write text to stdout that contains embedded ANSI escape sequences.
    # If begin_color is set, wrap the text in that color and immediately
    # revert to the end color when finished..
    txt = cwrap(txt, begin_color, end_color)
    _writec(_STDOUT, txt)

def ewritec(txt, begin_color = None, end_color = NORMTXT):
    # Write text to stderr that contains embedded ANSI escape sequences.
    # If begin_color is set, wrap the text in that color and immediately
    # revert to the end color when finished..
    txt = cwrap(txt, begin_color, end_color, _STDERR)
    _writec(_STDERR, txt)

def printc(txt, begin_color = None, end_color = NORMTXT):
    # Print line to stdout that contains embedded ANSI escape sequences.
    # If begin_color is set, wrap the text in that color and immediately
    # revert to the end color when finished..
    txt = cwrap(txt, begin_color, end_color)
    writec(txt + '\n')

def eprintc(txt, begin_color = None, end_color = NORMTXT):
    # Print line to stderr that contains embedded ANSI escape sequences.
    # If begin_color is set, wrap the text in that color and immediately
    # revert to the end color when finished..
    txt = cwrap(txt, begin_color, end_color, _STDERR)
    ewritec(txt + '\n')

