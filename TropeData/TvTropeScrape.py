"""
Scrape relevant information from TvTropes
http://tvtropes.org/
"""
import urllib
import urllib2
import sys
import re
from collections import deque
from bs4 import BeautifulSoup
import logging
import ColourStreamHandler

import DBTools

counter = 0
limit = 50000

dbconnection = None
dbcursor = None
new_urls = deque()
known_redirects = {}
urls_visited = set()

# Sometimes TvTropes doesn't refer to media with the right name
# This is dumb and requires hacks.  Probably I should make this a config file.  Maybe later.
known_aliases = {
    'BuffyTheVampireSlayer' : 'Buffy'
    }

allowedMedia = [
    'advertising',
    'anime',
    'animeandmanga',
    'animatedfilm',
    'animatedfilms',
    'animation',
    'arg',
    'asiananimation',
    'audio',
    'audioplay',
    'author',
    'blog',
    'bollywood',
    'book',
    'cardgame',
    'cardgames',
    'comicbook',
    'comicbooks',
    'comic',
    'comics',
    'comicstrip',
    'composer',
    'creator',
    'dcanimateduniverse'
    'discworld',
    'disney',               # Apparently big enough to be it's own type of media.  Who knew?
    'disneyandpixar',
    'dreamworks',
    'dungeonsanddragons',
    'easternanimation',
    'fairytales',
    'fanfic',
    'fanfics',
    'fanfiction',
    'fanwork',
    'fanworks',
    'film',
    'films',
    'fokelore',
    'folklore',
    'folkloreandfairytales',
    'franchise',
    'gamebooks',
    'jokes',
    'larp',
    'letsplay',
    'lightnovel',
    'literature',
    'liveaction',
    'liveactionfilm',
    'liveactionfilms',
    'liveactiontv',
    'machinima',
    'manga',
    'manhua',
    'manhwa',
    'manhwaandmanhua',
    'magazine',
    'magazines',
    'marvelcinematicuniverse',
    'media',
    'music',
    'musicvideos',
    'myth',
    'mythandreligion',
    'mythology',
    'mythologyandreligion',
    'mythsandreligion',
    'newmedia',
    'newspapercomic',
    'newspapercomics',
    'other',
    'pinball',
    'podcast',
    'printmedia',
    'professionalwrestling',
    'prowrestling',
    'puppetshows',
    'radio',
    'reallife',
    'recordedandstandupcomedy'
    'religion',
    'religionandmythology',
    'roleplay',
    'roleplayinggames',
    'script',
    'series',
    'sports',
    'standupcomedy',
    'tabletop',
    'tabletoprpg',
    'tabletopgame',
    'tabletopgames',
    'tabletopgaming',
    'television',
    'theater',
    'theatre',
    'themeparks',
    'toys',
    'troperworks',
    'videogame',
    'videogames',
    'visualnovel',
    'visualnovels',
    'webanimation',
    'webcomic',
    'webcomics',
    'webcreator',
    'webgames',
    'webmedia',
    'weboriginal',
    'website',
    'webvideo',
    'webvideos',
    'westernanimation',
    'wiki',
    'wrestling',
    ]

# Can I work out a way to scrape this?
# Maybe using the full list and hardcode some specific allowed types?
# This will do for now
ignoredTypes = [
    # Ignore languages other than English (for now)
    'de', 'eo', 'es', 'fi', 'fr', 'hu', 'it', 'itadministrivia',
    'itdarthwiki', 'itsugarwiki', 'no', 'pl', 'pt', 'ro', 'se',

    # Ignore YMMV type namespaces
    'aatafovs', 'accidentalnightmarefuel', 'alternativecharacterinterpretation',
    'andthefandomrejoiced', 'analysis', 'awesome', 'awesomebosses', 'awesomebutimpractical',
    'awesomemusic', 'badass', 'betterthanitsounds', 'fetishfuel', 'fridge', 'fridgebrilliance',
    'fridgehorror', 'funny', 'headscratchers', 'heartwarming', 'highoctanenightmarefuel',
    'horrible', 'narm', 'nightmarefuel', 'shockingelimination', 'thatoneboss', 'thescrappy',
    'whatanidiot', 'ymmv',

    # Ignored types that we may add in future
    'allblue', 'shoutout', 'usefulnotes', 'whamepisode',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer',
    'creatorkiller', 'crimeandpunishmentseries', 'darthwiki', 'dieforourship',
    'directlinetotheauthor', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname',
    'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 'hellisthatnoise', 'hoyay',
    'imagelinks', 'images', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect',
    'memes', 'pantheon', 'quotes', 'recap', 'referencedby', 'ride', 'sandbox', 'selfdemonstrating',
    'slidingscale', 'soyouwantto', 'sugarwiki', 'thatoneboss', 'trivia', 'tropeco', 'tropers',
    'tropertales', 'troubledproduction', 'turnofthemillennium', 'warpthataesop', 'wmg',
    'workpagesinmain', 'monster', 'wallbangers',
    ]

tvtropes_base = "tvtropes.org"
tvtropes_main = "http://tvtropes.org"
tvtropes_page = tvtropes_main + "/pmwiki/pmwiki.php/"
tvtropes_trope = tvtropes_page + "Main/"
tvtropes_tropeindex = tvtropes_trope + "Tropes"

def test_redirect(url):
    '''
    Find if a url redirects
    If it does, return that new url
    '''
    # Remove Tvtropes redirect tag
    redirect_index = url.rfind("?from=")
    final_url = None
    if redirect_index > 0:
        url = url[0:redirect_index]
    if url in known_redirects:
        final_url = known_redirects[url]
    else:
        logging.debug("Testing redirect for %s", url)
        req = urllib2.Request(url)
        try:
            res = urllib2.urlopen(req)
        except urllib2.HTTPError:
            logging.error("%s could not be found", url)
            return None
        except:
            logging.error("Unknown error opening %s", url)
            logging.error("%s", sys.exc_info()[0])
            return None
        final_url = res.geturl()
        # Remove Tvtropes redirect tag
        redirect_index = final_url.rfind("?from=")
        if redirect_index > 0:
            final_url = final_url[0:redirect_index]
        known_redirects[url] = final_url
    return final_url

def identify_url(url, parent_name=None):
    '''
    Identify page type by parsing the url
    '''
    url_components = url.split('/')
    url_type = url_components[-2]
    url_name = url_components[-1]

    # Simple Cases.  Page Url is .../Type/Name
    # If we're ignoring this page type -> return None
    if any(url_type.lower() == ignored for ignored in ignoredTypes):
        logging.info("Ignored Type: %s", url_type)
        page_type = None
        page_key = None
    # If this is a media url -> return "media", type/name
    elif any(url_type.lower() == media for media in allowedMedia):
        page_type = "media"
        page_key = url_type + '/' + url_name
    # If this is a trope url -> return "trope", name
    elif url_type == "Main":
        page_type = "trope"
        page_key = url_name

    # Trickier Cases. SubPages where we have the parent_name because we came from that page
    # Ignored types for trope sub-pages
    elif url_type == parent_name and any(url_name.lower() == media for media in ignoredTypes):
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
    elif url_type == parent_name and any(url_name.lower() == media for media in allowedMedia):
        page_type = "tropeSubPage"
        page_key = parent_name
    # Sometimes a name is shortened for sub-pages.  This is really annoying.
    # If this is a media sub-page with a known alias -> return "mediaSubPage", mediaName
    elif parent_name in known_aliases:
        if url_type == known_aliases[parent_name] and "Tropes" in url_name:
            page_type = "mediaSubPage"
            page_key = parent_name
        elif (url_type == known_aliases[parent_name]
              and any(url_name.lower() == media for media in allowedMedia)):
            page_type = "tropeSubPage"
            page_key = parent_name
        elif url_type == known_aliases[parent_name]:
            logging.warning("Known Alias but not a Recognised SubPage: %s", url)
            page_type = None
            page_key = None
        else:
            logging.warning("Unknown Page Type: %s", url)
            page_type = None
            page_key = None

    # Complicated Cases. For the first cases we have Name because we came from that page
    # What if a page links to a sub-page for another trope
    elif any(url_name.lower() == media for media in allowedMedia):
        test_url = tvtropes_trope + url_type
        logging.info("Possibly a link to a sub-page not from a parent %s", url)
        logging.info("Testing for %s", test_url)
        result = test_redirect(test_url)
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

def parse_page(url, options=None):
    '''
    Extract all relevant information from url
    options exists to aid parsing sub-pages
    maybe it's scope will be expanded in future
    '''
    global dbcursor
    global dbconnection

    # Load Page
    html = BeautifulSoup(urllib.urlopen(url))

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
        page_type, page_key = identify_url(url)

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
    elif url not in urls_visited:
        logging.info("Creating New Entry")
        if page_type == "media":
            DBTools.add_media(dbconnection, page_key, url,
                              html.find('title').string.replace(" - TV Tropes", ""))
        elif page_type == "trope":
            DBTools.add_trope(dbconnection, page_key, url,
                              html.find('title').string.replace(" - TV Tropes", ""))

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
            initial_url = testlink['href'].encode('ascii', 'ignore')
            final_url = None
            # Save some time not bothering to follow external links
            if tvtropes_page not in initial_url:
                continue
            final_url = test_redirect(initial_url)

            # Redirect unresolved
            if not final_url:
                continue
            # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
            if tvtropes_page not in initial_url:
                continue
            # Found the first link worth following
            else:
                link = testlink
                break
        # Verify we have a link
        if not link:
            continue
        entry_type, entry_key = identify_url(final_url, page_key.split('/')[-1])

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
                DBTools.add_relation(dbconnection, page_key, entry_key, 1, 1)
            # Harvest urls to follow
            if final_url not in urls_visited:
                # Add link to link database
                if entry_type == "trope":
                    if initial_url not in new_urls:
                        new_urls.append(initial_url)
                        DBTools.add_url(dbconnection, initial_url, final_url)
                # We've got a bunch of sub-pages for this media
                # Immediately go get subpage information
                elif entry_type == "mediaSubPage":
                    if options:
                        logging.warning("A sub-subPage or subPages refer to each other")
                        logging.warning("Skipping %s", final_url)
                        continue
                    parse_page(final_url, {"MediaSubPage" : page_key})
                # Franchise pages sometimes just link to each media subpage
                # In this case we should investigate each of those links,
                # but not associate them to the Franchise page
                elif page_key.split('/')[0] == "Franchise" and entry_type == "media":
                    # Add link to link database
                    if initial_url not in new_urls:
                        new_urls.append(initial_url)
                        DBTools.add_url(dbconnection, initial_url, final_url)
                elif entry_type == "media":
                    if initial_url not in new_urls and final_url != tvtropes_page + page_key:
                        new_urls.append(initial_url)
                        DBTools.add_url(dbconnection, initial_url, final_url)
                else:
                    logging.warning("Not currently considering: %s", final_url)
        # Save media associated to trope, check their urls
        elif page_type == "trope":
            # Make a note of this connection
            if entry_type == "media":
                DBTools.add_relation(dbconnection, entry_key, page_key, 1, -1)
            # Harvest urls to follow
            if final_url not in urls_visited:
                # Add link to link database
                if entry_type == "media":
                    if initial_url not in new_urls:
                        DBTools.add_url(dbconnection, initial_url, final_url)
                        new_urls.append(initial_url)
                # If this is a super-trope page, add tropes to list
                elif entry_type == "trope":
                    if initial_url not in new_urls and final_url != tvtropes_trope + page_key:
                        new_urls.append(initial_url)
                        DBTools.add_url(dbconnection, initial_url, final_url)
                # This tropes media have been split into types, go explore them all now
                elif entry_type == "tropeSubPage":
                    if options:
                        logging.warning("A sub-subPage or subPages refer to each other")
                        logging.warning("Skipping %s", final_url)
                        continue
                    parse_page(final_url, {"TropeSubPage" : page_key})
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
                previous_url = tvtropes_main + previous['href']
                previous_redirect = test_redirect(previous_url.encode('ascii', 'ignore'))
                if previous_redirect:
                    previous_type, previous_key = identify_url(previous_redirect)
                    if (previous_redirect not in urls_visited
                            and previous_url not in new_urls and previous_type):
                        new_urls.append(previous_url)
                        DBTools.add_url(dbconnection, previous_url, previous_redirect)
            if current:
                current_url = tvtropes_main + current['href']
                current_redirect = test_redirect(current_url.encode('ascii', 'ignore'))
                if current_redirect:
                    current_type, current_key = identify_url(current_redirect)
                    if current_type:
                        if page_key != current_key:
                            DBTools.add_index(dbconnection, page_key, current_key)
                        if current_redirect not in urls_visited and current_url not in new_urls:
                            new_urls.append(current_url)
                            DBTools.add_url(dbconnection, current_url, current_redirect)
            if subsequent:
                subsequent_url = tvtropes_main + subsequent['href']
                subsequent_redirect = test_redirect(subsequent_url.encode('ascii', 'ignore'))
                if subsequent_redirect:
                    subsequent_type, subsequent_key = identify_url(subsequent_redirect)
                    if (subsequent_redirect not in urls_visited
                            and subsequent_url not in new_urls and subsequent_type):
                        new_urls.append(subsequent_url)
                        DBTools.add_url(dbconnection, subsequent_url, subsequent_redirect)
    elif do_related:
        logging.warning("No Relation Table found at %s", final_url)

    # Done Parsing, add to DB
    logging.debug("%s finished", url)
    urls_visited.add(url)
    DBTools.commit_page(dbconnection, url)
    return 0

# Recurse through all links found
def recur_search(url=None):
    '''
    Use a recursive depth-first search across all of TvTropes
    Number of urls accessed restricted by the LIMIT option
    '''
    global counter
    if not url:
        url = new_urls.popleft()

    # Don't follow external links
    if "tvtropes.org" not in url:
        logging.info("External Link Ignored: %s", url)
        return

    if limit != -1 and counter >= limit:
        logging.critical("Exceeded limit")
        dbconnection.commit()
        dbconnection.close()
        sys.exit()

    final_url = test_redirect(url)
    if not final_url:
        return
    counter = counter + 1
    page_type, page_title = identify_url(final_url)
    # Code snippet to make ordinal numbers
    # http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n/10%10 != 1)*(n%10 < 4)*n%10::4])
    logging.info("Processing %s url", ordinal(counter))
    logging.info("%s", final_url)

    # Ignore links with bad types
    if page_type in ignoredTypes:
        logging.info("Link to unintersting page ignored")
        return
    # Ignore links already searched
    if final_url in urls_visited:
        logging.debug("Link already discovered")
        if new_urls:
            recur_search(new_urls.popleft())
        return

    logging.info("%s: %s", page_title, page_type)

    parse_page(final_url)
    # If parsing is successful, add any original url to urls_visited too
    #if not parse_page(final_url):
    #    if final_url != url:
    #        urls_visited.add(url)

    # Recurse this search through all untested urls
    if new_urls:
        recur_search(new_urls.popleft())

    return

def loop_search():
    '''
    Use a breadth-first search across all of TvTropes
    Number of urls accessed restricted by the LIMIT option
    '''
    current_count = 0

    while new_urls:
        url = new_urls.popleft()
        if limit > 0 and current_count >= limit:
            logging.critical("Exceeded limit")
            break

        # Don't follow external links
        if "tvtropes.org" not in url:
            logging.info("External Link Ignored: %s", url)
            continue

        final_url = test_redirect(url)
        if not final_url:
            logging.info("%s could not be resolved", url)
            continue
        current_count = current_count + 1

        page_type, page_title = identify_url(final_url)
        # Code snippet to make ordinal numbers
        # http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
        ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n/10%10 != 1)*(n%10 < 4)*n%10::4])

        # Ignore links with bad types
        if page_type in ignoredTypes:
            logging.info("Link to unintersting page ignored")
            continue
        # Ignore links already searched
        if final_url in urls_visited:
            logging.debug("Link already discovered")
            current_count = current_count -1
            continue
        logging.info("Processing %s url", ordinal(current_count))
        logging.info("%s", final_url)

        logging.info("%s: %s", page_title, page_type)
        parse_page(final_url)

    dbconnection.commit()
    dbconnection.close()
    return

#def start_at_top():
#    # Start the recursive search at the top level trope index
#    htmltest = urllib.urlopen(tvtropes_tropeindex).readlines()
#    interesting = False
#    commentblock = '<!&#8212;index&#8212;>'
#
#    # Parsing HTML as text
#    # This is kinda hacky but I can't be bothered changing it for now
#    for line in htmltest:
#        if commentblock in line:
#            interesting = not interesting
#        if not interesting:
#            continue
#        else:
#            if "class='plus'" in line:
#                index = re.search("title=.*>(.*)<", line).group(1)
#                url = re.search("href='([^\s]*)'", line).group(1)
#                print 'index: ' + index + '\t' + url
#            elif "href" in line:
#                category = re.search("title=.*>(.*)<", line).group(1)
#                url = re.search("href='([^\s]*)'", line).group(1)
#                print 'category: ' + category + '\t' + url

if __name__ == "__main__":
    f = open("Scrape.log", 'a')
    f.write('\n---------------------------------------------------------\n')
    f.close()

    log_format = '[%(asctime)s] %(filename)-20s %(levelname)8s - %(message)s'
    console_format = '%(filename)-20s %(levelname)8s : %(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO,
                        filename='Scrape.log', filemode='a')

    consoleOut = ColourStreamHandler.ColourStreamHandler
    consoleOut.setFormatter(logging.Formatter(console_format))
    logging.getLogger().addHandler(consoleOut)

    dbconnection = DBTools.initialise_db()
    dbcursor = dbconnection.cursor()

    unreadUrls, oldUrls = DBTools.get_urls(dbconnection)
    redirects = DBTools.get_redirects(dbconnection)
    for url in oldUrls:
        urls_visited.add(url[0])
    for url in unreadUrls:
        new_urls.append(url[0])
    for redirect in redirects:
        known_redirects[redirect[0]] = redirect[1]

    # Search Tvtropes
    start_url = "http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury"

    if new_urls:
        logging.debug("Starting New Run with %i urls to search", len(new_urls))
        loop_search()
    else:
        logging.debug("Starting New Run fresh from %s", start_url)
        DBTools.add_url(dbconnection, start_url)
        recur_search(start_url)

    # TESTING AREA
    # Trope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury")

    # Media parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Manga/MahouSenseiNegima")

    # SuperTrope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ActionGirl")
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/ActionGirl/AnimatedFilms")
