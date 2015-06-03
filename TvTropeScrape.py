import urllib
import urllib2
import sys
import re
import logging
from collections import deque
from bs4 import BeautifulSoup

from DBTools import *
import json 
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
import sqlite3

counter = 0
limit = 50

DatabaseName = "TropeStats.db"
dbconnection = None
dbcursor = None
new_urls = deque()
known_redirects = {}
urls_visited = set()

logging.basicConfig(filename = 'scrape.log', level = logging.INFO, filemode = "w")
logging.getLogger().addHandler(logging.StreamHandler())

# Sometimes TvTropes doesn't refer to media with the right name
# This is dumb and requires hacks.  Probably I should make this a config file.  Maybe later.
known_aliases = {
    'BuffyTheVampireSlayer' : 'Buffy'
    }

allowedMedia = [
    'anime',
    'comicbook',
    'comics',
    'comicstrip',
    'creator',
    'discworld',
    'disney',               # Apparently big enough to be it's own type of media.  Who knew?
    'fanfic',
    'film',
    'franchise',
    'letsplay',
    'lightnovel',
    'literature',
    'liveactiontv',
    'manga',
    'machinima',
    'magazine',
    'music',
    'myth',
    'newmedia',
    'podcast',
    'radio',
    'roleplay',
    'series',
    'tabletopgame',
    'theatre',
    'toys',
    'videogame',
    'visualnovel',
    'webanimation',
    'webcomic',
    'weboriginal',
    'website',
    'webvideo',
    'westernanimation',
    'wiki',
    ]

# Can I work out a way to scrape this?  Maybe using the full list and hardcode some specific allowed types?
# This will do for now
ignoredTypes = [
    # Ignore languages other than English (for now)
    'de', 'eo', 'es', 'fi', 'fr', 'hu', 'it', 'itadministrivia', 'itdarthwiki', 'itsugarwiki', 'no', 'pl', 'pt', 'ro', 'se', 
    
    # Ignore YMMV type namespaces
    'aatafovs', 'accidentalnightmarefuel', 'alternativecharacterinterpretation', 'andthefandomrejoiced', 'analysis', 'awesome', 
    'awesomebosses', 'awesomebutimpractical', 'awesomemusic', 'badass', 'betterthanitsounds', 'fetishfuel', 'fridge', 'fridgebrilliance', 'fridgehorror', 
    'funny', 'headscratchers', 'highoctanenightmarefuel', 'horrible', 'narm', 'nightmarefuel', 'shockingelimination', 'thatoneboss',
    'thescrappy', 'whatanidiot', 'ymmv',

    # Ignored types that we may add in future
    'shoutout', 'usefulnotes', 'wrestling', 'script',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer', 'creatorkiller', 'crimeandpunishmentseries', 
    'darthwiki', 'dieforourship', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname', 'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 
    'hellisthatnoise', 'hoyay', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect', 'memes', 'pantheon', 'pinball', 
    'quotes', 'reallife', 'recap', 'referencedby', 'ride', 'sandbox', 'selfdemonstrating', 'slidingscale', 'soyouwantto', 'sugarwiki', 'thatoneboss',
    'trivia', 'tropeco', 'tropers', 'tropertales', 'troubledproduction', 'turnofthemillennium', 'warpthataesop', 'wmg', 'workpagesinmain',
    'monster', 'wallbangers',
    ]

# Namespaces allowed (basically super-tropes), they have a main page:
# LyricalDissonance
# NoodleIncident
# RunningGag
# Woobie
# Wham Episode
# TropeNamers - Special Parsing for this I think
# TearJerker
# TakeThat
# ShoutOut
# Radar
# LampshadeHanging
# FiveManBad
# FiveManBand
# FamousLastWords
# EpicFail
# EnsembleDarkHorse
# Earworm
# Creator
# CrazyPrepared
# ContinuityNod
# BerserkButton
# ArtEvolution
# AnachronismStew 
# ActorAllusion

tvtropes_base = "tvtropes.org"
tvtropes_main = "http://tvtropes.org"
tvtropes_tropeindex = tvtropes_main + "/pmwiki/pmwiki.php/Main/Tropes"

def test_redirect(url):
    # Remove Tvtropes redirect tag
    redirectIndex = url.rfind("?from=") 
    finalURL = None
    if redirectIndex > 0:
        url = url[0:redirectIndex]
    if url in known_redirects:
        finalURL = known_redirects[url]
    else:
        req = urllib2.Request(url)
        try: res = urllib2.urlopen(req)
        except urllib2.HTTPError:
            logging.error("%s could not be found", url)
        finalURL = res.geturl()
        # Remove Tvtropes redirect tag
        redirectIndex = finalURL.rfind("?from=") 
        if redirectIndex > 0:
            finalURL = finalURL[0:redirectIndex]
        known_redirects[url] = finalURL
    return finalURL

def identify_url(url, inputKey = None):
    urlComponents = url.split('/')
    # If we're ignoring this page type -> return None
    if any(category == urlComponents[-2].lower() for category in ignoredTypes):
        logging.info("Ignored Type: %s", urlComponents[-2])
        return None, None
    # If this is a media url -> return "media", type/name
    elif any(media == urlComponents[-2].lower() for media in allowedMedia):
        pageType = "media"
        pageKey = urlComponents[-2] + '/' + urlComponents[-1]
    # If this is a trope url -> return "trope", name
    elif "main" in urlComponents[-2].lower():
        pageType = "trope"
        pageKey = urlComponents[-1]
    # If this is a media sub-page -> return "mediaSubPage", mediaName
    elif urlComponents[-2] == inputKey and "Tropes" in urlComponents[-1]:
        pageType = "mediaSubPage"
        pageKey = inputKey 
    # If this is a media sub-page with a known alias -> return "mediaSubPage", mediaName
    elif inputKey in known_aliases:
        if urlComponents[-2] == known_aliases[inputKey] and "Tropes" in urlComponents[-1]:
            pageType = "mediaSubPage"
            pageKey = inputKey 
        elif urlComponents[-2] == known_aliases[inputKey]:
            logging.warning("Known Alias but not a Media SubPage: %s", url)
            return None, None
        else:
            logging.warning("Unknown Page Type: %s", url)
            return None, None
    # If this is a trope sub-page -> return "tropeSubPage", tropeName
    elif urlComponents[-2] == inputKey and any(media in urlComponents[-1].lower() for media in allowedMedia):
        pageType = "tropeSubPage"
        pageKey = inputKey
    # What if a page links to a sub-page for another trope
    #elif any(media in urlComponents[-1].lower() for media in allowedMedia):
    #    testUrl = tvtropes_main + "/pmwiki/pmwiki.php/Main/" + urlComponents[-2]
    #    print "Testing Url: ", testUrl
    #    result = test_redirect(testUrl)
    #    print result
    else:
        logging.error("Unknown Url: %s\nOn page: \%", url, inputKey)
        return None, None
    return pageType, pageKey

def parse_page(url, options = None):
    global dbcursor
    global dbconnection
    
    # Load Page
    html = BeautifulSoup(urllib.urlopen(url))

    pageType = None
    pageKey = None
    # Get page information from options
    if options:
        for key in options:
            if key == "MediaSubPage":
                pageType = "media"
                pageKey = options[key]
            if key == "TropeSubPage":
                pageType = "trope"
                pageKey = options[key]
    # If that didn't work try and work out info from url
    if not pageType or not pageKey:
        pageType, pageKey = identify_url(url)

    # Find text block
    textblock = html.find(attrs={"id": "wikitext"})
    
    # If there is no text block, give up
    if not textblock:
        logging.error("%s has no wikitext", url)
        return 1

    # Save this page information
    # Fix this for the sub-page cases
    if options:
        if any(x in options for x in ["MediaSubPage","TropeSubPage"]):
            logging.info("%s\nAdding to Entry: %s", url, pageKey)
    elif url not in urls_visited:
        logging.info("Creating New Entry")
        if pageType == "media":
            add_media(dbconnection, pageKey, url, html.find('title').string.replace(" - TV Tropes", ""))
        if pageType == "trope":
            add_trope(dbconnection, pageKey, url, html.find('title').string.replace(" - TV Tropes", ""))
        
    # There are some examples - Let's go find them    
    items = textblock.find_all('li')
    nSubTags = 0
    for item in items:
        # Skip any 'li' nested within 'li'
        if nSubTags > 0:
            nSubTags -= 1
            continue
        else:
            nSubTags = len(item.find_all('li'))
        
        # Find the first relevant link in a line
        links = item.find_all('a')
        link = None
        initialUrl = None
        finalUrl = None
        for testlink in links:
            initialUrl = testlink['href']
            finalUrl = None
            # Save some time not bothering to follow external links
            if tvtropes_base not in testlink['href']:
                continue
            finalUrl = test_redirect(testlink['href']) 
            
            # Redirect unresolved
            if not finalUrl:
                continue
            # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
            if tvtropes_base not in testlink['href']:
                continue
            # Found the first link worth following
            else:
                link = testlink
                break
        # Verify we have a link
        if not link:
            continue
        entryType, entryKey = identify_url(finalUrl, pageKey.split('/')[-1])
       
        # Assign results to appropriate dictionary
        # Save tropes associated to this media, check their urls
        if pageType == "media":
            if entryType == "trope":
                add_relation(dbconnection, pageKey, entryKey, 1, 1)
                # Add link to link database
                if initialUrl not in new_urls and finalUrl not in urls_visited:
                    new_urls.append(initialUrl)
                    add_url(dbconnection, initialUrl, finalUrl)
            # We've got a bunch of sub-pages for this media
            elif entryType == "mediaSubPage":
                # Immediately go get subpage information 
                parse_page(finalUrl, {"MediaSubPage" : pageKey})
            # Franchise pages sometimes just link to each media subpage
            # In this case we should investigate each of those links, but not associate them to the Franchise page
            elif pageKey.split('/')[0] == "Franchise" and entryType == "media":
                # Add link to link database
                if initialUrl not in new_urls and finalUrl not in urls_visited:
                    new_urls.append(initialUrl)
                    add_url(dbconnection, initialUrl, finalUrl)
            elif entryType == "media" and initialUrl not in new_urls and initialUrl not in urls_visited:
                new_urls.append(initialUrl)
                add_url(dbconnection, initialUrl, finalUrl)
            else:
                print "Not currently considering: ", finalUrl
        # Save media associated to trope, check their urls
        elif pageType == "trope":
            if entryType == "media":
                add_relation(dbconnection, entryKey, pageKey, 1, -1)
                # Add link to link database
                if initialUrl not in new_urls and finalUrl not in urls_visited:
                    test = add_url(dbconnection, initialUrl, finalUrl)
                    if test == "Debug":
                        print
                        print initialUrl
                        print finalUrl
                        print
                        print new_urls
                        print urls_visited
                        print
                    new_urls.append(initialUrl)
            # If this is a super-trope page, add tropes to list
            elif entryType == "trope":
                # Add link to link database
                if initialUrl not in new_urls and finalUrl not in urls_visited:
                    new_urls.append(initialUrl)
                    add_url(dbconnection, initialUrl, finalUrl)
            # This tropes media have been split into types, go explore them all now
            elif entryType == "tropeSubPage":
                parse_page(finalUrl, {"TropeSubPage" : pageKey})
            else:
                print "Not currently considering: ", finalUrl

    # Map out related pages
    doRelated = True
    if options:
        if "MediaSubPage" in options:
            doRelated = False
        if "TropeSubPage" in options:
            doRelated = False

    if doRelated:    
        related = html.find_all(attrs={"class": "wiki-walk"})[0]
        rows = related.find_all(attrs={"class": "walk-row"})
        for row in rows:
            items = row.find_all('span')
            previous = items[0].find('a')
            current = items[1].find('a')
            subsequent = items[2].find('a')
            if previous:
                previousUrl = tvtropes_main + previous['href']
                previousRedirect = test_redirect(tvtropes_main + previous['href'])
                previousType, previousKey = identify_url(previousRedirect)
                if previousRedirect not in urls_visited and previousUrl not in new_urls and previousType:
                    new_urls.append(previousUrl)
                    add_url(dbconnection, previousUrl, previousRedirect)
            if current:
                currentUrl = tvtropes_main + current['href']
                currentRedirect = test_redirect(currentUrl)
                currentType, currentKey = identify_url(currentRedirect)
                if currentType:
                    if pageKey != currentKey:
                        add_index(dbconnection, pageKey, currentKey)
                    if currentRedirect not in urls_visited and currentUrl not in new_urls:
                        new_urls.append(currentUrl)
                        add_url(dbconnection, currentUrl, currentRedirect)
            if subsequent:    
                subsequentUrl = tvtropes_main + subsequent['href']
                subsequentRedirect = test_redirect(subsequentUrl)
                subsequentType, subsequentKey = identify_url(subsequentRedirect)
                if subsequentRedirect not in urls_visited and subsequentUrl not in new_urls and subsequentType:
                    new_urls.append(subsequentUrl)
                    add_url(dbconnection, subsequentUrl, subsequentRedirect)
   
    # Done Parsing, add to DB
    urls_visited.add(url)
    commit_page(dbconnection, url)
    return 0

# Recurse through all links found
def recur_search(url = None):
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

    counter = counter + 1
    finalUrl = test_redirect(url)
    pageType, pageTitle = identify_url(finalUrl)
    logging.info("%s: %s", counter, finalUrl)

    # Ignore links with bad types
    if pageType in ignoredTypes:
        logging.info("Link to unintersting page ignored")
        return
    # Ignore links already searched
    if finalUrl in urls_visited:
        logging.info("Link already discovered")
        return

    logging.info("%s: %s", pageTitle, pageType)

    parse_page(finalUrl)
    # If parsing is successful, add any original url to urls_visited too
    #if not parse_page(finalUrl):
    #    if finalUrl != url:
    #        urls_visited.add(url)

    # Recurse this search through all untested urls
    if new_urls:
        recur_search(new_urls.popleft())

    return

def start_at_top():
    # Start the recursive search at the top level trope index
    htmltest = urllib.urlopen(tvtropes_tropeindex).readlines()
    interesting = False
    commentblock = '<!&#8212;index&#8212;>'

    # Parsing HTML as text
    # This is kinda hacky but I can't be bothered changing it for now
    for line in htmltest:
        if commentblock in line:
            interesting = not interesting
        if not interesting:
            continue
        else:
            if "class='plus'" in line:
                index = re.search("title=.*>(.*)<", line).group(1)
                url = re.search("href='([^\s]*)'", line).group(1)
                print 'index: ' + index + '\t' + url
            elif "href" in line:
                category = re.search("title=.*>(.*)<", line).group(1)
                url = re.search("href='([^\s]*)'", line).group(1)
                print 'category: ' + category + '\t' + url

if __name__ == "__main__":
    # Let's set up some tests
    outJSON = open("test.json", "w")
    dbconnection = initialise_db() 
    dbcursor = dbconnection.cursor()
   
    unreadUrls, oldUrls = get_urls(dbconnection)
    redirects = get_redirects(dbconnection)
    for url in oldUrls:
        urls_visited.add(url[0])
    for url in unreadUrls:
        new_urls.append(url[0])
    for redirect in redirects:
        known_redirects[redirect[0]] = redirect[1]

    # Trope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury") 

    # Media parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Manga/MahouSenseiNegima") 

    # SuperTrope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ActionGirl") 
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/ActionGirl/AnimatedFilms") 
    
    # Recursive search test
    testUrl = "http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury"
    if new_urls:
        recur_search()
    else:
        add_url(dbconnection, testUrl)
        recur_search(testUrl)

    dbconnection.commit()
    dbconnection.close()
#    print "URLS TO VISIT"
#    for URL in new_urls:
#        print URL
#    print
#    print "MEDIA INDEX:"
#    print json.dumps(media, cls=SetEncoder) 
#    json.dump(media, outJSON, indent = 4, cls=SetEncoder)
#    print
#    print "TROPE INDEX:"
#    print json.dumps(tropes, cls=SetEncoder)
#    json.dump(tropes, outJSON, indent = 4, cls=SetEncoder)
#    print
#    print "URLS VISITED:"
#    print urls_visited
#    print
#    print "KNOWN REDIRECTS:"
#    for redirect in known_redirects:
#        print redirect, ": ", known_redirects[redirect]
#    print

