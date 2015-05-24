import urllib
import urllib2
import sys
import re
from collections import deque
from bs4 import BeautifulSoup

import json 
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

counter = 0
limit = 5

newURLs = deque()

known_redirects = {}
tropes_visited = set()
tropes = {}
media_visited = set()
media = {}
allowedMedia = [
    'anime',
    'comicbook',
    'comics',
    'comicstrip',
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

def parse_page(url, options = None):
    print url
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

    if thisPage == "media":
        if pageKey not in media:
            media[pageKey] = {}
            media[pageKey]['tropes'] = set()
            media[pageKey]['url'] = url
            media[pageKey]['title'] = html.find('title').string.replace(" - TV Tropes", "")
            media[pageKey]['indicies'] = []
    elif thisPage == "trope":
        if pageTitle not in tropes:
            tropes[pageTitle] = {}
            tropes[pageTitle]['media'] = set()
            tropes[pageTitle]['url'] = url
            tropes[pageTitle]['title'] = html.find('title').string.replace(" - TV Tropes", "")
            tropes[pageTitle]['indicies'] = []
        if 'url' not in tropes[pageTitle]:
            tropes[pageTitle]['url'] = url
    elif pageTitle not in tropes:
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
        for testlink in links:
            finalURL = None
            # Save some time not bothering to follow external links
            if tvtropes_base not in testlink['href']:
                continue
            if testlink['href'] in known_redirects:
                finalURL = known_redirects[testlink['href']]
            else:
                req = urllib2.Request(testlink['href'])
                res = urllib2.urlopen(req)
                finalURL = res.geturl()
                known_redirects[testlink['href']] = finalURL
            if not finalURL:
                continue

            entryInfo = finalURL.split('/')
            redirectIndex = entryInfo[-1].rfind("?from=") 
            if redirectIndex > 0:
                entryInfo[-1] = entryInfo[-1][0:redirectIndex]
            # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
            if tvtropes_base not in testlink['href']:
                continue
            else:
                link = testlink
                break

        # Verify we have a link and Skip external links
        if not link:
            continue
        entryKey = entryInfo[-2] + '/' + entryInfo[-1]
       
        # Assign results to appropriate dictionary
        if thisPage == "media":
            # Save tropes associated to this media, check their urls
            if 'main' in entryInfo[-2].lower():
                media[pageKey]['tropes'].add(link['href'].split('/')[-1])
                if link.string not in tropes_visited:
                    newURLs.append(link['href'])
            # We've got a bunch of sub-pages for this media
            elif entryInfo[-2] == pageTitle and "Tropes" in entryInfo[-1]:
                parse_page(link['href'], {"MediaSubPage" : pageKey})
        elif thisPage == "supertrope" or thisPage == "trope":
            # Save media associated to trope, check their urls
            if any(media in entryInfo[-2].lower() for media in allowedMedia):
                tropes[pageTitle]['media'].add(entryKey)
                if entryInfo[-1] not in media_visited:
                    newURLs.append(link['href'])
            # If this is a super-trope page, let's go explore the sub-tropes
            elif 'main' in entryInfo[-2].lower():
                # SuperTrope trope sub-pages 
                if 'main' in entryInfo[-2].lower():
                    newURLs.append(link['href'])
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
                if previous.string not in tropes_visited and previous.string not in media_visited and previousType.lower() not in ignoredTypes:
                    newURLs.append(tvtropes_main + previous['href'])
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
                    if current.string not in tropes_visited and current.string not in media_visited:
                        newURLs.append(tvtropes_main + current['href'])
            if subsequent:    
                subsequentType = subsequent['href'].split('/')[-2]
                if subsequent.string not in tropes_visited and subsequent.string not in media_visited and subsequentType.lower() not in ignoredTypes:
                    newURLs.append(tvtropes_main + subsequent['href'])
   
    # Done Parsing
    return

# Recurse through all links found
def recur_search(url):
    global counter
    if limit != -1 and counter >= limit:
        print "Exceeded counter"
        outJSON.write('Media\n\n')
        json.dump(media, outJSON, indent = 4, cls=SetEncoder)
        outJSON.write('\nTropes\n\n')
        json.dump(tropes, outJSON, indent = 4, cls=SetEncoder)
        sys.exit()

    counter = counter + 1
    if url in known_redirects:
        url = known_redirects[url]
    redirectIndex = url.rfind("?from=") 
    if redirectIndex > 0:
        url = url[0:redirectIndex]
    urlComponents = url.split('/')
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
    if pageTitle in tropes_visited or pageTitle in media_visited:
        print "Link already discovered"
        return

    print pageTitle + ": " + pageType

    # This URL is for media
    if any(media in pageType.lower() for media in allowedMedia):
        media_visited.add(pageTitle)
    # This URL is for a trope or superTrope
    else:
        tropes_visited.add(pageTitle)
    parse_page(url)

    # Recurse this search through all untested urls
    if newURLs:
        recur_search(newURLs.popleft())

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
   
    # Trope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury") 

    # Media parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Manga/MahouSenseiNegima") 

    # SuperTrope parsing test
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/Main/ActionGirl") 
    #parse_page("http://tvtropes.org/pmwiki/pmwiki.php/ActionGirl/AnimatedFilms") 
    
    # Recursive search test
    recur_search("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury")

#    print "URLS TO VISIT"
#    for URL in newURLs:
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
#    print "MEDIA VISITED:"
#    print media_visited
#    print
#    print "TROPES VISITED:"
#    print tropes_visited
#    print
#    print "KNOWN REDIRECTS:"
#    for redirect in known_redirects:
#        print redirect, ": ", known_redirects[redirect]
#    print

