'''Parse the urls for the things we care about'''
import json
import re
import os

import bs4
import luigi
from bs4 import BeautifulSoup
import numpy as np

from download_page import DownloadPageTask

TVTROPES_BASE = "tvtropes.org"
TVTROPES_MAIN = "http://tvtropes.org"
TVTROPES_PAGE = "%s/pmwiki/pmwiki.php" % TVTROPES_MAIN
TVTROPES_TROPE = "%s/Main" % TVTROPES_PAGE
TVTROPES_TROPEINDEX = "%s/Tropes" % TVTROPES_TROPE

ERROR_PAGES = [
    '''This page was cut for reason:''',
    '''If you want to start this new page, just click the edit button above.''',
]

def error_page(sample_text):
    '''Find the matching error text'''
    return any([error in sample_text for error in ERROR_PAGES])

IGNORED_TYPES = [
    'Administrivia',
]

def get_url_namespace(url):
    '''Find the TvTropes Namespace'''
    if not url or TVTROPES_PAGE not in url:
        return None
    else:
        return url.split('/')[-2]

def get_url_name(url):
    '''Find the url name'''
    if not url or TVTROPES_PAGE not in url:
        return None
    else:
        return url.split('/')[-1]

def get_local_path(url):
    '''Unique local file path for any url'''
    return url.replace(TVTROPES_PAGE, '')

class ParsePage(luigi.Task):
    '''Parse a downloaded trope page for media'''
    page_url = luigi.Parameter()

    def output(self):
        file_path = get_local_path(self.page_url)
        target_path = './luigi_data/{0}.json'.format(file_path)
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        return luigi.LocalTarget(
            target_path
        )

    def requires(self):
        return DownloadPageTask(
            page_url=self.page_url
        )

    def parse_trope_page(self, html):
        '''Get tropes from the page'''
        # Parse Data
        try:
            trope_soup = BeautifulSoup(html, 'html5lib')
            article = trope_soup.find("div", class_="page-content", itemprop="articleBody")
            if article:
                links = [
                    (link.text, link['href'])
                    for example in article.find_all('li')
                    for link in example.find_all('a')
                    if 'href' in link.attrs.keys()
                ]
            list_section = article.find(re.compile('hr')) if article else None
            if list_section:
                article_text = list(list_section.previous_siblings)[::-1]
                trope_text = ' '.join(
                    [text.encode('utf-8')
                     for text in article_text
                     if not isinstance(text, bs4.element.Comment)]
                ).strip()
            else:
                article_text = None
                trope_text = ''
        except AttributeError:
            print html, 'parsing with html.parser'
            trope_soup = BeautifulSoup(html, 'html.parser')
            article = trope_soup.find("div", class_="page-content", itemprop="articleBody")
            if article:
                links = [
                    (link.text, link['href'])
                    for example in article.find_all('li')
                    for link in example.find_all('a')
                    if 'href' in link.attrs.keys()
                ]
            list_section = article.find(re.compile('hr')) if article else None
            if list_section:
                article_text = list(list_section.previous_siblings)[::-1]
                trope_text = ' '.join([
                    text.encode('utf-8')
                    for text in article_text
                    if not isinstance(text, bs4.element.Comment)
                ]).strip()
            else:
                article_text = None
                trope_text = ''

        # Handle bad pages
        if not article:
            return {
                'article_text': '',
                'sub_pages': [],
                'sub_page_links': [],
                'page_links': [],
                'external_links': [],
            }
        if not article_text or error_page(article_text):
            return {
                'article_text': article_text,
                'sub_pages': [],
                'sub_page_links': [],
                'page_links': [],
                'external_links': [],
            }

        links = [link for link in links if get_url_namespace(link[1]) not in IGNORED_TYPES]
        sub_pages = [link for link in links
                     if link[1].startswith(TVTROPES_MAIN)
                     and get_url_namespace(link[1]) == get_url_name(self.page_url)]
        page_links = [link for link in links
                      if link[1].startswith(TVTROPES_MAIN)
                      and get_url_namespace(link[1]) != get_url_name(self.page_url)]
        external_links = [link for link in links
                          if not link[1].startswith(TVTROPES_MAIN)]
        return {
            'article_text': trope_text,
            'sub_pages': sub_pages,
            'page_links': page_links,
            'sub_page_links': [],
            'external_links': external_links,
        }

    def run(self):
        with self.input().open('r') as raw_html:
            parsed_info = self.parse_trope_page(raw_html.read())
            subpages = yield [
                ParsePage(
                    page_url=url[1].encode('utf-8')
                )
                for url in parsed_info['sub_pages']
            ]
            for subpage in subpages:
                with subpage.open('r') as subpage_json:
                    subpage_info = json.load(subpage_json)
                    parsed_info['sub_page_links'] += subpage_info['page_links']

        with self.output().open('w') as outfile:
            json.dump(parsed_info, outfile, indent=4)
