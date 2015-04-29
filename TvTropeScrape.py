import urllib
import re
import json 
from bs4 import BeautifulSoup

trope_list = set()
tropes = {}
media_list = set()
media = {}
allowedMedia = [
    '/manga/',
    '/comicbook/',
    '/franchise/',
    '/fanfic/',
    '/webanimation/',
    '/westernanimation/',
    '/music/',
    '/film/',
    '/literature/',
    '/series/',
    '/videogame/',
    '/webcomic/',
    '/visualnovel/',
    '/roleplay/',
    '/webvideo/',
    ]

ignoredTypes = [
    # Ignore languages other than English (for now)
    '/no/',
    '/pt/',
    '/fi/',
    '/it/',
    '/de/',
    '/fr/',
    '/eo/',
    '/es/',
    '/ro/',
    '/se/',
    ]

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
    example_blocks = html.find_all("div", attrs={"class": "folder"})

    # If there is no example section, assume this is a super trope page
    if not example_blocks:
        print url, " is not a trope page"
        # This is a super-trope page
        return

    # There are some examples - Let's go find them    
    tropes[pageTitle] = {}
    tropes[pageTitle]['media'] = []
    for example_block in example_blocks:
        # Find all links in example blocks
        examples = example_block.find_all('a')
        for example in examples:
            # Skip external links
            if tvtropes_base not in example['href']:
                continue
            # Skip tropes
            if '/Main/' in example['href']:
                continue
            # Save media associated to trope, check their urls
            elif any(media in example['href'].lower() for media in allowedMedia):
                tropes[pageTitle]['media'].append(example.string)
                if example.string not in media_list:
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
            if previous.string not in trope_list:
                newURLs.append(tvtropes_main + previous['href'])
        if current:
            tropes[pageTitle]['indicies'].append(current.string)
            if current.string not in trope_list:
                newURLs.append(tvtropes_main + current['href'])
        if subsequent:    
            if subsequent.string not in trope_list:
                newURLs.append(tvtropes_main + subsequent['href'])
   
    # Done Parsing
    return newURLs

def parse_superTrope(url):
    # Fill this in
    return

def parse_media(url):
    # Fill this in
    return

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
    if pageTitle in trope_list or pageTitle in media_list:
        return

    print url
    print pageTitle + ": " + pageType

    # This URL is for media
    if any(media in pageType.lower() for media in allowedMedia):
        media_list.add(pageTitle)
        newURLs = parse_media(url)
    # This URL is for a trope or superTrope
    else:
        trope_list.add(pageTitle)
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
    
    # Trope parsing test
    #URLs = parse_trope("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury") 
    #print "URLS TO VISIT"
    #print URLs
    #print

    # Recursive search test
    recur_search("http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury")
    outJSON = open("test.json", "w")

    print
    print "MEDIA INDEX:"
    print json.dumps(media) 
    json.dump(media, outJSON, indent = 4)
    print
    print "TROPE INDEX:"
    print json.dumps(tropes)
    json.dump(tropes, outJSON, indent = 4)
    print
    print "MEDIA VISITED:"
    print media_list
    print
    print "TROPES VISITED:"
    print trope_list
    print
