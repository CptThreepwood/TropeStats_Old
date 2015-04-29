import urllib
import re
from bs4 import BeautifulSoup

trope_list = set()
tropes = {}
media_list = set()
media = {}
allowed_media = [
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
    ]

ignoredtypes = [
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
tvtropes_mainpage = "http://www.tvtropes.org"
tvtropes_tropeindex = tvtropes_mainpage + "/pmwiki/pmwiki.php/Main/Tropes"

def parse_trope(url):
    # Try and work out info from url
    urlComponents = url.split('/')
    pageTitle = url[-1]
    pageType = url[-2]
    
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
            elif any(media in example['href'].lower() for media in allowed_media):
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
        items = row.find_all('a')
        if items[0].string not in trope_list:
            newURLs.append(items[0]['href'])
        tropes[pageTitle]['indicies'].append(items[1].string)
        if items[1].string not in trope_list:
            newURLs.append(items[1]['href'])
        if items[2].string not in trope_list:
            newURLs.append(items[2]['href'])
   
    # Done Parsing
    return newURLs

# Recurse through all links found
def recur_search(url):
    urlComponents = url.split('/')
    pageTitle = url[-1]
    pageType = url[-2]

    # Don't follow external links
    if "tvtropes.org" not in url:
        return
    # Ignore links already searched
    if pageTitle in trope_list or pageTitle in media_list:
        return

    print url
    print pageTitle + ": " + pageType
    
    # Let's get tropes working for now
    if "Main" not in pageType:
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
    print "test"

