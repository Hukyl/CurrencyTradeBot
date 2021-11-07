class ExceptionWithCause(Exception):
    def __init__(self, message: str, *, cause: str = None):
        super().__init__(message)
        self.cause = cause


class UserDoesNotExistError(ExceptionWithCause):
    pass


class UserAlreadyExistsError(ExceptionWithCause):
    pass


class PredictionDoesNotExistError(ExceptionWithCause):
    pass


class RateDoesNotExistError(ExceptionWithCause):
    pass


class SessionDoesNotExistError(ExceptionWithCause):
    pass


class SessionAlreadyExistsError(ExceptionWithCause):
    pass


class CurrencyDoesNotExistError(ExceptionWithCause):
    pass


class ParsingError(ExceptionWithCause):
    pass
