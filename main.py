# -*- coding: UTF-8 -*-
import math
import json
import urllib2
import time
from urllib import urlencode
from datetime import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import vk_auth


dt = datetime.now()
d = dt.strftime("%a, %d %b %Y %I:%M:%S") + ' +0000'

# данные авторизации
VK_USER_EMAIL = 'buslaevka@gmail.com'
VK_USER_SECRET = '898b5a72c3cdc'
VK_APP_ID = '4671925'


def call_api(method, params, token):
    if isinstance(params, list):
        params_list = [kv for kv in params]
    elif isinstance(params, dict):
        params_list = params.items()
    else:
        params_list = [params]
    params_list.append(("access_token", token))
    url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params_list))
    return json.loads(urllib2.urlopen(url).read())['response']


def latest_news():
    global post_author
    token, user_id = vk_auth.auth(
        VK_USER_EMAIL, VK_USER_SECRET,
        VK_APP_ID, 'friends,offline,wall,photos')
    res = call_api('newsfeed.get', [
        ('start_time', int(time.time() - 7 * 24 * 60 * 60)),  # получаем за последние 7 дней
        ('filters', 'post')], token)

    _news = []

    # разбираем всё что получили
    for item in res['items']:
        # тип новости
        # print(item['type'])
        # post — новые записи со стен
        # photo — новые фотографии
        # photo_tag — новые отметки на фотографиях
        # wall_photo — новые фотографии на стенах
        # friend — новые друзья
        # note — новые заметки

        # source_id - идентификатор источника новости
        # положительный — новость пользователя, отрицательный — новость группы
        if item['source_id'] < 0:
            source_id = math.trunc(math.fabs(item['source_id']))
            for g in res['groups']:
                if g['gid'] == source_id:
                    # название источника
                    post_author = g['name']
                    break
        else:
            source_id = item['source_id']
            for p in res['profiles']:
                if p['gid'] == source_id:
                    # название источника
                    post_author = p['name']
                    break

        # время публикации новости
        post_date = datetime.fromtimestamp(item['date']).strftime("%a, %d %b %Y %H:%M:%S") + ' +0000'

        # находится в записях со стен и содержит текст записи
        post_text = item['text']

        post_images = ''
        if item['type'] == 'post' and 'attachments' in item:
            # содержит массив объектов, которые прикреплены к текущей новости (фотография, ссылка и т.п.)
            for a in item['attachments']:
                if a['type'] == 'photo':
                    post_images += '<img src="' + str(a['photo']['src_big']) + '" alt="">'

        # ссылка на пост
        post_link = 'https://vk.com/feed?w=wall' + str(item['source_id']) + '_' + str(item['post_id'])

        _news.append({
            'author': post_author,
            'date': post_date,
            'text': post_text,
            'link': post_link,
            'images': post_images
        })

    return _news


# получаем новости и формуируем ответ
def get():
    text = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"'
    text += '\n\t xmlns:content="http://purl.org/rss/1.0/modules/content/"'
    text += '\n\t xmlns:wfw="http://wellformedweb.org/CommentAPI/"'
    text += '\n\t xmlns:dc="http://purl.org/dc/elements/1.1/"'
    text += '\n\t xmlns:atom="http://www.w3.org/2005/Atom"'
    text += '\n\t xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"'
    text += '\n\t xmlns:slash="http://purl.org/rss/1.0/modules/slash/"'
    text += '\n\t >\n\n'
    text += '<channel>'
    text += '\n\t<title>VK.com Новости</title>'
    text += '\n\t<atom:link href="http://vkfeed.caaat.pro/atom.xml" rel="self" type="application/rss+xml" />'
    text += '\n\t<link>http://vkfeed.caaat.pro/</link>'
    text += '\n\t<description>VK.com Новости Рудых Андрея</description>'
    text += '\n\t<lastBuildDate>' + d + '</lastBuildDate>'
    text += '\n\t<language>ru-RU</language>'
    text += '\n\t<sy:updatePeriod>hourly</sy:updatePeriod>'
    text += '\n\t<sy:updateFrequency>1</sy:updateFrequency>'
    text += '\n\t<generator>http://wordpress.org/?v=4.1.1</generator>'

    news = latest_news()
    for n in news:
        text += '\n\t<item>'
        text += '\n\t\t<title>' + n['author'].encode('utf-8') + '</title>'
        text += '\n\t\t<link>' + n['link'] + '</link>'
        text += '\n\t\t<comments>' + n['link'] + '</comments>'
        text += '\n\t\t<pubDate>' + n['date'].encode('utf-8') + '</pubDate>'
        text += '\n\t\t<dc:creator><![CDATA[' + n['author'].encode('utf-8') + ']]></dc:creator>'
        text += '\n\t\t<category></category>'

        text += '\n\t\t<description><![CDATA[' + n['images'] + n['text'].encode('utf-8') + ']]]></description>'
        text += '\n\t\t<content:encoded><![CDATA[' + n['images'] + n['text'].encode('utf-8') + ']]>'
        text += '\n\t\t</content:encoded>'
        text += '\n\t</item>'

    text += '\n</channel>'
    text += '\n</rss>'

    # path = "/var/www/vkfeed.caaat.pro/atom.xml"
    #path = "atom.xml"
    # f = open(path, 'w')
    #f.write(text)
    #f.close()

    return text


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_header("Content-type", "application/rss+xml; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Expose-Headers", "Access-Control-Allow-Origin")
        self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Accept-Language", "ru-RU,ru;q=0.8")
        self.end_headers()

    def do_GET(self):
        print(self.path)

        if self.path == "/favicon.ico":
            self.send_response(200)
            self._set_headers()
# определять страницу и отдавать контент только с ниё!
        text = get()
        self.wfile.write(text)

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        self.wfile.write("1")


def run(server_class=HTTPServer, handler_class=S, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()


if __name__ == '__main__':
    run()