#! python
'''Bot for telegram'''
import telebot
import urllib.request
import urllib.parse
import json
import time
import logging
import requests
import os.path
from fake_useragent import UserAgent
import re
import giphypop

logging.basicConfig(filename='ohaibot.log',
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

def load_config():
    '''Load config file'''
    try:
        with open('ohaibot.json', 'r') as infile:
            config = json.load(infile)
    except:
        print("Failed to load config. Check your Syntax!")
        exit(1)

    return config

# Must do this stuff after load_config so we actually can run it ;)
config = load_config()
bot = telebot.AsyncTeleBot(config['bot_token'])
keyword_map = config['keywordmap']


def save_config(new_config):
    '''Save config file, return i if successful'''
    try:
        with open('ohaibot.json', 'w') as outfile:
            json.dump(new_config, outfile)
        result = True
    except:
        print("Failed to save config, using old config")
        result = False

    return result

def get_redirect_url(url):
    '''Images on google like to use redirects, so get the destination url to use'''
    try:
        response = requests.get(url)
        actual_url = response.url
    except:
        logging.info("Couldn't get URL")
        actual_url = url

    # Lets try to clean the URL up as well by removing all but netloc and path
    url_object = urllib.parse.urlparse(actual_url)
    url = url_object.scheme + "://" + url_object.netloc + url_object.path

    return url


def image_search(search_term):
    '''Search for an image on google. Grabs the first one, if it ends in html or php
    grab the next one in the array'''
    search_term = re.sub(r'\W+', '', search_term)
    url = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + \
        search_term + "&start=0&safe=active"
    response = None
    search_results = []
    try:
        response = requests.get(url).json()
    except:
        response = None

    if response and len(response['responseData']['results']) > 0:
        logging.info("We have %s results, yay!" %
            len(response['responseData']['results']))

        for result in response['responseData']['results']:
            image_url = result['unescapedUrl']
            real_url = get_redirect_url(image_url)
            if real_url.endswith('html') or \
                real_url.endswith('php') or \
                real_url.endswith('htm'):
                logging.info("Could not get image url for %s" % real_url)
                continue
            else:
                search_results.append(real_url)
    else:
        logging.info("Couldn't find any results! *shrugs*")

    logging.debug("Returning %s results" % len(search_results))

    return search_results


def save_keyword(message):
    '''Add a custom keyword that maps to a URL'''
    try:
        keyword, url = message.text.split(' ')[1:]
    except:
        logging.info("Invalid command!")
        keyword = None

    if keyword:
        logging.info("Key: %s Value: %s" % (keyword, url))
        config['keywordmap'][keyword] = url
        if save_config(config):
            logging.info("Config saved")
        else:
            bot.send_message(message.chat.id, "Failed to save config")
        keyword_map = config['keywordmap']
        return keyword
    else:
        logging.info("Invalid command, could not save it")
        return keyword


def download_file(url, name=None):
    ''' Downloads the given file url to the cache folder'''
    if name:
        file_name = name
    else:
        file_name = url.split('/')[-1]

    ua = UserAgent()
    # todo create cache folder if it does not already exist.
    cache_folder = 'cache'
    if os.path.isfile(os.path.join(cache_folder, file_name)):
        logging.info('File already exists, skipping download')
        return os.path.join(cache_folder, file_name)
    else:
        logging.info("Downloading %s" % url)
        response = None
        try:
            response = requests.get(
                url, stream=True, headers = {'User-Agent': ua.chrome }
            )
        except:
            response = None

        fail = False
        try:
            if response.status_code == 200:
                with open(os.path.join('cache', file_name), 'wb') as out_file:
                    for chunk in response.iter_content(1024):
                        out_file.write(chunk)
                    else:
                        logging.critical("Couldn't download %s" % file_name)
        except:
            fail = True
        del response
        if not fail:
            file_path = os.path.join(cache_folder, file_name)
            logging.info("Downloaded %s" % file_path)
            return file_path
        else:
            return None

@bot.message_handler(commands=['help'])
def get_help(message):
    '''This function should always return the help text'''
    return_message = 'Query Options:\n\n'
    return_message = return_message + '/get search for this' + '\n'
    return_message = return_message + '/add keyword url' + '\n\n'

    return_message = return_message + 'Command Options:\n\n'
    for item in sorted(keyword_map):
        return_message = return_message + '/' + item + '\n'

    bot.reply_to(message, return_message)

@bot.message_handler(commands=list(keyword_map.keys()))
def static_command(message):
    '''This handles all the static commands'''
    get_static(message)

@bot.message_handler(commands=['get', 'image'])
def google_image_search(message):
    '''Do a google image search and send it to chat'''
    result, term = get_image(message)
    if result:
        logging.info("Got Image: %s" % result)
    else:
        return_message = "Couldn't find image for %s" % term
        bot.send_message(message.chat.id, return_message)

@bot.message_handler(commands=['add'])
def add_keyword_to_config(message):
    '''Add a static command to the config (like /ketchup)'''
    logging.debug("Adding a keyword")
    result = save_keyword(message)
    if result:
        bot.send_message(message.chat.id, "Saved Keyword %s" % result)
    else:
        # todo: Berate them for doing it wrong
        bot.send_message(
            message.chat.id, """Failed to save keyword, you are
                             probably doing it wrong""")

@bot.message_handler(commands=['gif', 'getgif'])
def giphy_search(message):
    '''Search giphy for a gif and post it to chat'''
    file_name, term = get_gif(message)
    if file_name:
        logging.info("Got gif: %s" % file_name)
        bot.send_document(message.chat.id, open(file_name, 'rb'))
    else:
        bot.send_message(message.chat.id, "Couldn't find gif for %s" % term)


def get_gif(message):
    giphy = giphypop.Giphy()
    message_parts = message.text.split(' ')
    message_parts.pop(0)
    search_terms = ' '.join(message_parts)
    try:
        giphy_results = [x for x in giphy.search(search_terms)]
        real_url = get_redirect_url(giphy_results[0].media_url)
        gif_name =  "{}.gif".format(giphy_results[0].id)
        result = download_file(real_url, gif_name )
    except:
        result = None

    return result, search_terms


def get_image(message):
    '''Gets and sends an image based on message text'''
    message_parts = message.text.split(' ')
    message_parts.pop(0)
    search_terms = ' '.join(message_parts)
    search_results = image_search(search_terms)
    image_sent = False
    if search_results:
        for image_url in search_results:
            # break out of this loop if an image is successfully sent
            if image_sent:
                logging.info(
                    "Already sent an image, skip the rest of the results"
                )
                break

            logging.debug("Supposedly URL: %s" % image_url)
            file_name = download_file(image_url)
            if not file_name:
                logging.critical("%s does not exist" % file_name)
                continue

            logging.debug("file: %s" % file_name)
            # Try to be smart about the content type
            try:
                if file_name.endswith('gif'):
                    bot.send_document(message.chat.id, open(file_name, 'rb'))
                    image_sent = True
                elif file_name.endswith('png') or \
                    file_name.endswith('jpg') or \
                    file_name.endswith('jpeg'):
                    bot.send_photo(message.chat.id, open(file_name, 'rb'))
                    image_sent = True
                else:
                    image_sent = False
            except:
                image_sent = False
    else:
        image_sent = False

    return image_sent, search_terms


def get_static(message):
    command = message.text.strip('/')
    if command in keyword_map:
        file_ext = keyword_map[command].split('.')[-1]
        if file_ext in ['jpg', 'jpeg', 'png']:
            file_name = download_file(keyword_map[command])
            logging.info("Sending photo %s" % file_name)
            bot.send_photo(message.chat.id, open(file_name, 'rb'))
            return True
        elif file_ext in ['gif']:
            file_name = download_file(keyword_map[command])
            logging.info("Sending gif %s" % file_name)
            bot.send_document(message.chat.id, open(file_name, 'rb'))
            return True
        else:
            return_message = get_redirect_url(keyword_map[command])
            bot.send_message(message.chat.id, return_message)
            return True
    else:
        return None


def main():
    '''Main program loop, handles timing and long polling'''
    bot.polling()

    # main program loop
    while True:
        time.sleep(100)

if __name__ == '__main__':
    main()
