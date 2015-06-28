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

try:
    from config import token
except:
    print("You must create a config.py file with your bot token in it!")

logging.basicConfig(filename='ohaibot.log',
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)

bot_url = 'https://api.telegram.org/bot' + token + '/'
offset_file = 'offset.txt'
update_id = 0
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


def send_simple_message(chat_id, text):
    try:
        data = urllib.parse.urlencode({'chat_id': chat_id,
                                       'text': text})
        urllib.request.urlopen(bot_url + 'sendMessage', data.encode('utf-8'))
    except Exception as e:
        logging.warning('Something went wrong when sending: ' + str(e))
        return


def send_document(chat_id, file_name):
    files = {'document': open(file_name, 'rb')}
    data = {'chat_id': str(chat_id)}
    logging.info(chat_id)
    try:
        r = requests.post(bot_url + 'sendDocument', data=data, files=files)
    except:
        logging.warning('failed to upload file!')
        logging.warning(r.text)


def send_photo(chat_id, file_name):
    files = {'photo': open(file_name, 'rb')}
    data = {'chat_id': str(chat_id)}
    logging.info(chat_id)
    try:
        r = requests.post(bot_url + 'sendPhoto', data=data, files=files)
    except:
        logging.warning('failed to upload file!')
        logging.warning(r.text)


def get_redirect_url(url):
    request = requests.get(url)
    return request.url


def download_file(url):
    file_name = url.split('/')[-1]
    cache_folder = 'cache'
    logging.info("File to download is %s" % file_name)
    if os.path.isfile(os.path.join(cache_folder, file_name)):
        logging.info('File already exists, skipping download')
        return os.path.join(cache_folder, file_name)
    else:
        logging.info("Downloading %s" % file_name)
        try:
            response = requests.get(url, stream=True)
            with open(os.path.join('cache', file_name), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
            return os.path.join(cache_folder, file_name)
        except:
            logging.warning("Failed to download %s" % file_name)
            return None


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
                messagetext = str(message['text'])

                # Skip anything that isn't a slash command
                if not messagetext.startswith('/'):
                    continue

                chat_id = message['chat']['id']

                if messagetext == '/help':
                    return_message = 'Command Options:\n\n'
                    for item in sorted(keyword_map):
                        return_message = return_message + '/' + item + '\n'

                    send_simple_message(chat_id, return_message)

                command = messagetext.strip('/')
                if command in keyword_map:
                    file_ext = keyword_map[command].split('.')[-1]
                    if file_ext in ['jpg', 'jpeg', 'png']:
                        file_name = download_file(keyword_map[command])
                        logging.info("Sending photo %s" % file_name)
                        send_photo(chat_id, file_name)
                    elif file_ext in ['gif']:
                        file_name = download_file(keyword_map[command])
                        logging.info("Sending gif %s" % file_name)
                        send_document(chat_id, file_name)
                    else:
                        return_message = get_redirect_url(keyword_map[command])
                        send_simple_message(chat_id, return_message)
                else:
                    continue

    return update_id


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
