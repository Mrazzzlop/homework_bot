
import logging
import os
import time
from dotenv import load_dotenv
import telegram
import requests

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


def check_tokens():
    """Checks the availability of variables."""
    ENV_VARS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(ENV_VARS)


def send_message(bot, message):
    """Sending a message."""
    logging.debug('Send message')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        is_message_sent = True
        logging.debug('Message sent successfully')
    except Exception as e:
        logging.error(f'Error sending message: {e}')
        is_message_sent = False
    bot.is_message_sent = is_message_sent
    return is_message_sent


def get_api_answer(timestamp):
    """The API Request."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, params=params, headers=HEADERS)
        response.raise_for_status()
        if response.status_code != 200:
            logging.error('http error.')
            raise requests.exceptions.HTTPError('http error')
    except requests.exceptions.HTTPError:
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f'error during request: {e}')
        raise Exception('error during request')
    return response.json()


def check_response(response):
    """Checking the response and forming a list."""
    if type(response) is not dict:
        logging.error('Data type error')
        raise TypeError('Data type error')
    if 'homeworks' not in response or 'current_date' not in response:
        logging.error('Error value')
        raise ValueError('Error value')
    homework_list = response.get('homeworks')
    if type(homework_list) is not list:
        logging.error('Homework is not a list')
        raise TypeError('Data type error')
    return homework_list


def parse_status(homework):
    """Parses homework statuses from the API response."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Missing necessary homework indormation')
    homework_name = homework['homework_name']
    status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError(f'Unknow homework status: {status}')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Unknow homework status: {status}')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """The main logic of the bot."""
    if not check_tokens():
        logging.critical('No tokens')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp=int(time.time()))
            check_response(response)
            homeworks = response['homeworks']
            if not homeworks:
                logging.debug('Статус не изменился')
                continue
            else:
                for homework in homeworks:
                    send_message(bot, parse_status(homework))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
