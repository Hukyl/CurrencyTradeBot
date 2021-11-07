from datetime import datetime

from .db import DBHandler, SessionDBHandler
from configs import settings
from utils import prettify_percent, get_default_rates, prettify_float
from utils.dt import (
    check_datetime_in_future, 
    adapt_datetime, convert_to_country_format
)
from . import exceptions


class UserBase(object):
    """
    User base class

    :attributes:
        id(int): user's id in Telegram
        is_pro(bool | datetime.datetime): has user bought the subscription
        is_active(bool): if to send the notifications
        is_staff(bool): is user staff
        rates(dict):
            iso_code(str): currencies str:
                'check_times'(str): list of times
                'percent_delta'(float): not in percent format (not 23%, 0.23)
                'value'(float): just normal
        timezone(int): utcoffset (in range (-11, 13))
        language(str): user's language
    """

    def __init__(self, user_data: dict):
        supported_fields = [
            'id', 'is_active', 'is_pro', 'is_staff',
            'to_notify_by_experts', 'rates', 'timezone', 'language'
        ]
        for k, v in user_data.items():
            if k in supported_fields:
                self.__dict__[k] = v
        if 'rates' in user_data:
            self.rates = self.normalize_rates(self.rates)

    @staticmethod
    def normalize_rates(rates: list) -> dict[str, dict[str, float]]:
        return {
            rate['iso']: { 
                'check_times': rate['check_times'],
                'percent_delta': rate['percent_delta'],
                'value': rate['value']
            }
            for rate in rates
        }

    @staticmethod
    def prettify_rates(rates: dict) -> str:
        total_str = ''
        for idx, (k, v) in enumerate(rates.items(), start=1):
            total_str += (
                    "\t{}. {}:\n\t\t▫ Процент - {}\n"
                    "\t\t▫ Время проверки - {}\n"
                ).format(
                    idx, k, 
                    prettify_percent(v.get('percent_delta')), 
                    ', '.join(v.get('check_times'))
                ).replace('\t', '    ')
        return total_str

    def __iter__(self):
        # also implements list(User), because __iter__ is used by list()
        for i in [
                self.id, self.is_active, self.is_pro, self.is_staff,
                self.to_notify_by_experts, self.rates, 
                self.timezone, self.language
                ]:
            yield i


class User(UserBase):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, user_id: int):
        if not self.__class__.exists(user_id):
            self.init_user(user_id)
        data = self.db.get_user(user_id)
        super().__init__(data)

    def update(self, **kwargs) -> None:
        """
        Update some user attributes, also in database
        type: instancemethod
        
        :keyword arguments:
            **kwargs(dict): attributes to change with corresponding values
        :raise:
            DBHandler.change_user errors
        :return: None            
        """
        self.db.change_user(self.id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        bare_user = cls.__new__(cls)
        super(cls, bare_user).__init__(data)
        return bare_user

    def get_currencies_by_check_time(self, check_time: str, /) -> dict:
        """
        Get currencies info where its check time equals some check_time
        type: instancemethod

        :positional arguments:
            check_time(str): time in '%H:%M' format
        :return:
            currencies(dict): rates dict which have `check_time` in check times
        """
        return {
            k: v for k, v in self.rates.items()
            if check_time in v.get('check_times')
        }

    @property
    def predictions(self):
        return list(self.get_predictions())

    def get_predictions(self, *, only_actual: bool = True) -> 'Prediction':
        """
        Get user's predictions
        type: instancemethod

        :keyword arguments:
            only_actual(bool)=True: to return only actual predictions
        :yield:
            prediction(Prediction): user's prediction
        """
        for pred_data in self.db.get_user_predictions(
                self.id, only_actual=only_actual
                ):
            yield Prediction.from_dict(pred_data)

    def update_rates(self, iso: str, **kwargs) -> None:
        """
        Update some rates values, also in database
        type: instancemethod

        :arguments:
            iso(str): iso of currency to change values
        :keyword arguments:
            check_times(list): list of check times in format '%H:%M'
            percent_delta(float): a percent at which to notify 
                                  (0 < `percent_delta` < 1)
            value(float): exchange rate according to `iso`-USD
        :raise:
            DBHandler.change_user_rate errors
        :return: None
        """
        self.db.change_user_rate(self.id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.id))

    def create_prediction(
            self, iso_from: str, iso_to: str, value: float, 
            up_to_date: datetime
            ) -> None:
        """
        Create a prediction by user
        type: instancemethod

        :arguments:
            iso_from(str): currency's iso from which to convert
            iso_to(str): currency's iso to which to convert
            value(str): 1 `iso_from` - `value` `iso_to`
            up_to_date(datetime.datetime): when to check the prediction
        :return: None
        :raise:
            AssertionError: if `up_to_date` is in past
            DBHandler.add_prediction errors
        """
        assert check_datetime_in_future(up_to_date)
        self.db.add_prediction(
            self.id, iso_from, iso_to, 
            value, up_to_date, is_by_experts=self.is_staff
        )

    def add_rate(self, iso: str, **kwargs) -> True:
        """
        Add some rate
        type: instancemethod

        :arguments:
            iso(str): currency's iso which to add
        :keyword arguments:
            check_times(list): list of check times in format '%H:%M'
            percent_delta(float): a percent at which to notify 
                                  (0 < `percent_delta` < 1)
            value(float): exchange rate according to `iso`-USD
        :raise:
            DBHandler.add_user_rate errors
        :return:
            success_status(bool)=True
        """
        self.db.add_user_rate(self.id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.id))
        return True

    def delete_rate(self, iso: str) -> True:
        """
        Delete a rate
        type: instancemethod

        :arguments:
            iso(str): currency's iso which to delete
        :return:
            success_status(bool)=True
        :raise:
            ValueError: if `iso` in `settings.CURRENCIES`
            KeyError: if `iso` not in user's rates
            DBHandler.delete_user_rate errors
        """
        if iso in settings.CURRENCIES:
            raise ValueError(
                f"can't delete {iso}, since it is in default currencies"
            )
        if iso not in self.rates: 
            raise KeyError(f"can't delete non-present currency {iso}")
        self.db.delete_user_rate(self.id, iso)
        del self.rates[iso]
        return True

    @classmethod
    def init_user(cls, user_id: int) -> True:
        """
        Initialize user in database
        type: classmethod

        :arguments:
            user_id(int): user's id in Telegram
        :return: None
        :raise:
            UserAlreadyExistsError: if user with `user_id` exists
        """
        if not cls.exists(user_id):
            # if user not exists, create user and all his rates
            cls.db.add_user(user_id)
            defaults = get_default_rates(*settings.CURRENCIES, to_print=False)
            for currency in settings.CURRENCIES:
                cls.db.add_user_rate(
                    user_id, currency, value=defaults.get(currency)
                )
            return True
        raise exceptions.UserAlreadyExistsError(
            f"user {user_id} already exists", cause="id"
        )

    @classmethod
    def exists(cls, user_id: int) -> bool:
        """
        Check if user with user_id exists
        type: classmethod

        :arguments:
            user_id(int): user's id in Telegram
        :return:
            exists(bool): does user exist or not
        """
        return cls.db.check_user_exists(user_id)

    @classmethod
    def get_pro_users(cls, *args, **kwargs):
        """
        Get all users who have `is_pro` not set to False
        type: classmethod

        :yield:
            user(User): some pro user
        """
        for user_data in cls.db.get_pro_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_all_users(cls, *args, **kwargs):
        """
        Get all users
        type: classmethod

        :keyword arguments:
            if_all(bool)=True: to include staff users
        :yield:
            user(User): some user
        """
        for user_data in cls.db.get_all_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_staff_users(cls, *args, **kwargs):
        """
        Get all users who have `is_staff` = True
        type: classmethod

        :yield:
            user(User): some staff user
        """
        for user_data in cls.db.get_staff_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_users_by_check_time(cls, check_time: str):
        """
        Get users which have in some of their rates check_times `check_time`
        type: classmethod

        :arguments:
            check_time(str): a time in format '%H:%M'
        :yield:
            user(User): some user referenced above
        """
        for user_data in cls.db.get_users_by_check_time(check_time):
            yield cls.from_dict(user_data)

    def init_premium(self, up_to_datetime: datetime) -> True:
        """
        Init user premium (`is_pro`),
        set all possible check times for all rates,
        add infinite experts notification count (see Session)
        type: instancemethod

        :arguments:
            up_to_datetime(datetime.datetime): datetime until user has premium
        :return:
            success_status(bool)=True
        """
        self.update(is_pro=up_to_datetime)
        for k, v in self.rates.items():
            self.update_rates(k, check_times=settings.CHECK_TIMES)
        return True

    def delete_premium(self) -> True:
        """
        Delete user premium (`is_pro`=False),
        set default check times for all rates,
        remove all additional rates,
        set default experts notification count (see Session)
        type: instancemethod
        
        :return:
            success_status(bool)=True
        """
        self.update(is_pro=0)
        try:
            Session.db.set_count(
                self.id, 
                settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
            )
        except exceptions.SessionDoesNotExistError:
            pass
        for k, v in self.rates.items():
            if k not in settings.CURRENCIES:
                self.delete_rate(k)
            else:
                self.update_rates(k, check_times=settings.DEFAULT_CHECK_TIMES)
        return True

    def init_staff(self) -> True:
        """
        Init all `init_premium` features,
        set actual predictions `is_by_experts` to True (see Prediction)

        :return:
            success_status(bool)=True
        """
        self.init_premium(True)
        self.update(is_staff=1)
        for prediction in self.get_predictions(only_actual=True):
            prediction.update(is_by_experts=1)
        return True

    def delete_staff(self) -> True:
        """
        Remove all `init_premium` features,
        set actual predictions `is_by_experts` to False (see Prediction)

        :return: 
            success_status(bool)=True
        """
        self.delete_premium()
        self.update(is_staff=0)
        for prediction in self.get_predictions(only_actual=True):
            prediction.update(is_by_experts=0)
        return True

    def __str__(self):
        return f"User(id={self.id})"

    def __repr__(self):
        return self.__str__()


class Prediction(object):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, pred_id: int):
        for k, v in self.db.get_prediction(pred_id).items():
            self.__dict__[k] = v

    @classmethod
    def from_dict(cls, pred_data: dict) -> 'Prediction':
        bare_pred = cls.__new__(cls)
        for k, v in pred_data.items():
            bare_pred.__dict__[k] = v
        return bare_pred

    def toggle_like(self, user_id: int, reaction: bool = True) -> None:
        """
        Set a reaction to a prediction by user
        type: instancemethod

        :arguments:
            user_id(int): user's id in Telegram who reacts
            reaction(bool): a reaction to a prediction
                True - like prediction
                False - dislike prediction
                None - delete any reaction
        :raise:
            DBHandler.toggle_prediction_reaction errors
        :return: None
        """
        self.db.toggle_prediction_reaction(self.id, user_id, reaction)

    def delete(self, *, force: bool = False) -> True:
        """
        Delete a prediction from database
        type: instancemethod

        :keyword arguments:
            force(bool)=False: to delete a prediction if it is verified
        :raise:
            AssertionError: if `force` is False and `is_actual` is False
        :return:
            success_status(bool)=True    
        """
        if not force:
            assert self.is_actual, "can't delete a past prediction"
        self.db.delete_prediction(self.id)
        return True

    def update(self, **kwargs) -> None:
        """
        Update prediction attributes, also in database
        type: instancemethod

        :keyword arguments:
            is_by_experts(bool): is made by expert (at least at verifying time)
            up_to_date(datetime.datetime): when will be verified
            value(float): which value was predicted
            real_value(float | None): which value was at `up_to_date`
        :raise:
            DBHandler.change_prediction errors
        :return: None 
        """
        self.db.change_prediction(self.id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    def get_closest_neighbours(self) -> dict:
        """
        Get closest unverified prediction before and next the prediction id
        type: instancemethod

        :raise:
            DBHandler.get_closest_prediction_neighbours errors
        :return:
            neighbors(dict): neighbors of the prediction
                'previous'(Prediction | None): previous prediction
                'next'(Prediction | None): next prediction
        """
        res = self.db.get_closest_prediction_neighbours(self.id)
        prev_id, next_id = res['previous'], res['next']
        return {
            'previous': Prediction(prev_id) if prev_id else None,
            'next': Prediction(next_id) if next_id else None
        }

    @property
    def is_actual(self):
        return check_datetime_in_future(self.up_to_date)

    @property
    def likes(self):
        return self.db.get_prediction_likes(self.id)

    @property
    def dislikes(self):
        return self.db.get_prediction_dislikes(self.id)

    @classmethod
    def exists(cls, pred_id: int) -> bool:
        """
        Check if prediction exists
        type: classmethod

        :arguments:
            pred_id(int): prediction's id to check
        :return:
            success_status(bool): does prediction exist or not 
        """
        return cls.db.check_prediction_exists(pred_id)

    @classmethod
    def get_experts_predictions(cls, *, only_actual: bool = False):
        """
        Get all predictions with `is_by_experts` is True
        type: classmethod

        :keyword arguments:
            only_actual(bool)=False: to include past predictions
        :yield:
            prediction(Prediction): an experts' prediction
        """
        for pred_data in cls.db.get_experts_predictions(
                only_actual=only_actual
                ):
            yield cls.from_dict(pred_data)

    @classmethod
    def get_most_liked_predictions(cls, *args, **kwargs):
        """
        type: classmethod

        :yield:
            prediction(Prediction)
        """
        for pred_data in cls.db.get_max_liked_predictions(*args, **kwargs):
            yield cls.from_dict(pred_data)

    @classmethod
    def get_unverified_predictions(cls, *args, **kwargs):
        """
        Get predictions which `up_to_date` is in past and `real_value` is None
        type: classmethod

        :yield:
            prediction(Prediction)
        """
        for pred_data in cls.db.get_unverified_predictions(*args, **kwargs):
            yield cls.from_dict(pred_data)

    @classmethod
    def get_random_prediction(cls):
        """
        type: classmethod

        :yield:
            prediction(Prediction | None)
        """
        pred_data = cls.db.get_random_prediction()
        return cls.from_dict(pred_data) if pred_data != -1 else None

    def __str__(self):
        return "Prediction(up_to={}, currencies='{}-{}', value={}{})".format(
            str(self.up_to_date), self.iso_from, self.iso_to, 
            self.value, (
                f', real value={self.real_value}' if self.real_value else ''
            )
        )

    def __repr__(self):
        return self.__str__()

    def trepr(self, user: User) -> str:
        """ Telegram repr """
        return (
            "{}-{}, {}".format(
                self.iso_from, self.iso_to, 
                convert_to_country_format(
                    adapt_datetime(self.up_to_date, user.timezone), 
                    user.language
                )
            )
        )

    def tstr(self, user: User) -> str:
        """ Telegram str """
        return (
            "Prediction\nCurrencies: {}-{}\n"
            "Up to: {}\nExchange rate: {}\n{}"
        ).format(
            self.iso_from, self.iso_to, 
            convert_to_country_format(
                adapt_datetime(self.up_to_date, user.timezone), user.language
            ), prettify_float(self.value), 
            (
                f"\nLikes: {self.likes}\nDislikes: {self.dislikes}" 
                if not self.is_by_experts else ''
            )
        )


class Session(object):
    """
    A temporary session which can be easily removed, replaced etc.

    :attributes:
        user(User): which user's the session is
        free_notifications_count(int): how many notifications can user recieve
    """
    db = SessionDBHandler(settings.DB_NAME)

    def __init__(self, user_id: int):
        self.user = User(user_id)
        if not self.__class__.exists(user_id):
            self.db.add_session(user_id)

    @classmethod
    def exists(cls, user_id: int):
        """
        Check whether session with `user_id` exists

        :arguments:
            user_id(int): user's id in Telegram
        :return:
            success_status(bool)
        """
        return cls.db.check_session_exists(user_id)

    @property
    def free_notifications_count(self):
        return self.db.fetch_count(self.user.user_id)

    def decrease_count(self) -> None:
        """
        Decrease `free_notifications_count` by 1, also in database
        
        :return: None
        """
        self.db.decrease_count(self.user.user_id)

    def set_count(self, count: int) -> None:
        """
        Set `free_notifications_count` to `count`

        :arguments:
            count(int): how many notifications user will be able to recieve
        :return: None
        """
        self.db.set_count(self.user.user_id, count)
