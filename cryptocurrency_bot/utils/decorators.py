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


def private(types:list=['get', 'set'], *attributes):
    return accessControl(types, failIf=(lambda attr: attr in attributes))
 
def public(types:list=['get', 'set'], *attributes):
    return accessControl(types, failIf=(lambda attr: attr not in attributes))



def rangetest(_strict_comp:bool=True, **kargs):
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
                    if _strict_comp:
                        assert low < value < high, f"unexpected value '{value}' for argument '{argname}'"
                    else:
                        assert low <= value <= high, f"unexpected value '{value}' for argument '{argname}'"                        

                elif argname in allvars:
                    pos = allvars.index(argname)
                    if _strict_comp:
                        assert low < args[pos] < high, f"unexpected value '{args[pos]}' for argument '{argname}'"
                    else:
                        assert low <= args[pos] <=  high, f"unexpected value '{args[pos]}' for argument '{argname}'"
            return func(*args, **kwargs)
        return wrapper
    return inner
