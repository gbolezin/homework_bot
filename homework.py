import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import IncorrectAPIAnswerError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HOMEWORK_FIELD = 'homeworks'
HOMEWORK_NAME_FIELD = 'homework_name'
HOMEWORK_STATUS_FIELD = 'status'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, '
    '%(levelname)s, '
    '%(message)s, '
    '%(name)s, '
    '%(funcName)s, '
    '%(lineno)d'
    '%(process)d '
    '%(processName)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def check_tokens():
    """Проверка токенов, необходимых для работы бота."""
    token_list = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    for token in token_list:
        if not globals()[token]:
            logger.critical(f'Аварийное завершение - '
                            f'отсутствует токен {token}')
            raise ValueError


def send_message(bot, message):
    """Отправка сообщений в бот."""
    logger.debug(f'Начинается отправка сообщения {message} '
                 f'в чат {TELEGRAM_CHAT_ID}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение {message} отправлено '
                     f'в чат {TELEGRAM_CHAT_ID}')
    except telegram.TelegramError as error:
        raise telegram.TelegramError(error)


def get_api_answer(timestamp):
    """Получение ответа от API Практикума."""
    payload = {'from_date': timestamp}
    logger.debug(f'Попытка отправки запроса к эндпойнту {ENDPOINT} '
                 f'params = {payload}')
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        logger.debug(f'Запрос к эндпойнту {ENDPOINT} состоялся, '
                     f'код ответа = {response.status_code} '
                     f'причина = {response.reason}')
    except requests.RequestException:
        raise requests.ConnectionError(
            f'Ошибка соединения эндпойнту {ENDPOINT}. '
            f'params = {payload} '
            f'Статус = {response.status_code}:{response.reason}')
    if response.status_code != HTTPStatus.OK:
        raise IncorrectAPIAnswerError(
            f'Ошибка доступа к эндпойнту {ENDPOINT}. '
            f'Статус = {response.status_code}:{response.reason}'
        )
    return response.json()


def check_response(response):
    """Проверка ответа от API Практикума."""
    logger.debug('Начинается проверка ответа от эндпойнта')
    if not isinstance(response, dict):
        raise TypeError(
            f'Неверный тип данных в ответе API:{type(response)}. '
            f'Ожидаемый тип - <dict>'
        )
    if 'current_date' not in response.keys():
        raise KeyError('В словаре response отсутствует элемент current_date')
    elif HOMEWORK_FIELD not in response.keys():
        raise KeyError('В словаре response отсутствует элемент homeworks')
    else:
        homeworks = response.get('homeworks')
        logger.debug(f'Получен список домашних работ: {homeworks}')
    if not isinstance(homeworks, list):
        raise TypeError(
            f'Неверный тип данных в списке домашних работ:{type(homeworks)}. '
            f'Ожидаемый тип - <list>'
        )
    logger.debug('Проверка ответа от эндпойнта завершена')
    return homeworks


def parse_status(homework):
    """Парсинг статуса домашней работы."""
    logger.debug('Начинается парсинг домашней работы. ')
    if HOMEWORK_NAME_FIELD not in homework:
        raise KeyError(f'Объект домашней работы '
                       f'не содержит ключа {HOMEWORK_NAME_FIELD}'
                       )
    homework_name = homework.get(HOMEWORK_NAME_FIELD)
    logger.debug(f'Парсим домашнюю работу {homework}')
    if HOMEWORK_STATUS_FIELD not in homework:
        raise KeyError(f'Объект домашней работы '
                       f'не содержит ключа {HOMEWORK_STATUS_FIELD}'
                       )
    homework_status = homework.get(HOMEWORK_STATUS_FIELD)
    if not homework_status:
        raise KeyError(f'Поле {HOMEWORK_STATUS_FIELD} не заполнено '
                       f'у домашней работы {homework_name}')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестный статус {homework_status} '
                       f'домашней работы {homework_name}. '
                       f'Ожидаются статусы - {HOMEWORK_VERDICTS}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logger.debug('Парсинг домашней работы завершен успешно')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    buffer_message = ''
    while True:
        try:
            homeworks = check_response(get_api_answer(timestamp))
            if len(homeworks) > 0:
                tg_message = parse_status(homeworks[0])
                if tg_message != buffer_message:
                    send_message(bot, tg_message)
                    buffer_message = tg_message
            else:
                logger.debug('Новых статусов домашней работы не обнаружено')
            timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
