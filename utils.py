import threading


def validate_bounds(value, lower, upper):
    """
    :return: value if lower <= value <= upper
             lower if lower > value
             upper if upper < value
    """
    assert lower < upper
    value = min(value, upper)
    return max(value, lower)


def send_wrapper(f):
    def _decorated(self):
        return self.send_command(f(self))

    return _decorated


def try_to_int(value):
    """Used in combination with :func:`command_wrapper` as result_conversion argument"""
    try:
        value = int(value)
    except ValueError:
        pass
    return value


def command_wrapper(to_validate=(), result_conversion=None, command_timeout=None):
    """
    Decorator for sending commands to Tello. Allows
     * validating arguments using :func:`validate_bounds`,
     * converting the Tello response using the result_conversion function/lambda and
     * setting a command_timeout for :func:`send_command<tello.Drone.send_command>`

    :param to_validate: Check if every given argument is between bounds
    :type to_validate: tuple (tuple(names of parameters), lower bound, upper bound)
    :param result_conversion: Conversion that will be applied to the return value. Must handle exceptions
    :type result_conversion: Function to convert return value of send_command
    :param command_timeout: Passed to send_command
    """

    def _decorated(f):
        def send_command(*args, **kwargs):
            code = f.__code__
            modified_args = list(args)
            for it in to_validate:
                for name in it[0]:
                    idx = code.co_varnames.index(name)
                    validated = validate_bounds(args[idx], it[1], it[2])
                    if args[idx] != validated:
                        print(f'Modifying Argument {name} to constrain to boundaries ({args[idx]} -> {validated})')
                        modified_args[idx] = validated

            rv = args[0].send_command(f(*modified_args, **kwargs), command_timeout=command_timeout)

            if result_conversion:
                rv = result_conversion(rv)
            return rv

        return send_command

    return _decorated


class AtomicInteger:
    def __init__(self, value=0):
        self._value = value
        self._lock = threading.Lock()

    def inc(self):
        with self._lock:
            self._value += 1
            return self._value

    def dec(self):
        with self._lock:
            self._value -= 1
        return self._value

    @property
    def value(self):
        with self._lock:
            return self._value

    @value.setter
    def value(self, val):
        with self._lock:
            self._value = val
