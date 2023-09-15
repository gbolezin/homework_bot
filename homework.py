import logging
import os
import requests
import sys
import time
import telegram

from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import (
    PracticumTokenMissingError,
    TelegramTokenMissingError,
    ChatIDMissingError,
    IncorrectAPIAnswerError
)

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

HOMEWORK_NAME = 'gbolezin__django_testing.zip'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка токенов, необходимых для работы бота."""
    if not PRACTICUM_TOKEN:
        logger.critical('Отсутствует токен доступа в Практикум!')
        raise PracticumTokenMissingError
    if not TELEGRAM_TOKEN:
        logger.critical('Отсутствует токен доступа в Телеграм!')
        raise TelegramTokenMissingError
    if not TELEGRAM_CHAT_ID:
        logger.critical('Отсутствует ID пользователя Телеграм!')
        raise ChatIDMissingError


def send_message(bot, message):
    """Отправка сообщений в бот."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Отправлено сообщение {message} '
                      'в чат {TELEGRAM_CHAT_ID}')
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Получение ответа от API Практикума."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
    except Exception as error:
        logging.error(error)
        return None

    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка доступа к эндпойнту {ENDPOINT}. '
                      f'Статус - {response.status_code}')
        raise IncorrectAPIAnswerError
    return response.json()


def check_response(response):
    """Проверка ответа от API Практикума."""
    if type(response) != dict:
        raise TypeError(
            f'Неверный тип данных в ответе API:{type(response)}. '
            'Ожидаемый тип - <dict>'
        )
    homeworks = response.get('homeworks')
    if type(homeworks) != list:
        raise TypeError(
            f'Неверный тип данных в списке домашних работ:{type(homeworks)}. '
            'Ожидаемый тип - <list>'
        )
    homework_statuses = []
    for homework in homeworks:
        homework_statuses.append(parse_status(homework))
    return homework_statuses


def parse_status(homework):
    """Парсинг статуса домашней работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('Объект домашней работы '
                       'не содержит ключа homework_name'
                       )
    homework_status = homework.get('status')
    if (not homework_status) or (homework_status not in HOMEWORK_VERDICTS):
        raise KeyError(f'Неизвестный статус {homework_status} '
                       'домашней работы {homework_name}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            homework_statuses = check_response(get_api_answer(timestamp))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        else:
            for homework_status in homework_statuses:
                send_message(bot, homework_status)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
