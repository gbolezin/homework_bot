class PracticumTokenMissingError(Exception):
    """Исключение об отсутстви токена доступа к Практикум."""

    pass


class TelegramTokenMissingError(Exception):
    """Исключение об отсутстви токена доступа к Телеграм."""

    pass


class ChatIDMissingError(Exception):
    """Исключение об отсутстви ID пользователя Телеграм."""

    pass


class IncorrectAPIAnswerError(Exception):
    """Исключение о неверном ответе сервиса API."""

    pass
