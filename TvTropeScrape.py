import urllib
import urllib2
import sys
import re
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
limit = 5 

DatabaseName = "TropeStats.db"
dbconnection = None
dbcursor = None

new_urls = deque()
known_redirects = {}
tropes = {}

urls_visited = set()

media = {}
allowedMedia = [
    'anime',
    'comicbook',
    'comics',
    'comicstrip',
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
    'de', 'eo', 'es', 'fi', 'fr', 'hu', 'it', 'itadministrivia', 'itdarthwiki', 'itsugarwiki', 'no', 'pl' 'pt', 'ro', 'se', 
    
    # Ignore YMMV type namespaces
    'aatafovs', 'accidentalnightmarefuel', 'alternativecharacterinterpretation', 'andthefandomrejoiced', 'analysis', 'awesome', 
    'awesomebosses', 'awesomebutimpractical', 'awesomemusic', 'badass', 'betterthanitsounds', 'fetishfuel', 'fridge', 'fridgebrilliance', 'fridgehorror', 
    'funny', 'headscratchers', 'highoctanenightmarefuel', 'horrible', 'narm', 'nightmarefuel', 'shockingelimination', 'thatoneboss',
    'thescrappy', 'whatanidiot', 'ymmv',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer', 'creatorkiller', 'crimeandpunishmentseries', 
    'darthwiki', 'dieforourship', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname', 'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 
    'hellisthatnoise', 'hoyay', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect', 'memes', 'mysteryfiction', 'pantheon', 'pinball', 
    'quotes', 'reallife', 'recap', 'referencedby', 'ride', 'sandbox', 'selfdemonstrating', 'slidingscale', 'soyouwantto', 'sugarwiki', 'thatoneboss',
    'trivia', 'tropeco', 'tropers', 'tropertales', 'troubledproduction', 'turnofthemillennium', 'usefulnotes', 'warpthataesop', 'wmg', 'workpagesinmain',
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
    if redirectIndex > 0:
        url = url[0:redirectIndex]
    if url in known_redirects:
        finalURL = known_redirects[url]
    else:
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)
        finalURL = res.geturl()
        # Remove Tvtropes redirect tag
        redirectIndex = finalURL.rfind("?from=") 
        if redirectIndex > 0:
            finalURL = finalURL[0:redirectIndex]
        known_redirects[url] = finalURL
    return finalURL

def parse_page(url, options = None):
    global dbcursor
    global dbconnection
    
    # Try and work out info from url
    urlComponents = url.split('/')
    pageTitle = urlComponents[-1]
    pageType = urlComponents[-2]
    pageKey = pageType + '/' + pageTitle
    
    # Load Page
    html = BeautifulSoup(urllib.urlopen(url))

    thisPage = None
    # Super trope subpage catching
    if any(media in pageType.lower() for media in allowedMedia):
        thisPage = "media"
    elif "main" in pageType.lower():
        thisPage = "trope"
    else:
        thisPage = "supertrope"
        pageTitle = pageType
    if not thisPage:
        print "Unrecognized Page Type: ", url
        return

    if options:
        for key in options:
            if key == "MediaSubPage":
                thisPage = "media"
                pageKey = options[key]

    # Find text block
    textblock = html.find(attrs={"id": "wikitext"})
    
    # If there is no text block, give up
    if not textblock:
        print url, " has no wikitext"
        return

    # Save this media page information
    if thisPage == "media":
        if pageKey not in media:
            print "Creating New Media Entry"
            media[pageKey] = {}
            media[pageKey]['tropes'] = set()
            media[pageKey]['url'] = url
            media[pageKey]['title'] = html.find('title').string.replace(" - TV Tropes", "")
            media[pageKey]['indicies'] = []
            add_media(dbconnection, pageKey, url, html.find('title').string.replace(" - TV Tropes", ""))
    # Save this trope page information
    elif thisPage == "trope":
        if pageTitle not in tropes:
            print "Creating New Trope Entry"
            tropes[pageTitle] = {}
            tropes[pageTitle]['media'] = set()
            tropes[pageTitle]['url'] = url
            tropes[pageTitle]['title'] = html.find('title').string.replace(" - TV Tropes", "")
            tropes[pageTitle]['indicies'] = []
            add_trope(dbconnection, pageTitle, url, html.find('title').string.replace(" - TV Tropes", ""))
        # We're visiting a top page after visiting subpages
        if 'url' not in tropes[pageTitle]:
            print "Creating New SuperTrope Entry"
            tropes[pageTitle]['url'] = url
            add_trope(dbconnection, pageTitle, url, tropes[pageTitle]['title'])
    # Sub-page, don't add to db (we'll do it when we get to the top page)
    elif pageTitle not in tropes:
        print "Not Creating an Entry - SubTrope"
        tropes[pageTitle] = {}
        tropes[pageTitle]['media'] = set()
        tropes[pageTitle]['title'] = html.find('title').string.replace(" - TV Tropes", "").split('/')[-1].strip()
        tropes[pageTitle]['indicies'] = []
        
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
        entryInfo = None
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
        
        entryInfo = finalUrl.split('/')
        entryKey = entryInfo[-2] + '/' + entryInfo[-1]
       
        # Assign results to appropriate dictionary
        if thisPage == "media":
            # Save tropes associated to this media, check their urls
            if 'main' in entryInfo[-2].lower():
                tropeKey = link['href'].split('/')[-1]
                media[pageKey]['tropes'].add(tropeKey)
                add_relation(dbconnection, pageKey, tropeKey, 1, 1)
                # Add link to link database
                if initialUrl not in new_urls and initialUrl not in urls_visited:
                    new_urls.append(link['href'])
                    add_url(dbconnection, initialUrl, finalUrl)
            # We've got a bunch of sub-pages for this media
            elif entryInfo[-2] == pageTitle and "Tropes" in entryInfo[-1]:
                parse_page(link['href'], {"MediaSubPage" : pageKey})
        elif thisPage == "supertrope" or thisPage == "trope":
            # Save media associated to trope, check their urls
            if any(media in entryInfo[-2].lower() for media in allowedMedia):
                tropes[pageTitle]['media'].add(entryKey)
                add_relation(dbconnection, entryKey, pageTitle, 1, -1)
                # Add link to link database
                if initialUrl not in new_urls and initialUrl not in urls_visited:
                    new_urls.append(link['href'])
                    add_url(dbconnection, initialUrl, finalUrl)
            # If this is a super-trope page, let's go explore the sub-tropes
            elif 'main' in entryInfo[-2].lower():
                # Add link to link database
                if initialUrl not in new_urls and initialUrl not in urls_visited:
                    new_urls.append(link['href'])
                    add_url(dbconnection, initialUrl, finalUrl)
            # This trope media have been split into types, go explore them all now
            elif any(media in entryInfo[-1].lower() for media in allowedMedia):
                parse_page(link['href'])
            else:
                print entryInfo[-1]
                print entryInfo[-2]
                print "Not currently considering: ", link['href']

    # Map out related pages
    doRelated = True
    if options:
        if "MediaSubPage" in options:
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
                previousType = previous['href'].split('/')[-2]
                if previous.string not in urls_visited and previousType.lower() not in ignoredTypes:
                    new_urls.append(tvtropes_main + previous['href'])
            if current:
                currentComponents = current['href'].split('/')
                currentType = currentComponents[-2]
                currentTitle = currentComponents[-1]
                if currentType.lower() not in ignoredTypes:
                    if pageTitle != currentTitle:
                        if thisPage == "media":
                            media[pageKey]['indicies'].append(current.string)
                        else:
                            tropes[pageTitle]['indicies'].append(current.string)
                    if current.string not in urls_visited:
                        new_urls.append(tvtropes_main + current['href'])
            if subsequent:    
                subsequentType = subsequent['href'].split('/')[-2]
                if subsequent.string not in urls_visited and subsequentType.lower() not in ignoredTypes:
                    new_urls.append(tvtropes_main + subsequent['href'])
   
    # Done Parsing, add to DB
    urls_visited.add(url)
    commit_page(dbconnection, url)
    return

# Recurse through all links found
def recur_search(url = None):
    global counter
    if not url:
        url = new_urls.popleft()
    
    if limit != -1 and counter >= limit:
        print "Exceeded limit"
        outJSON.write('Media\n\n')
        json.dump(media, outJSON, indent = 4, cls=SetEncoder)
        outJSON.write('\nTropes\n\n')
        json.dump(tropes, outJSON, indent = 4, cls=SetEncoder)
        dbconnection.commit()
        dbconnection.close()
        sys.exit()

    counter = counter + 1
    finalUrl = test_redirect(url)
    
    urlComponents = finalUrl.split('/')
    pageTitle = urlComponents[-1]
    pageType = urlComponents[-2]

    print counter, ": ", url
    # Don't follow external links
    if "tvtropes.org" not in url:
        print "External Link Ignored"
        return
    # Ignore links with bad types
    if pageType in ignoredTypes:
        print "Link to uninteresting page ignored"
        return
    # Ignore links already searched
    if finalUrl in urls_visited:
        print "Link already discovered"
        return

    print pageTitle + ": " + pageType

    parse_page(finalUrl)

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

