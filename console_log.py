_LOG = []
_MAX = 50
_LAST_EXCEPTION = []
_LAST_EXCEPTION_MAX = 8


def setup():
    """No-op — sys.stdout is read-only in CircuitPython. Use log() explicitly."""
    pass


def log(msg):
    """Print msg to serial and buffer it for the WebUI /console endpoint."""
    s = str(msg)
    print(s)
    if s:
        _LOG.append(s[:120])
        if len(_LOG) > _MAX:
            del _LOG[0]


def get_lines():
    return list(_LOG)


def clear():
    del _LOG[:]


def add_exception(context, err):
    entry = "{}: {}".format(context, str(err))[:160]
    _LAST_EXCEPTION.append(entry)
    if len(_LAST_EXCEPTION) > _LAST_EXCEPTION_MAX:
        del _LAST_EXCEPTION[0]
    log("ERR " + entry)


def get_last_exception():
    return list(_LAST_EXCEPTION)
