import urllib
import re
from bs4 import BeautifulSoup

import json 
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

tropes_visited = set()
tropes = {}
media_visited = set()
media = {}
allowedMedia = [
    'comicbook',
    'fanfic',
    'film',
    'franchise',
    'letsplay',
    'lightnovel',
    'literature',
    'manga',
    'machinima',
    'magazine',
    'music',
    'roleplay',
    'series',
    'TabletopGame',
    'Toys',
    'videogame',
    'visualnovel',
    'webanimation',
    'webcomic',
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

def parse_trope(url):
    # Try and work out info from url
    urlComponents = url.split('/')
    pageTitle = urlComponents[-1]
    pageType = urlComponents[-2]
    
    # Load Page
    html = BeautifulSoup(urllib.urlopen(url))
    newURLs = []

    # Find all blocks of examples of this trope
    bullets = html.find_all("li")

    # Super trope page
    if "main" not in pageType.lower():
        print url, " is not a trope page"
        parse_superTrope(url)
        return

    # There are some examples - Let's go find them    
    tropes[pageTitle] = {}
    tropes[pageTitle]['media'] = set()
    tropes[pageTitle]['url'] = url
    tropes[pageTitle]['title'] = html.find('title').string.replace(" - TV Tropes", "")
    for example_block in bullets:
        # Find all links in example blocks
        examples = example_block.find_all('a')
        for example in examples:
            # Skip external links
            if tvtropes_base not in example['href']:
                continue
            entryInfo = example['href'].split('/')
            entryKey = entryInfo[-2] + '/' + entryInfo[-1]
            # Skip tropes
            if '/Main/' in example['href']:
                continue
            # Save media associated to trope, check their urls
            elif any(media in entryInfo[-2].lower() for media in allowedMedia):
                tropes[pageTitle]['media'].add(entryKey)
                if example.string not in media_visited:
                    newURLs.append(example['href'])
            else:
                print "Not currently considering: ", example['href']

    # Map out related tropes
    tropes[pageTitle]['indicies'] = []
    related = html.find_all(attrs={"class": "wiki-walk"})[0]
    rows = related.find_all(attrs={"class": "walk-row"})
    for row in rows:
        items = row.find_all('span')
        previous = items[0].find('a')
        current = items[1].find('a')
        subsequent = items[2].find('a')
        if previous:
            if previous.string not in tropes_visited:
                newURLs.append(tvtropes_main + previous['href'])
        if current:
            tropes[pageTitle]['indicies'].append(current.string)
            if current.string not in tropes_visited:
                newURLs.append(tvtropes_main + current['href'])
        if subsequent:    
            if subsequent.string not in tropes_visited:
                newURLs.append(tvtropes_main + subsequent['href'])
   
    # Done Parsing
    return newURLs

def parse_superTrope(url):
    
    return

def parse_media(url):
    # Try and work out info from url
    urlComponents = url.split('/')
    pageTitle = urlComponents[-1]
    pageType = urlComponents[-2]
    pageKey = pageType + '/' + pageTitle

    # Load Page
    html = BeautifulSoup(urllib.urlopen(url))
    newURLs = []

    # Find text block
    textblock = html.find(attrs={"id": "wikitext"})

    # If there is no text block, give up
    if not textblock:
        print url, " is not a media page"
        return

    # There are some tropes - Let's go find them    
    media[pageKey] = {}
    media[pageKey]['tropes'] = set()
    media[pageKey]['url'] = url
    media[pageKey]['title'] = html.find('title').string.replace(" - TV Tropes", "")
    #tropeblock = textblock.find('ul')
    #items = tropeblock.find('li')
    #items = [items] + items.find_next_siblings('li')
    items = textblock.find_all('li')
    nSubTags = 0
    for item in items:
        # Skip any 'li' nested within 'li'
        if nSubTags > 0:
            nSubTags -= 1
            continue
        else:
            nSubTags = len(item.find_all('li'))

        # Find the first link in a line
        link = item.find('a')
        # Verify we have a link and Skip external links
        if not link or tvtropes_base not in link['href']:
            continue
        # Save tropes associated to this media, check their urls
        media[pageKey]['tropes'].add(link['href'].split('/')[-1])
        if link.string not in tropes_visited:
            newURLs.append(link['href'])

    # Map out related media 
    media[pageKey]['indicies'] = []
    related = html.find(attrs={"class": "wiki-walk"})
    rows = related.find_all(attrs={"class": "walk-row"})
    for row in rows:
        items = row.find_all('span')
        previous = items[0].find('a')
        current = items[1].find('a')
        subsequent = items[2].find('a')
        if previous:
            if previous.string not in media_visited:
                newURLs.append(tvtropes_main + previous['href'])
        if current:
            media[pageKey]['indicies'].append(current.string)
            if current.string not in tropes_visited:
                newURLs.append(tvtropes_main + current['href'])
        if subsequent:    
            if subsequent.string not in media_visited:
                newURLs.append(tvtropes_main + subsequent['href'])
   
    # Done Parsing
    return newURLs

# Recurse through all links found
def recur_search(url):
    urlComponents = url.split('/')
    pageTitle = urlComponents[-1]
    pageType = urlComponents[-2]

    # Don't follow external links
    if "tvtropes.org" not in url:
        return
    # Ignore links with bad types
    if pageType in ignoredTypes:
        return
    # Ignore links already searched
    if pageTitle in tropes_visited or pageTitle in media_visited:
        return

    print url
    print pageTitle + ": " + pageType

    # This URL is for media
    if any(media in pageType.lower() for media in allowedMedia):
        media_visited.add(pageTitle)
        newURLs = parse_media(url)
    # This URL is for a trope or superTrope
    else:
        tropes_visited.add(pageTitle)
        newURLs = parse_trope(url)

    # Recurse this search through all new urls
    for url in newURLs:
        print url
        #recur_search(url)

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
    URLs = parse_trope("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury") 

    # Media parsing test
    URLs += parse_media("http://tvtropes.org/pmwiki/pmwiki.php/Manga/Monster") 

    # Recursive search test
    #recur_search("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury")

    print "URLS TO VISIT"
    for URL in URLs:
        print URL
    print
    print "MEDIA INDEX:"
    print json.dumps(media, cls=SetEncoder) 
    json.dump(media, outJSON, indent = 4, cls=SetEncoder)
    print
    print "TROPE INDEX:"
    print json.dumps(tropes, cls=SetEncoder)
    json.dump(tropes, outJSON, indent = 4, cls=SetEncoder)
    print
    print "MEDIA VISITED:"
    print media_visited
    print
    print "TROPES VISITED:"
    print tropes_visited
    print
