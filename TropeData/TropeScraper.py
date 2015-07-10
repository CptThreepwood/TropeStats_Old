"""
Scrape relevant information from TvTropes
http://tvtropes.org/
"""
import requests
import sys
import re
from collections import deque
from bs4 import BeautifulSoup
import logging
import settings
import ColourStreamHandler

from DataHandler import DataHandler

TVTROPES_BASE = "tvtropes.org"
TVTROPES_MAIN = "http://tvtropes.org"
TVTROPES_PAGE = "%s/pmwiki/pmwiki.php" % TVTROPES_MAIN
TVTROPES_TROPE = "%s/Main" % TVTROPES_PAGE
TVTROPES_TROPEINDEX = "%s/Tropes" % TVTROPES_TROPE

class TropeScraper(object):
    """
    TropeScraper
    """
    urls_parsed = 0
    new_urls = deque()
    known_redirects = {}
    urls_visited = set()
    data_handler = None

    ignored_types = settings.IGNORED_TYPES
    allowed_media = settings.ALLOWED_MEDIA
    known_aliases = settings.KNOWN_ALIASES

    def __init__(self):

        self.data_handler = DataHandler()

        unread_urls, old_urls = self.data_handler.get_urls()
        redirects = self.data_handler.get_redirects()
        for url in old_urls:
            self.urls_visited.add(url[0])
        for url in unread_urls:
            self.new_urls.append(url[0])
        for redirect in redirects:
            self.known_redirects[redirect[0]] = redirect[1]

    def test_redirect(self, url):
        '''
        Find if a url redirects
        If it does, return that new url
        '''
        # Remove Tvtropes redirect tag
        redirect_index = str(url).rfind("?from=")
        final_url = None
        if redirect_index > 0:
            url = url[0:redirect_index]
        if url in self.known_redirects:
            final_url = self.known_redirects[url]
        else:
            logging.debug("Testing redirect for %s", url)
            try:
                req = requests.get(url)

                final_url = req.url

                # Remove Tvtropes redirect tag
                redirect_index = final_url.rfind("?from=")
                if redirect_index > 0:
                    final_url = final_url[:redirect_index]

                self.known_redirects[url] = final_url

            except OSError:
                logging.error("%s could not be found", url)
                return None
            except BaseException as err:
                logging.error("Unknown error opening %s", url)
                logging.error("%s\n%s", sys.exc_info()[0], err)
                return None

        return final_url

    def identify_url(self, url, parent_name=None):
        '''
        Identify page type by parsing the url
        '''
        url_components = url.split('/')
        url_type = url_components[-2]
        url_name = url_components[-1]

        # Simple Cases.  Page Url is .../Type/Name
        # If we're ignoring this page type -> return None
        if any(url_type.lower() == ignored for ignored in self.ignored_types):
            logging.info("Ignored Type: %s", url_type)
            page_type = None
            page_key = None
        # If this is a media url -> return "media", type/name
        elif any(url_type.lower() == media for media in self.allowed_media):
            page_type = "media"
            page_key = url_type + '/' + url_name
        # If this is a trope url -> return "trope", name
        elif url_type == "Main":
            page_type = "trope"
            page_key = url_name

        # Trickier Cases. SubPages where we have the parent_name because we came from that page
        # Ignored types for trope sub-pages
        elif (url_type == parent_name
              and any(url_name.lower() == media for media in self.ignored_types)):
            logging.info("Ignored Type: %s", url_type)
            page_type = None
            page_key = None
        # MediaSubPage Url is something like /MediaName/TropesAtoC
        # If this is a media sub-page -> return "mediaSubPage", mediaName
        elif url_type == parent_name and re.search("[A-Za-z][Tt]o[A-Za-z]$", url_name):
            page_type = "mediaSubPage"
            page_key = parent_name
        # TropeSubPage Url is something like /TropeName/MediaType
        # If this is a trope sub-page -> return "tropeSubPage", tropeName
        elif (url_type == parent_name
              and any(url_name.lower() == media for media in self.allowed_media)):
            page_type = "tropeSubPage"
            page_key = parent_name
        # Sometimes a name is shortened for sub-pages.  This is really annoying.
        # If this is a media sub-page with a known alias -> return "mediaSubPage", mediaName
        elif parent_name in self.known_aliases:
            if url_type == self.known_aliases[parent_name] and "Tropes" in url_name:
                page_type = "mediaSubPage"
                page_key = parent_name
            elif (url_type == self.known_aliases[parent_name]
                  and any(url_name.lower() == media for media in self.allowed_media)):
                page_type = "tropeSubPage"
                page_key = parent_name
            elif url_type == self.known_aliases[parent_name]:
                logging.warning("Known Alias but not a Recognised SubPage: %s", url)
                page_type = None
                page_key = None
            else:
                logging.warning("Unknown Page Type: %s", url)
                page_type = None
                page_key = None

        # Complicated Cases. For the first cases we have Name because we came from that page
        # What if a page links to a sub-page for another trope
        elif any(url_name.lower() == media for media in self.allowed_media):
            test_url = TVTROPES_TROPE + url_type
            logging.info("Possibly a link to a sub-page not from a parent %s", url)
            logging.info("Testing for %s", test_url)
            result = self.test_redirect(test_url)
            if result:
                logging.info("Found a trope page")
                page_type = "trope"
                page_key = url_type
            else:
                page_type = None
                page_key = None
        else:
            logging.error("Unknown Url: %s", url)
            logging.error("On page: %s with %s/%s", parent_name, url_type, url_name)
            page_type = None
            page_key = None
        return page_type, page_key

    def parse_page(self, url, options=None):
        '''
        Extract all relevant information from url
        options exists to aid parsing sub-pages
        maybe it's scope will be expanded in future
        '''
        # Load Page
        text = requests.get(url).text
        html = BeautifulSoup(text)

        page_type = None
        page_key = None
        # Get page information from options
        if options:
            for key in options:
                if key == "MediaSubPage":
                    page_type = "media"
                    page_key = options[key]
                if key == "TropeSubPage":
                    page_type = "trope"
                    page_key = options[key]
        # If that didn't work try and work out info from url
        if not page_type or not page_key:
            page_type, page_key = self.identify_url(url)

        # Find text block
        textblock = html.find(attrs={"id": "wikitext"})

        # If there is no text block, give up
        if not textblock:
            logging.error("%s has no wikitext", url)
            return 1

        # Save this page information
        # Fix this for the sub-page cases
        if options:
            if any(x in options for x in ["MediaSubPage", "TropeSubPage"]):
                logging.info("%s", url)
                logging.info("Adding to Entry: %s", page_key)
        elif url not in self.urls_visited:
            logging.info("Creating New Entry")
            name = html.find('title').string.replace(" - TV Tropes", "")
            if page_type == "media":
                self.data_handler.add_media(page_key, url, name)
            elif page_type == "trope":
                self.data_handler.add_trope(page_key, url, name)

        # There are some examples - Let's go find them
        items = textblock.find_all('li')
        n_subtags = 0
        for item in items:
            # Find the first relevant link in a line
            links = item.find_all('a')
            link = None
            initial_url = None
            final_url = None
            for testlink in links:
                #if 'href' not in testlink:
                #    logging.warning("a element does not contain href: %s", testlink)
                #    continue
                # Sometimes links contain unicode characters.
                # I'm guessing that's never something I want but this is kinda hacky
                # I should instead flag this as an error and resolve it sensibly
                # https://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen
                initial_url = testlink['href'] #.encode('ascii', 'ignore')
                final_url = None
                # Save some time not bothering to follow external links
                if TVTROPES_PAGE not in initial_url:
                    continue
                # Don't bother testing the redirect if it's an ignored type
                initial_url_type = initial_url.split('/')[-2]
                if any(initial_url_type.lower() == ignored for ignored in self.ignored_types):
                    logging.info("Ignored Type: %s", initial_url_type)
                    continue
                final_url = self.test_redirect(initial_url)

                # Redirect unresolved
                if not final_url:
                    continue
                # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
                if TVTROPES_PAGE not in initial_url:
                    continue
                # Found the first link worth following
                else:
                    link = testlink
                    break
            # Verify we have a link
            if not link:
                continue
            entry_type, entry_key = self.identify_url(final_url, page_key.split('/')[-1])

            # Skip any 'li' nested within 'li'
            # Only skip if they aren't subPages (thanks Buffy)
            if n_subtags > 0:
                n_subtags -= 1
                if entry_type != "mediaSubPage" and entry_type != "tropeSubPage":
                    continue
            else:
                n_subtags = len(item.find_all('li'))

            # Assign results to appropriate dictionary
            # Save tropes associated to this media, check their urls
            if page_type == "media":
                # Make a note of this connection
                if entry_type == "trope":
                    self.data_handler.add_relation(page_key, entry_key, 1, 1)
                # Harvest urls to follow
                if final_url not in self.urls_visited:
                    # Add link to link database
                    if entry_type == "trope":
                        if initial_url not in self.new_urls:
                            self.new_urls.append(initial_url)
                            self.data_handler.add_url(initial_url, final_url)
                    # We've got a bunch of sub-pages for this media
                    # Immediately go get subpage information
                    elif entry_type == "mediaSubPage":
                        if options:
                            logging.warning("A sub-subPage or subPages refer to each other")
                            logging.warning("Skipping %s", final_url)
                            continue
                        self.parse_page(final_url, {"MediaSubPage" : page_key})
                    # Franchise pages sometimes just link to each media subpage
                    # In this case we should investigate each of those links,
                    # but not associate them to the Franchise page
                    elif page_key.split('/')[0] == "Franchise" and entry_type == "media":
                        # Add link to link database
                        if initial_url not in self.new_urls:
                            self.new_urls.append(initial_url)
                            self.data_handler.add_url(initial_url, final_url)
                    elif entry_type == "media":
                        if (initial_url not in self.new_urls
                                and final_url != TVTROPES_PAGE + page_key):
                            self.new_urls.append(initial_url)
                            self.data_handler.add_url(initial_url, final_url)
                    else:
                        logging.warning("Not currently considering: %s", final_url)
            # Save media associated to trope, check their urls
            elif page_type == "trope":
                # Make a note of this connection
                if entry_type == "media":
                    self.data_handler.add_relation(entry_key, page_key, 1, -1)
                # Harvest urls to follow
                if final_url not in self.urls_visited:
                    # Add link to link database
                    if entry_type == "media":
                        if initial_url not in self.new_urls:
                            self.data_handler.add_url(initial_url, final_url)
                            self.new_urls.append(initial_url)
                    # If this is a super-trope page, add tropes to list
                    elif entry_type == "trope":
                        if (initial_url not in self.new_urls
                                and final_url != TVTROPES_TROPE + page_key):
                            self.new_urls.append(initial_url)
                            self.data_handler.add_url(initial_url, final_url)
                    # This tropes media have been split into types, go explore them all now
                    elif entry_type == "tropeSubPage":
                        if options:
                            logging.warning("A sub-subPage or subPages refer to each other")
                            logging.warning("Skipping %s", final_url)
                            continue
                        self.parse_page(final_url, {"TropeSubPage" : page_key})
                    else:
                        logging.warning("Not currently considering: %s", final_url)

        # Map out related pages
        do_related = True
        if options:
            if any(x in options for x in ["MediaSubPage", "TropeSubPage"]):
                do_related = False

        table = html.find_all(attrs={"class": "wiki-walk"})
        if do_related and table:
            related = table[0]
            rows = related.find_all(attrs={"class": "walk-row"})
            for row in rows:
                items = row.find_all('span')
                previous = items[0].find('a')
                current = items[1].find('a')
                subsequent = items[2].find('a')
                if previous:
                    previous_url = "".join([TVTROPES_MAIN, previous['href']])
                    previous_redirect = self.test_redirect(previous_url.encode('ascii', 'ignore'))
                    if previous_redirect:
                        previous_type = self.identify_url(previous_redirect)[0]
                        if (previous_redirect not in self.urls_visited
                                and previous_url not in self.new_urls and previous_type):
                            self.new_urls.append(previous_url)
                            self.data_handler.add_url(previous_url, previous_redirect)
                if current:
                    current_url = TVTROPES_MAIN + current['href']
                    current_redirect = self.test_redirect(current_url.encode('ascii', 'ignore'))
                    if current_redirect:
                        current_type, current_key = self.identify_url(current_redirect)
                        if current_type:
                            if page_key != current_key:
                                self.data_handler.add_index(page_key, current_key)
                            if (current_redirect not in self.urls_visited
                                    and current_url not in self.new_urls):
                                self.new_urls.append(current_url)
                                self.data_handler.add_url(current_url, current_redirect)
                if subsequent:
                    subsequent_url = (TVTROPES_MAIN + subsequent['href']).encode('ascii', 'ignore')
                    subsequent_redirect = self.test_redirect(subsequent_url)
                    if subsequent_redirect:
                        subsequent_type, subsequent_key = self.identify_url(subsequent_redirect)
                        if (subsequent_redirect not in self.urls_visited
                                and subsequent_url not in self.new_urls and subsequent_type):
                            self.new_urls.append(subsequent_url)
                            self.data_handler.add_url(subsequent_url, subsequent_redirect)
        elif do_related:
            logging.warning("No Relation Table found at %s", final_url)

        # Done Parsing, add to DB
        logging.debug("%s finished", url)
        self.urls_visited.add(url)
        self.data_handler.commit_page(url)
        return 0

    def recur_search(self, url=None):
        '''
        Use a recursive depth-first search across all of TvTropes
        Number of urls accessed restricted by the settings.limit option
        '''
        if not url:
            url = self.new_urls.popleft()

        # Don't follow external links
        if "tvtropes.org" not in url:
            logging.info("External Link Ignored: %s", url)
            return

        if settings.LIMIT != -1 and self.urls_parsed >= settings.LIMIT:
            logging.critical("Exceeded limit")
            sys.exit()

        final_url = self.test_redirect(url)
        if not final_url:
            return
        self.urls_parsed = self.urls_parsed + 1
        page_type, page_title = self.identify_url(final_url)
        # Code snippet to make ordinal numbers
        # http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
        ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n/10%10 != 1)*(n%10 < 4)*n%10::4])
        logging.info("Processing %s url", ordinal(self.urls_parsed))
        logging.info("%s", final_url)

        # Ignore links with bad types
        if page_type in self.ignored_types:
            logging.info("Link to unintersting page ignored")
            return
        # Ignore links already searched
        if final_url in self.urls_visited:
            logging.debug("Link already discovered")
            # This shouldn't really be here.  The logic needs to be fixed
            self.data_handler.checked_url(final_url)
            if self.new_urls:
                self.recur_search(self.new_urls.popleft())
            return

        logging.info("%s: %s", page_title, page_type)

        self.parse_page(final_url)
        # If parsing is successful, add any original url to self.urls_visited too
        #if not self.parse_page(final_url):
        #    if final_url != url:
        #        self.urls_visited.add(url)

        # Recurse this search through all untested urls
        if self.new_urls:
            self.recur_search(self.new_urls.popleft())

        return

    def loop_search(self):
        '''
        Use a breadth-first search across all of TvTropes
        Number of urls accessed restricted by the settings.limit option
        '''
        current_count = 0

        while self.new_urls:
            url = self.new_urls.popleft()
            if settings.LIMIT > 0 and current_count >= settings.LIMIT:
                logging.critical("Exceeded limit")
                break

            # Don't follow external links
            if "tvtropes.org" not in url:
                logging.info("External Link Ignored: %s", url)
                # Remove url from DB
                continue

            final_url = self.test_redirect(url)
            if not final_url:
                logging.info("%s could not be resolved", url)
                continue
            current_count = current_count + 1

            page_type, page_title = self.identify_url(final_url)
            # Code snippet to make ordinal numbers
            # http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
            ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n/10%10 != 1)*(n%10 < 4)*n%10::4])

            # Ignore links with bad types
            if page_type in self.ignored_types:
                logging.info("Link to unintersting page ignored")
                continue
            # Ignore links already searched
            if final_url in self.urls_visited:
                logging.debug("Link already discovered")
                # This shouldn't really be here.  The logic needs to be fixed
                self.data_handler.checked_url(final_url)
                current_count = current_count -1
                continue
            logging.info("Processing %s url", ordinal(current_count))
            logging.info("%s", final_url)

            logging.info("%s: %s", page_title, page_type)
            self.parse_page(final_url)
        return

    def run(self, options=None):
        '''
        Run the scraper with options.
        '''
        if options:
            if options['start_url'] not in [self.new_urls, self.urls_visited]:
                self.new_urls.append(options['start_url'])
                self.data_handler.add_url(options['start_url'])
            if options['run_mode'] == 'recursive':
                logging.info("Starting New Run fresh from %s", options['start_url'])
                self.recur_search()
            else:
                logging.info("Starting New Run with %i urls to search", len(self.new_urls))
                self.loop_search()
        if not self.new_urls:
            logging.info("No Urls to investigate.  Provide a start url if a new run is desired")
        return

def main():
    """ Default run """
    log = open(settings.LOG_FILENAME, 'a')
    log.write('\n---------------------------------------------------------\n')
    log.close()

    logging.basicConfig(format=settings.LOG_FORMAT, level=settings.LOG_LEVEL,
                        filename=settings.LOG_FILENAME, filemode='a')

    console_out = ColourStreamHandler.ColourStreamHandler
    console_out.setFormatter(logging.Formatter(settings.CONSOLE_FORMAT))
    logging.getLogger().addHandler(console_out)

    # Search Tvtropes
    scraper = TropeScraper()

    scraper.run(settings.RUN_OPTIONS)

if __name__ == "__main__":
    main()

