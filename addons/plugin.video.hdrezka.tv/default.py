#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Writer (c) 2012-2021, MrStealth, dandy

import os
import socket
import sys
import urllib.parse
from operator import itemgetter

import SearchHistory as history
import XbmcHelpers
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from Translit import Translit

import requests
import router
from helpers import log, get_media_attributes, color_rating

common = XbmcHelpers
transliterate = Translit()

socket.setdefaulttimeout(120)

USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0"


class HdrezkaTV:
    def __init__(self):
        self.id = 'plugin.video.hdrezka.tv'
        self.addon = xbmcaddon.Addon(self.id)
        self.icon = self.addon.getAddonInfo('icon')
        self.icon_next = os.path.join(self.addon.getAddonInfo('path'), 'resources/icons/next.png')
        self.language = self.addon.getLocalizedString
        self.handle = int(sys.argv[1])

        # settings
        self.use_transliteration = self.addon.getSettingBool('use_transliteration')
        self.quality = self.addon.getSetting('quality')
        self.translator = self.addon.getSetting('translator')
        self.domain = self.addon.getSetting('domain')
        self.show_description = self.addon.getSettingBool('show_description')

        self.url = self.addon.getSetting('dom_protocol') + '://' + self.domain
        self.proxies = self._load_proxy_settings()

    def _load_proxy_settings(self):
        if self.addon.getSetting('use_proxy') == 'false':
            return False
        proxy_protocol = self.addon.getSetting('protocol')
        proxy_url = self.addon.getSetting('proxy_url')
        return {
            'http': proxy_protocol + '://' + proxy_url,
            'https': proxy_protocol + '://' + proxy_url
        }

    def make_response(self, method, uri, params=None, data=None, cookies=None, headers=None):
        if not headers:
            headers = {
                "Host": self.domain,
                "Referer": self.domain,
                "User-Agent": USER_AGENT,
            }
        return requests.request(method, self.url + uri, params=params, data=data, headers=headers, cookies=cookies)

    def main(self):
        params = router.parse_uri(sys.argv[2])
        log(f'*** main params: {params}')
        mode = params.get('mode')
        if mode == 'play':
            self.play(params.get('url'))
        elif mode == 'play_episode':
            self.play_episode(
                params.get('url'),
                params.get('post_id'),
                params.get('season_id'),
                params.get('episode_id'),
                urllib.parse.unquote_plus(params['title']),
                params.get('image'),
                params.get('idt'),
                urllib.parse.unquote_plus(params['data'])
            )
        elif mode == 'show':
            self.show(params.get('uri'))
        elif mode == 'index':
            self.index(params.get('uri'), params.get('page'), params.get('query_filter'))
        elif mode == 'categories':
            self.categories()
        elif mode == 'sub_categories':
            self.sub_categories(params.get('uri'))
        elif mode == 'search':
            external = 'main' if 'main' in params else None
            if not external:
                external = 'usearch' if 'usearch' in params else None
            self.search(params.get('keyword'), external)
        elif mode == 'history':
            self.history()
        elif mode == 'collections':
            self.collections(int(params.get('page', 1)))
        else:
            self.menu()

    def menu(self):
        menu_items = (
            ('search', 'FF00FF00', 30000),
            ('history', 'FF00FF00', 30008),
            ('categories', 'FF00FF00', 30003),
            ('index', 'FFDDD2CC', 30009),
            ('index_popular', 'FFDDD2CC', 30010),
            ('index_soon', 'FFDDD2CC', 30011),
            ('index_watching', 'FFDDD2CC', 30012),
        )
        for mode, color, translation_id in menu_items:
            uri = router.build_uri(mode)
            if '_' in mode:
                mode, query_filter = mode.split('_')
                uri = router.build_uri(mode, query_filter=query_filter)
            item = xbmcgui.ListItem(f'[COLOR={color}][{self.language(translation_id)}][/COLOR]')
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def categories(self):
        response = self.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"id": "topnav-menu"})

        titles = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"})
        links = common.parseDOM(genres, "a", attrs={"class": "b-topnav__item-link"}, ret='href')
        for i, title in enumerate(titles):
            title = common.stripTags(title)
            item_uri = router.build_uri('sub_categories', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        item_uri = router.build_uri('collections')
        item = xbmcgui.ListItem('Подборки')
        item.setArt({'thumb': self.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def sub_categories(self, uri):
        response = self.make_response('GET', '/')
        genres = common.parseDOM(response.text, "ul", attrs={"class": "left"})

        titles = common.parseDOM(genres, "a")
        links = common.parseDOM(genres, "a", ret='href')

        item_uri = router.build_uri('index', uri=uri)
        item = xbmcgui.ListItem('[COLOR=FF00FFF0][' + self.language(30007) + '][/COLOR]')
        item.setArt({'thumb': self.icon})
        xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        for i, title in enumerate(titles):
            if not links[i].startswith(uri):
                continue
            item_uri = router.build_uri('index', uri=links[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def collections(self, page):
        uri = '/collections/'
        if page != 1:
            uri = f'/collections/page/{page}/'

        response = self.make_response('GET', uri)
        content = common.parseDOM(response.text, 'div', attrs={'class': 'b-content__collections_list clearfix'})
        titles = common.parseDOM(content, "a", attrs={"class": "title"})
        counts = common.parseDOM(content, 'div', attrs={"class": ".num"})
        links = common.parseDOM(content, "div", attrs={"class": "b-content__collections_item"}, ret="data-url")
        icons = common.parseDOM(content, "img", attrs={"class": "cover"}, ret="src")

        for i, name in enumerate(titles):
            item_uri = router.build_uri('index', uri=router.normalize_uri(links[i]))
            item = xbmcgui.ListItem(f'{name} [COLOR=55FFFFFF]({counts[i]})[/COLOR]')
            item.setArt({'thumb': icons[i]})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        if not len(titles) < 32:
            item_uri = router.build_uri('collections', page=page + 1)
            item = xbmcgui.ListItem("[COLOR=orange]" + self.language(30004) + "[/COLOR]")
            item.setArt({'icon': self.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'files')
        xbmcplugin.endOfDirectory(self.handle, True)

    def index(self, uri=None, page=None, query_filter=None):
        url = uri
        if not url:
            url = '/'
        if page:
            url += f'page/{page}/'
        if query_filter:
            url += f'?filter={query_filter}'

        response = self.make_response('GET', url)
        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__inline_items"})

        items = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"})
        post_ids = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"}, ret="data-id")

        link_containers = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-link"})

        links = common.parseDOM(link_containers, "a", ret='href')
        titles = common.parseDOM(link_containers, "a")
        div_covers = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-cover"})

        country_years = common.parseDOM(link_containers, "div")

        for i, name in enumerate(titles):
            info = self.get_item_description(post_ids[i])
            title = f'{name} {color_rating(info["rating"])} [COLOR=55FFFFFF]({country_years[i]})[/COLOR]'
            image = self._normalize_url(common.parseDOM(div_covers[i], "img", ret='src')[0])
            item_uri = router.build_uri('show', uri=router.normalize_uri(links[i]))
            year, country, genre = get_media_attributes(country_years[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': image, 'icon': image})
            item.setInfo(
                type='video',
                infoLabels={
                    'title': title,
                    'genre': genre,
                    'year': year,
                    'country': country,
                    'plot': info['description'],
                    'rating': info['rating']
                }
            )
            is_serial = common.parseDOM(div_covers[i], 'span', attrs={"class": "info"})
            is_folder = True
            if (self.quality != 'select') and not is_serial:
                item.setProperty('IsPlayable', 'true')
                is_folder = False
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        if not len(titles) < 16:
            params = {'page': 2, 'uri': uri}
            if page:
                params['page'] = int(page) + 1
            if query_filter:
                params['query_filter'] = query_filter
            item_uri = router.build_uri('index', **params)
            item = xbmcgui.ListItem("[COLOR=orange]" + self.language(30004) + "[/COLOR]")
            item.setArt({'icon': self.icon_next})
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def select_quality(self, links, title, image, subtitles=None):
        lst = sorted(iter(links.items()), key=itemgetter(0))
        i = 0
        quality_prev = 360
        for quality, link in lst:
            i += 1
            if self.quality != 'select':
                if quality > int(self.quality[:-1]):
                    self.play(links[quality_prev], subtitles)
                    break
                elif len(lst) == i:
                    self.play(links[quality], subtitles)
            else:
                film_title = f"{title} - [COLOR=orange]{quality}p[/COLOR]"
                item_uri = router.build_uri('play', url=link)
                item = xbmcgui.ListItem(film_title)
                item.setArt({'icon': image})
                item.setInfo(
                    type='Video',
                    infoLabels={'title': film_title, 'overlay': xbmcgui.ICON_OVERLAY_WATCHED, 'playCount': 0}
                )
                item.setProperty('IsPlayable', 'true')
                if subtitles:
                    item.setSubtitles([subtitles])
                xbmcplugin.addDirectoryItem(self.handle, item_uri, item, False)
            quality_prev = quality

    def select_translator(self, content, tv_show, post_id, url, idt, action):
        try:
            div = common.parseDOM(content, 'ul', attrs={'id': 'translators-list'})[0]
        except Exception as ex:
            log(f'select_translator fault parse dom ex: {ex}')
            return tv_show, idt, None
        titles = common.parseDOM(div, 'li', ret='title')
        ids = common.parseDOM(div, 'li', ret="data-translator_id")

        # transform flag image into title suffix
        title_items = common.parseDOM(div, 'li')
        for index, title in enumerate(title_items):
            images = common.parseDOM(title, 'img', ret='title')
            for img in images:
                titles[index] += f' ({img})'

        if len(titles) > 1:
            dialog = xbmcgui.Dialog()
            index_ = dialog.select(self.language(30006), titles)
            if int(index_) < 0:
                index_ = 0
        else:
            index_ = 0
        idt = ids[index_]

        data = {
            "id": post_id,
            "translator_id": idt,
            "action": action
        }
        is_director = common.parseDOM(div, 'li', attrs={'data-translator_id': idt}, ret='data-director')
        if is_director:
            data['is_director'] = is_director[0]

        headers = {
            "Host": self.domain,
            "Origin": self.url,
            "Referer": url,
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest"
        }

        # {"success":true,"message":"","url":"[
        # 360p]https:\/\/stream.voidboost.cc\/8\/8\/1\/3\/3\/ddddfc45662e813d93128d783cb46e7f:2020101118\/3dxox.mp4
        # :hls:manifest.m3u8 or https:\/\/stream.voidboost.cc\/61e68929526165ffb2e5483777a4bd94:2020101118\/8\/8\/1
        # \/3\/3\/3dxox.mp4,[480p]https:\/\/stream.voidboost.cc\/8\/8\/1\/3\/3\/ddddfc45662e813d93128d783cb46e7f
        # :2020101118\/ppjm0.mp4:hls:manifest.m3u8 or
        # https:\/\/stream.voidboost.cc\/6498b090482768d1433d456b2e35c46a:2020101118\/8\/8\/1\/3\/3\/ppjm0.mp4,
        # [720p]https:\/\/stream.voidboost.cc\/8\/8\/1\/3\/3\/ddddfc45662e813d93128d783cb46e7f:2020101118\/0w0az.mp4
        # :hls:manifest.m3u8 or https:\/\/stream.voidboost.cc\/b10164963f454ad391b2a13460568561:2020101118\/8\/8\/1
        # \/3\/3\/0w0az.mp4,[1080p]https:\/\/stream.voidboost.cc\/8\/8\/1\/3\/3\/ddddfc45662e813d93128d783cb46e7f
        # :2020101118\/n9qju.mp4:hls:manifest.m3u8 or
        # https:\/\/stream.voidboost.cc\/b8a860d0938b593ed4b64723944b9a12:2020101118\/8\/8\/1\/3\/3\/n9qju.mp4,
        # [1080p Ultra]https:\/\/stream.voidboost.cc\/8\/8\/1\/3\/3\/ddddfc45662e813d93128d783cb46e7f:2020101118
        # \/4l9xx.mp4:hls:manifest.m3u8 or https:\/\/stream.voidboost.cc\/13c067a1dcd54be75007a74bde421b17:2020101118
        # \/8\/8\/1\/3\/3\/4l9xx.mp4","quality":"480p","subtitle":"[
        # \u0420\u0443\u0441\u0441\u043a\u0438\u0439]https:\/\/static.voidboost.com\/view\/BmdZqxHeI9zXhhEWUUP70g
        # \/1602429855\/8\/8\/1\/3\/3\/c1lz5sebdx.vtt,
        # [\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430]https:\/\/static.voidboost.com\/view
        # \/F8mGgsIZee6XMjvtXSojhQ\/1602429855\/8\/8\/1\/3\/3\/f0zfov3en4.vtt,
        # [English]https:\/\/static.voidboost.com\/view\/enBDXHLd9y6OByIGY8AiZQ\/1602429855\/8\/8\/1\/3\/3
        # \/ut8ik78tq5.vtt","subtitle_lns":{"off":"","\u0420\u0443\u0441\u0441\u043a\u0438\u0439":"ru",
        # "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430":"ua","English":"en"},"subtitle_def":"ru",
        # "thumbnails":"\/ajax\/get_cdn_tiles\/0\/32362\/?t=1602170655"}

        response = self.make_response('POST', "/ajax/get_cdn_series/", data=data, headers=headers).json()

        subtitles = None
        if action == "get_movie":
            playlist = [response["url"]]
            try:
                subtitles = response["subtitle"].split(']')[1].split(',')[0].replace(r"\/", "/")
            except Exception as ex:
                log(f'fault decode subtitles ex: {ex}')
        else:
            # seasons = response["seasons"] not used ?
            episodes = response["episodes"]
            playlist = common.parseDOM(episodes, "ul", attrs={"class": "b-simple_episodes__list clearfix"})
        return playlist, idt, subtitles

    @staticmethod
    def get_links(data):
        log(f'*** get_links data: {data}')
        links = data.replace(r"\/", "/").split(",")
        manifest_links = {}
        for link in links:
            if "Ultra" not in link:
                manifest_links[int(link.split("]")[0].replace("[", "").replace("p", ""))] = link.split("]")[1]
            else:
                manifest_links[2160] = link.split("]")[1]
        return manifest_links

    def show(self, uri):
        response = self.make_response('GET', uri)

        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__main"})[0]
        image = common.parseDOM(content, "img", attrs={"itemprop": "image"}, ret="src")[0]
        title = common.parseDOM(content, "h1")[0]
        post_id = common.parseDOM(content, "input", attrs={"id": "post_id"}, ret="value")[0]
        idt = "0"
        try:
            idt = common.parseDOM(
                content,
                "li",
                attrs={"class": "b-translator__item active"},
                ret="data-translator_id"
            )[0]
        except Exception as ex:
            log(f'fault parseDOM ex: {ex}')
            try:
                idt = response.text.split("sof.tv.initCDNSeriesEvents")[-1].split("{")[0]
                idt = idt.split(",")[1].strip()
            except Exception as ex:
                log(f'fault search CDN ex: {ex}')
        subtitles = None
        tv_show = common.parseDOM(response.text, "div", attrs={"id": "simple-episodes-tabs"})
        if tv_show:
            if self.translator == "select":
                tv_show, idt, subtitles = self.select_translator(content, tv_show, post_id, uri, idt, "get_episodes")
            titles = common.parseDOM(tv_show, "li")
            ids = common.parseDOM(tv_show, "li", ret='data-id')
            seasons = common.parseDOM(tv_show, "li", ret='data-season_id')
            episodes = common.parseDOM(tv_show, "li", ret='data-episode_id')
            data = common.parseDOM(tv_show, "li", ret='data-cdn_url')

            for i, title_ in enumerate(titles):
                title_ = f"{title_} ({self.language(30005)} {seasons[i]})"
                url_episode = uri
                item_uri = router.build_uri(
                    'play_episode',
                    url=url_episode,
                    urlm=uri,
                    post_id=ids[i],
                    season_id=seasons[i],
                    episode_id=episodes[i],
                    title=title_,
                    image=image,
                    idt=idt,
                    data=data[i]
                )
                item = xbmcgui.ListItem(title_)
                item.setArt({'thumb': image, 'icon': image})
                item.setInfo(type='Video', infoLabels={'title': title_})
                if self.quality != 'select':
                    item.setProperty('IsPlayable', 'true')
                xbmcplugin.addDirectoryItem(self.handle, item_uri, item, True if self.quality == 'select' else False)
        else:
            content = [response.text]
            if self.translator == "select":
                content, idt, subtitles = self.select_translator(content[0], content, post_id, uri, idt, "get_movie")
            data = content[0].split('"streams":"')[-1].split('",')[0]

            links = self.get_links(data)
            self.select_quality(links, title, image, subtitles)

        xbmcplugin.setContent(self.handle, 'episodes')
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_item_description(self, post_id):
        if not self.show_description:
            return {'rating': '', 'description': ''}
        data = {
            "id": post_id,
            "is_touch": 1
        }
        response = self.make_response('POST', '/engine/ajax/quick_content.php', data=data)
        description = common.parseDOM(response.text, 'div', attrs={'class': 'b-content__bubble_text'})[0]

        try:
            imdb_rating = common.parseDOM(response.text, 'span', attrs={'class': 'imdb'})[0]
            rating = common.parseDOM(imdb_rating, 'b')[0]
        except IndexError as ex:
            log(f'fault parse imdb_rating ex: {ex}')
            try:
                kp_rating = common.parseDOM(response.text, 'span', attrs={'class': 'kp'})[0]
                rating = common.parseDOM(kp_rating, 'b')[0]
            except IndexError as ex:
                log(f'fault parse kp_rating ex: {ex}')
                rating = 0
        return {'rating': rating, 'description': description}

    def history(self):
        words = history.get_history()
        for word in reversed(words):
            uri = router.build_uri('search', keyword=word, main=1)
            item = xbmcgui.ListItem(word)
            item.setArt({'thumb': self.icon, 'icon': self.icon})
            xbmcplugin.addDirectoryItem(self.handle, uri, item, True)
        xbmcplugin.endOfDirectory(self.handle, True)

    def get_user_input(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(self.language(30000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            if self.use_transliteration:
                keyword = transliterate.rus(kbd.getText())
            else:
                keyword = kbd.getText()

            history.add_to_history(keyword)

        return keyword

    def search(self, keyword, external):
        log(f'*** search keyword: {keyword} external: {external}')
        keyword = urllib.parse.unquote_plus(keyword) if (external is not None) else self.get_user_input()
        if not keyword:
            return self.menu()

        params = {
            "do": "search",
            "subaction": "search",
            "q": str(keyword)
        }
        response = self.make_response('GET', '/search/', params=params, cookies={"dle_user_taken": '1'})

        content = common.parseDOM(response.text, "div", attrs={"class": "b-content__inline_items"})
        items = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"})
        post_ids = common.parseDOM(content, "div", attrs={"class": "b-content__inline_item"}, ret="data-id")
        link_containers = common.parseDOM(items, "div", attrs={"class": "b-content__inline_item-link"})
        links = common.parseDOM(link_containers, "a", ret='href')
        titles = common.parseDOM(link_containers, "a")
        country_years = common.parseDOM(link_containers, "div")

        for i, name in enumerate(titles):
            info = self.get_item_description(post_ids[i])
            title = f'{name} {color_rating(info["rating"])} [COLOR=55FFFFFF]({country_years[i]})[/COLOR]'
            image = self._normalize_url(common.parseDOM(items[i], "img", ret='src')[0])
            item_uri = router.build_uri('show', uri=router.normalize_uri(links[i]))
            year, country, genre = get_media_attributes(country_years[i])
            item = xbmcgui.ListItem(title)
            item.setArt({'thumb': image, 'icon': image})
            item.setInfo(
                type='video',
                infoLabels={
                    'title': title,
                    'genre': genre,
                    'year': year,
                    'country': country,
                    'plot': info['description'],
                    'rating': info['rating']
                }
            )
            is_serial = common.parseDOM(items[i], 'span', attrs={"class": "info"})
            is_folder = True
            if (self.quality != 'select') and not is_serial:
                item.setProperty('IsPlayable', 'true')
                is_folder = False
            xbmcplugin.addDirectoryItem(self.handle, item_uri, item, is_folder)

        xbmcplugin.setContent(self.handle, 'movies')
        xbmcplugin.endOfDirectory(self.handle, True)

    def play(self, url, subtitles=None):
        log(f'*** play url: {url} subtitles: {subtitles}')
        item = xbmcgui.ListItem(path=url)
        if subtitles:
            item.setSubtitles([subtitles])
        xbmcplugin.setResolvedUrl(self.handle, True, item)

    def play_episode(self, url, post_id, season_id, episode_id, title, image, idt, data):
        if data == "null":
            data = {
                "id": post_id,
                "translator_id": idt,
                "season": season_id,
                "episode": episode_id,
                "action": "get_stream"
            }
            headers = {
                "Host": self.domain,
                "Origin": self.url,
                "Referer": url,
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest"
            }
            response = self.make_response('POST', "/ajax/get_cdn_series/", data=data, headers=headers).json()
            data = response["url"]
        links = self.get_links(data)
        self.select_quality(links, title, image, None)
        xbmcplugin.setContent(self.handle, 'episodes')
        xbmcplugin.endOfDirectory(self.handle, True)

    def _normalize_url(self, item):
        if not item.startswith("http"):
            item = self.url + item
        return item


plugin = HdrezkaTV()
plugin.main()
