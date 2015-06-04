import urllib
import urllib2
import sys
import re
from collections import deque
from bs4 import BeautifulSoup
import logging
import ColourStreamHandler

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
limit = 200 

DatabaseName = "TropeStats.db"
dbconnection = None
dbcursor = None
new_urls = deque()
known_redirects = {}
urls_visited = set()

f = open("Scrape.log", 'a')
f.write('\n---------------------------------------------------------\n')
f.close()

logFormat = '[%(asctime)s] %(filename)-20s %(levelname)8s - %(message)s'
consoleFormat = '%(filename)-20s %(levelname)8s : %(message)s'
logging.basicConfig(format=logFormat, level=logging.DEBUG, filename='Scrape.log', filemode = 'a')

#consoleOut = logging.StreamHandler()
#consoleOut.setFormatter(logging.Formatter(consoleFormat))
#logging.getLogger().addHandler(consoleOut)

consoleOut = ColourStreamHandler.ColourStreamHandler
consoleOut.setFormatter(logging.Formatter(consoleFormat))
logging.getLogger().addHandler(consoleOut)

# Sometimes TvTropes doesn't refer to media with the right name
# This is dumb and requires hacks.  Probably I should make this a config file.  Maybe later.
known_aliases = {
    'BuffyTheVampireSlayer' : 'Buffy'
    }

allowedMedia = [
    'advertising',
    'anime',
    'animeandmanga',
    'animation',
    'arg',
    'blog',
    'comicbook',
    'comicbooks',
    'comics',
    'comicstrip',
    'creator',
    'discworld',
    'disney',               # Apparently big enough to be it's own type of media.  Who knew?
    'fanfic',
    'fanworks',
    'film',
    'franchise',
    'letsplay',
    'lightnovel',
    'literature',
    'liveactiontv',
    'manga',
    'machinima',
    'magazine',
    'media',
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
    'videogames',
    'visualnovel',
    'visualnovels',
    'webanimation',
    'webcomic',
    'webcomics',
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
    'other', 'pinball', 'script', 'shoutout', 'usefulnotes', 'wrestling',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer', 'creatorkiller', 'crimeandpunishmentseries', 
    'darthwiki', 'dieforourship', 'directlinetotheauthor', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname', 'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 
    'hellisthatnoise', 'hoyay', 'images', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect', 'memes', 'pantheon', 
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
tvtropes_page = tvtropes_main + "/pmwiki/pmwiki.php/"
tvtropes_trope = tvtropes_page + "Main/"
tvtropes_tropeindex = tvtropes_trope + "Tropes"

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
            return None
        finalURL = res.geturl()
        # Remove Tvtropes redirect tag
        redirectIndex = finalURL.rfind("?from=") 
        if redirectIndex > 0:
            finalURL = finalURL[0:redirectIndex]
        known_redirects[url] = finalURL
    return finalURL

def identify_url(url, parentName = None):
    urlComponents = url.split('/')
    urlType = urlComponents[-2]
    urlName = urlComponents[-1]
    
    # Simple Cases.  Page Url is .../Type/Name
    # If we're ignoring this page type -> return None
    if any(urlType.lower() == ignored for ignored in ignoredTypes):
        logging.info("Ignored Type: %s", urlType)
        return None, None
    # If this is a media url -> return "media", type/name
    elif any(urlType.lower() == media for media in allowedMedia):
        pageType = "media"
        pageKey = urlType + '/' + urlName
    # If this is a trope url -> return "trope", name
    elif urlType == "Main":
        pageType = "trope"
        pageKey = urlName

    # Trickier Cases. SubPages where er have the parentName because we came from that page
    # Ignored types for trope sub-pages
    elif urlType == parentName and any(urlName.lower() == media for media in ignoredTypes):
        logging.info("Ignored Type: %s", urlType)
        return None, None
    # MediaSubPage Url is something like /MediaName/TropesAtoC
    # If this is a media sub-page -> return "mediaSubPage", mediaName
    elif urlType == parentName and re.search("[A-Za-z][tT]o[A-Za-z]$", urlName):
        pageType = "mediaSubPage"
        pageKey = parentName 
    # TropeSubPage Url is something like /TropeName/MediaType
    # If this is a trope sub-page -> return "tropeSubPage", tropeName
    elif urlType == parentName and any(urlName.lower() == media for media in allowedMedia):
        pageType = "tropeSubPage"
        pageKey = parentName
    # Sometimes a name is shortened for sub-pages.  This is really annoying.
    # If this is a media sub-page with a known alias -> return "mediaSubPage", mediaName
    elif parentName in known_aliases:
        if urlType == known_aliases[parentName] and "Tropes" in urlName:
            pageType = "mediaSubPage"
            pageKey = parentName 
        elif urlType == known_aliases[parentName] and any(urlName.lower() == media for media in allowedMedia):
            pageType = "tropeSubPage"
            pageKey = parentName
        elif urlType == known_aliases[parentName]:
            logging.warning("Known Alias but not a Recognised SubPage: %s", url)
            return None, None
        else:
            logging.warning("Unknown Page Type: %s", url)
            return None, None
    
    # Complicated Cases. For the first cases we have Name because we came from that page
    # What if a page links to a sub-page for another trope
    elif any(urlName.lower() == media for media in allowedMedia):
        testUrl = tvtropes_trope + urlType
        logging.info("Possibly a link to a sub-page not from a parent %s", url)
        logging.info("Testing for %s", testUrl)
        result = test_redirect(testUrl)
        if result:
            logging.info("Found a trope page")
            pageType = "trope"
            pageKey = urlType
        else:
            return None, None
    else:
        logging.error("Unknown Url: %s", url)
        logging.error("On page: %s with %s/%s", parentName, urlType, urlName)
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
            logging.info("%s", url)
            logging.info("Adding to Entry: %s", pageKey)
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
        # Find the first relevant link in a line
        links = item.find_all('a')
        link = None
        initialUrl = None
        finalUrl = None
        for testlink in links:
            # Sometimes links contain unicode characters.  I'm guessing that's never something I want but this is kinda hacky
            initialUrl = testlink['href'].encode('ascii', 'ignore')
            finalUrl = None
            # Save some time not bothering to follow external links
            if tvtropes_base not in initialUrl:
                continue
            finalUrl = test_redirect(initialUrl) 
            
            # Redirect unresolved
            if not finalUrl:
                continue
            # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
            if tvtropes_base not in initialUrl:
                continue
            # Found the first link worth following
            else:
                link = testlink
                break
        # Verify we have a link
        if not link:
            continue
        entryType, entryKey = identify_url(finalUrl, pageKey.split('/')[-1])
       
        # Skip any 'li' nested within 'li'
        # Only skip if they aren't subPages (thanks Buffy)
        if nSubTags > 0:
            nSubTags -= 1
            if entryType != "mediaSubPage" and entryType != "tropeSubPage":
                continue
        else:
            nSubTags = len(item.find_all('li'))
        
        # Assign results to appropriate dictionary
        # Save tropes associated to this media, check their urls
        if pageType == "media":
            if entryType == "trope":
                add_relation(dbconnection, pageKey, entryKey, 1, 1)
            if finalUrl not in urls_visited:
                # Add link to link database
                if entryType == "trope":
                    if initialUrl not in new_urls:
                        new_urls.append(initialUrl)
                        add_url(dbconnection, initialUrl, finalUrl)
                # We've got a bunch of sub-pages for this media
                # Immediately go get subpage information 
                elif entryType == "mediaSubPage":
                    parse_page(finalUrl, {"MediaSubPage" : pageKey})
                # Franchise pages sometimes just link to each media subpage
                # In this case we should investigate each of those links, but not associate them to the Franchise page
                elif pageKey.split('/')[0] == "Franchise" and entryType == "media":
                    # Add link to link database
                    if initialUrl not in new_urls:
                        new_urls.append(initialUrl)
                        add_url(dbconnection, initialUrl, finalUrl)
                elif entryType == "media":
                    if initialUrl not in new_urls and finalUrl != tvtropes_page + pageKey:
                        new_urls.append(initialUrl)
                        add_url(dbconnection, initialUrl, finalUrl)
                else :
                    logging.warning("Not currently considering: %s", finalUrl)
        # Save media associated to trope, check their urls
        elif pageType == "trope":
            if entryType == "media":
                add_relation(dbconnection, entryKey, pageKey, 1, -1)
            if finalUrl not in urls_visited:
                # Add link to link database
                if entryType == "media":
                    if initialUrl not in new_urls:
                        add_url(dbconnection, initialUrl, finalUrl)
                        new_urls.append(initialUrl)
                # If this is a super-trope page, add tropes to list
                elif entryType == "trope":
                    if initialUrl not in new_urls and finalUrl != tvtropes_trope + pageKey:
                        new_urls.append(initialUrl)
                        add_url(dbconnection, initialUrl, finalUrl)
                # This tropes media have been split into types, go explore them all now
                elif entryType == "tropeSubPage":
                    parse_page(finalUrl, {"TropeSubPage" : pageKey})
                else:
                    logging.warning("Not currently considering: %s", finalUrl)

    # Map out related pages
    doRelated = True
    if options:
        if any(x in options for x in ["MediaSubPage","TropeSubPage"]):
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
                if previousRedirect:
                    previousType, previousKey = identify_url(previousRedirect)
                    if previousRedirect not in urls_visited and previousUrl not in new_urls and previousType:
                        new_urls.append(previousUrl)
                        add_url(dbconnection, previousUrl, previousRedirect)
            if current:
                currentUrl = tvtropes_main + current['href']
                currentRedirect = test_redirect(currentUrl)
                if currentRedirect:
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
                if subsequentRedirect:
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

    finalUrl = test_redirect(url)
    if not finalUrl:
        return
    counter = counter + 1
    pageType, pageTitle = identify_url(finalUrl)
    # Code snippet to make ordinal numbers
    # Taken from http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])
    logging.info("Processing %s url", ordinal(counter))
    logging.info("%s", finalUrl)

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
    
    # Urls to fix
    
    if new_urls:
        logging.debug("Starting New Run with %i urls to search", len(new_urls))
        recur_search()
    else:
        logging.debug("Starting New Run fresh from %s", testUrl)
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

