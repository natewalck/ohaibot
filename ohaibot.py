#! python
import urllib.request
import urllib.parse
import codecs
import json
import random
import datetime
import time
import logging
import requests
import shutil
import os.path
from fake_useragent import UserAgent
import re

try:
    from config import token
except:
    print("You must create a config.py file with your bot token in it!")

logging.basicConfig(filename='ohaibot.log',
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

bot_url = 'https://api.telegram.org/bot' + token + '/'
offset_file = 'offset.txt'
update_id = 0

# Map of keywords to URLs, used for static content (non-searched)
keyword_map = { 'cantbrain': 'https://dl.dropboxusercontent.com/u/11466/meme/cantbrain.jpg',
                'fixit': 'https://dl.dropboxusercontent.com/u/11466/gifs/fixit.gif',
                'trololo': 'https://dl.dropboxusercontent.com/u/11466/meme/trolololo.jpg',
                'noideadog': 'https://dl.dropboxusercontent.com/u/11466/meme/ihavenoidea.jpg',
                'afraidtoask': 'https://dl.dropboxusercontent.com/u/11466/meme/noideaafraidtoask.jpg',
                'climbingnope': 'https://dl.dropboxusercontent.com/u/11466/meme/towerclimbing.gif',
                'nopenopenope': 'https://dl.dropboxusercontent.com/u/11466/gifs/nopenopenope.gif',
                'ketchup': 'https://dl.dropboxusercontent.com/u/11466/gifs/ketchup.gif',
                'lastf': 'https://dl.dropboxusercontent.com/u/11466/gifs/last_f.gif',
                'deadhorse': 'https://dl.dropboxusercontent.com/u/11466/gifs/beatADeadHorse.gif',
                'billandsteve': 'https://dl.dropboxusercontent.com/u/11466/gifs/billandsteve.gif',
                'duckno': 'https://dl.dropboxusercontent.com/u/11466/gifs/duckno.gif',
                'frakthis': 'https://dl.dropboxusercontent.com/u/11466/gifs/frakthisfrakthat.gif',
                'why': 'https://dl.dropboxusercontent.com/u/11466/gifs/WHY.gif',
                'sillywalknope': 'https://dl.dropboxusercontent.com/u/11466/gifs/SillyWalkNope.gif',
                'sure': 'https://dl.dropboxusercontent.com/u/11466/gifs/sure_i_tested_it.gif',
                'maxpower': 'https://dl.dropboxusercontent.com/u/11466/meme/maxpower.jpg',
                'rustled': 'https://dl.dropboxusercontent.com/u/11466/meme/jimmiesrustled.png',
                'overrustled': 'https://dl.dropboxusercontent.com/u/11466/meme/jimmiesrustledmaximum.jpg',
                'random': 'http://www.reddit.com/r/random',
                }


'''Send a text only message, useful for help, feedback and errors'''
def send_simple_message(chat_id, text):
    try:
        data = urllib.parse.urlencode({'chat_id': chat_id,
                                       'text': text})
        urllib.request.urlopen(bot_url + 'sendMessage', data.encode('utf-8'))
    except Exception as e:
        logging.critical('Something went wrong when sending simple message: ' + str(e))


''' Required for gifs, otherwise they will not be animated'''
def send_document(chat_id, file_name):
    files = {'document': open(file_name, 'rb')}
    data = {'chat_id': str(chat_id)}
    logging.info(chat_id)
    try:
        r = requests.post(bot_url + 'sendDocument', data=data, files=files)
    except:
        logging.critical('failed to upload file!')
        logging.critical(r.text)


''' For sending photos only. If gif, use send_document'''
def send_photo(chat_id, file_name):
    files = {'photo': open(file_name, 'rb')}
    data = {'chat_id': str(chat_id)}
    logging.info(chat_id)
    try:
        r = requests.post(bot_url + 'sendPhoto', data=data, files=files)
    except:
        logging.critical('failed to upload file!')
        logging.critical(r.text)


'''Images on google like to use redirects, so get the destination url to use'''
def get_redirect_url(url):
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


'''Search for an image on google. Grabs the first one, if it ends in html or php
 grab the next one in the array'''
def image_search(search_term):
    search_term = re.sub(r'\W+', '', search_term)
    url = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + search_term + "&start=0&safe=active"
    response = None
    try:
        response = requests.get(url).json()
    except:
        response = None

    if response and len(response['responseData']['results']) > 0:
        logging.info("We have %s results, yay!" % len(response['responseData']['results']) )
        for result in response['responseData']['results']:
            image_url = result['unescapedUrl']
            real_url = get_redirect_url(image_url)
            if real_url.endswith('html') or real_url.endswith('php') or real_url.endswith('htm'):
                logging.info("Could not get image url for %s" % real_url)
                continue
            else:
                return_value = real_url
                break
    else:
        logging.info("Couldn't find any results! *shrugs*")
        return_value = None

    logging.debug("return_value: %s" % return_value)
    return return_value


''' Downloads the given file url to the cache folder'''
def download_file(url):
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
            response = requests.get(url, stream=True, headers = {'User-Agent': ua.chrome } )
        except:
            resposne = None

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


def get_help(chat_id):
    return_message = 'Query Options:\n\n'
    return_message = return_message + '/get search for this' + '\n\n'
    
    return_message = return_message + 'Command Options:\n\n'
    for item in sorted(keyword_map):
        return_message = return_message + '/' + item + '\n'
    
    send_simple_message(chat_id, return_message)



def get_image(chat_id, messagetext):
    message_parts = messagetext.split(' ')
    message_parts.pop(0)
    search_terms = ' '.join(message_parts)
    image_url = image_search(search_terms)
    if image_url:
        logging.debug("Supposedly URL: %s" % image_url)
        file_name = download_file(image_url)
        if not file_name:
            logging.critical("%s does not exist" % file_name)

        logging.debug("file: %s" % file_name)
        # Try to be smart about the content type
        try:
            if file_name.endswith('gif'):
                send_document(chat_id, file_name)
            elif file_name.endswith('png') or file_name.endswith('jpg') or file_name.endswith('jpeg'):
                send_photo(chat_id, file_name)
                return True
            else:
                send_simple_message(chat_id, "I have failed to find a picture for %s." % search_terms)
            return None 
        except:
            send_simple_message(chat_id, "I have failed to find a picture for %s." % search_terms)
            return None 
    else:
        send_simple_message(chat_id, "I have failed to find a picture for %s." % search_terms)
        return None


def get_static(chat_id, messagetext):
    command = messagetext.strip('/')
    if command in keyword_map:
        file_ext = keyword_map[command].split('.')[-1]
        if file_ext in ['jpg', 'jpeg', 'png']:
            file_name = download_file(keyword_map[command])
            logging.info("Sending photo %s" % file_name)
            send_photo(chat_id, file_name)
            return True
        elif file_ext in ['gif']:
            file_name = download_file(keyword_map[command])
            logging.info("Sending gif %s" % file_name)
            send_document(chat_id, file_name)
            return True
        else:
            return_message = get_redirect_url(keyword_map[command])
            send_simple_message(chat_id, return_message)
            return True
    else:
        return None


'''All bot logic happens here and calls out to functions'''
def do_bot_stuff(update_id):
    try:
        data = urllib.parse.urlencode({'offset': format(update_id),
                                       'limit': '100', 'timeout': '60'})

        response = urllib.request.urlopen(bot_url + 'getUpdates',
                                          data.encode('utf-8'))

        reader = codecs.getreader("utf-8")
        data = json.load(reader(response))
    except Exception as e:
        logging.warning('Something went wrong when fetching update: ' + str(e))
        return update_id

    if data['ok'] == True:
        for update in data['result']:

            # take new update id
            update_id = update['update_id'] + 1
            message = update['message']

            # respond if this is a message containing text
            if 'text' in message:
                # Get text of the message
                messagetext = str(message['text'])

                # Skip anything that isn't a slash command
                if not messagetext.startswith('/'):
                    continue

                # Get chat id, which is used to send the return message
                chat_id = message['chat']['id']

                # Show help text 
                if messagetext == '/help':
                    get_help(chat_id)
                # get a image via google image search API 
                elif messagetext.startswith('/get'):
                    result = get_image(chat_id, messagetext)
                    logging.info("Got Image: %s" % result)
                # Is it a statically set item?
                else:
                    result =  get_static(chat_id, messagetext)
                    logging.info("Got Image: %s" % result)
                    continue

    return update_id


'''Main program loop, handles timing and long polling'''
def main():
    # make sure the offset file exists and contains an integer
    try:
        file = open(offset_file, 'rt')
        update_id = int(file.read())
        file.close()
    except Exception as e:
        logging.warning(offset_file + 'does not exist. Creating it now' + str(e))
        with open(offset_file, 'w') as file:
            file.write('0')
            update_id = 0
    # main program loop
    while True:
    # process updates
        newupdate_id = do_bot_stuff(update_id)

        # Write the update ID to a file and sleep 3 seconds if we processed updates
        if (newupdate_id != update_id):
            file = open(offset_file, 'wt')
            file.write(str(newupdate_id))
            file.close()
            time.sleep(3)
        else:
            # Otherwise we can wait some more during long polling if we have to.
            time.sleep(1)

        # use new update ID
        update_id = newupdate_id


if __name__ == '__main__':
    main()
