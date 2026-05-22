_LOG = []
_MAX = 50


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
