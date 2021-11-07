def accessControl(type_, failIf):
    def onDecorator(aClass):
        class onInstance:
            def __init__(self, *args, **kargs):
                self.__wrapped = aClass(*args, **kargs)

            def __getattr__(self, attr):
                if failIf(attr) and 'get' in type_:
                    raise TypeError('private attribute fetch: ' + attr)
                else:
                    return getattr(self.__wrapped, attr)

            def __setattr__(self, attr, value):
                if attr == '_onInstance__wrapped':
                    self.__dict__[attr] = value
                elif failIf(attr) and 'set' in type_:
                    raise TypeError('private attribute change: ' + attr)
                else:
                    setattr(self.__wrapped, attr, value)
        return onInstance
    return onDecorator


def private(types=None, *attributes):
    if types is None:
        types = ['get', 'set']
    return accessControl(types, failIf=(lambda attr: attr in attributes))


def public(types=None, *attributes):
    if types is None:
        types = ['get', 'set']
    return accessControl(types, failIf=(lambda attr: attr not in attributes))


def rangetest(strict_range: bool = True, **kargs):
    """
    Test if argument in range of values, otherwise AssertionError

    uasge:
    @rangetest(arg=(0, 1))
    def f(arg):
        pass
    """
    privates = kargs

    def inner(func):
        code = func.__code__
        allargs = code.co_varnames[:code.co_argcount]

        def wrapper(*args, **kwargs):
            allvars = allargs[:len(args)]

            for argname, (low, high) in privates.items():
                if argname in kwargs:
                    value = kwargs.get(argname)
                    if strict_range:
                        assert low < value < high, \
                            "unexpected value '{}' for argument '{}'".format(
                                value, argname
                            )
                    else:
                        assert low <= value <= high, \
                            "unexpected value '{}' for argument '{}'".format(
                                value, argname
                            )                        

                elif argname in allvars:
                    pos = allvars.index(argname)
                    if strict_range:
                        assert low < args[pos] < high, \
                            "unexpected value '{}' for argument '{}'".format(
                                args[pos], argname
                            )
                    else:
                        assert low <= args[pos] <= high, \
                            "unexpected value '{}' for argument '{}'".format(
                                args[pos], argname
                            )
            return func(*args, **kwargs)
        return wrapper
    return inner
