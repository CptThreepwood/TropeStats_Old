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

# Can I work out a way to scrape this?  Maybe using the full list and hardcode some specific allowed types?
# This will do for now
ignoredTypes = [
    # Ignore languages other than English (for now)
    'de', 'eo', 'es', 'fi', 'fr', 'hu', 'it', 'itadministrivia', 'itdarthwiki', 'itsugarwiki', 'no', 'pl', 'pt', 'ro', 'se', 
    
    # Ignore YMMV type namespaces
    'aatafovs', 'accidentalnightmarefuel', 'alternativecharacterinterpretation', 'andthefandomrejoiced', 'analysis', 'awesome', 
    'awesomebosses', 'awesomebutimpractical', 'awesomemusic', 'badass', 'betterthanitsounds', 'fetishfuel', 'fridge', 'fridgebrilliance', 'fridgehorror', 
    'funny', 'headscratchers', 'heartwarming', 'highoctanenightmarefuel', 'horrible', 'narm', 'nightmarefuel', 'shockingelimination', 'thatoneboss',
    'thescrappy', 'whatanidiot', 'ymmv',


    # Ignored types that we may add in future
    'allblue', 'shoutout', 'usefulnotes', 'whamepisode',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer', 'creatorkiller', 'crimeandpunishmentseries', 
    'darthwiki', 'dieforourship', 'directlinetotheauthor', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname', 'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 
    'hellisthatnoise', 'hoyay', 'imagelinks', 'images', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect', 'memes', 'pantheon', 
    'quotes', 'recap', 'referencedby', 'ride', 'sandbox', 'selfdemonstrating', 'slidingscale', 'soyouwantto', 'sugarwiki', 'thatoneboss',
    'trivia', 'tropeco', 'tropers', 'tropertales', 'troubledproduction', 'turnofthemillennium', 'warpthataesop', 'wmg', 'workpagesinmain',
    'monster', 'wallbangers',
    ]

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
        logging.debug("Testing redirect for %s", url)
        req = urllib2.Request(url)
        try: res = urllib2.urlopen(req)
        except urllib2.HTTPError:
            logging.error("%s could not be found", url)
            return None
        except:
            logging.error("Unknown error opening %s", url)
            logging.error("%s", sys.exc_info()[0])
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
    elif urlType == parentName and re.search("[A-Za-z][Tt]o[A-Za-z]$", urlName):
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
        if page_type == "media":
            DBTools.add_media(dbconnection, page_key, url, html.find('title').string.replace(" - TV Tropes", ""))
        if page_type == "trope":
            DBTools.add_trope(dbconnection, page_key, url, html.find('title').string.replace(" - TV Tropes", ""))
        
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
            #if 'href' not in testlink:
            #    logging.warning("a element does not contain href: %s", testlink)
            #    continue
            # Sometimes links contain unicode characters.  I'm guessing that's never something I want but this is kinda hacky
            # I should instead flag this as an error and resolve it sensibly
            # see: https://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen
            initialUrl = testlink['href'].encode('ascii', 'ignore')
            finalUrl = None
            # Save some time not bothering to follow external links
            if tvtropes_page not in initialUrl:
                continue
            finalUrl = test_redirect(initialUrl) 
            
            # Redirect unresolved
            if not finalUrl:
                continue
            # Not sure if a tvtropes link will ever redirect somewhere else, but let's be safe
            if tvtropes_page not in initialUrl:
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
            # Make a note of this connection
            if entryType == "trope":
                DBTools.add_relation(dbconnection, page_key, entryKey, 1, 1)
            # Harvest urls to follow
            if finalUrl not in urls_visited:
                # Add link to link database
                if entryType == "trope":
                    if initialUrl not in new_urls:
                        new_urls.append(initialUrl)
                        DBTools.add_url(dbconnection, initialUrl, finalUrl)
                # We've got a bunch of sub-pages for this media
                # Immediately go get subpage information 
                elif entryType == "mediaSubPage":
                    if options:
                        logging.warning("There is a sub-subPage here or subPages refer to each other")
                        logging.warning("Skipping %s", finalUrl)
                        continue
                    parse_page(finalUrl, {"MediaSubPage" : pageKey})
                # Franchise pages sometimes just link to each media subpage
                # In this case we should investigate each of those links, but not associate them to the Franchise page
                elif pageKey.split('/')[0] == "Franchise" and entryType == "media":
                    # Add link to link database
                    if initialUrl not in new_urls:
                        new_urls.append(initialUrl)
                        DBTools.add_url(dbconnection, initialUrl, finalUrl)
                elif entryType == "media":
                    if initialUrl not in new_urls and finalUrl != tvtropes_page + pageKey:
                        new_urls.append(initialUrl)
                        DBTools.add_url(dbconnection, initialUrl, finalUrl)
                else :
                    logging.warning("Not currently considering: %s", finalUrl)
        # Save media associated to trope, check their urls
        elif pageType == "trope":
            # Make a note of this connection
            if entryType == "media":
                DBTools.add_relation(dbconnection, entryKey, page_key, 1, -1)
            # Harvest urls to follow
            if finalUrl not in urls_visited:
                # Add link to link database
                if entryType == "media":
                    if initialUrl not in new_urls:
                        DBTools.add_url(dbconnection, initialUrl, finalUrl)
                        new_urls.append(initialUrl)
                # If this is a super-trope page, add tropes to list
                elif entryType == "trope":
                    if initialUrl not in new_urls and finalUrl != tvtropes_trope + pageKey:
                        new_urls.append(initialUrl)
                        DBTools.add_url(dbconnection, initialUrl, finalUrl)
                # This tropes media have been split into types, go explore them all now
                elif entryType == "tropeSubPage":
                    if options:
                        logging.warning("There is a sub-subPage here or subPages refer to each other")
                        logging.warning("Skipping %s", finalUrl)
                        continue
                    parse_page(finalUrl, {"TropeSubPage" : pageKey})
                else:
                    logging.warning("Not currently considering: %s", finalUrl)

    # Map out related pages
    doRelated = True
    if options:
        if any(x in options for x in ["MediaSubPage","TropeSubPage"]):
            doRelated = False

    table = html.find_all(attrs={"class": "wiki-walk"})
    if doRelated and table:    
        related = table[0]
        rows = related.find_all(attrs={"class": "walk-row"})
        for row in rows:
            items = row.find_all('span')
            previous = items[0].find('a')
            current = items[1].find('a')
            subsequent = items[2].find('a')
            if previous:
                previousUrl = tvtropes_main + previous['href']
                previousRedirect = test_redirect(previousUrl.encode('ascii', 'ignore'))
                if previousRedirect:
                    previousType, previousKey = identify_url(previousRedirect)
                    if previousRedirect not in urls_visited and previousUrl not in new_urls and previousType:
                        new_urls.append(previousUrl)
                        DBTools.add_url(dbconnection, previousUrl, previousRedirect)
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
    elif doRelated:
        logging.warning("No Relation Table found at %s", finalUrl)
        
    # Done Parsing, add to DB
    logging.debug("%s finished", url)
    urls_visited.add(url)
    DBTools.commit_page(dbconnection, url)
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
        logging.debug("Link already discovered")
        if new_urls:
            recur_search(new_urls.popleft())
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

def loop_search():
    currentCount = 0
    
    while(new_urls):
        url = new_urls.popleft()
        if limit > 0 and currentCount >= limit:
            logging.critical("Exceeded limit")
            break

        # Don't follow external links
        if "tvtropes.org" not in url:
            logging.info("External Link Ignored: %s", url)
            continue

        finalUrl = test_redirect(url)
        if not finalUrl:
            logging.info("%s could not be resolved", url)
            continue
        currentCount = currentCount + 1

        pageType, pageTitle = identify_url(finalUrl)
        # Code snippet to make ordinal numbers
        # Taken from http://codegolf.stackexchange.com/questions/4707/outputting-ordinal-numbers-1st-2nd-3rd
        ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

        # Ignore links with bad types
        if pageType in ignoredTypes:
            logging.info("Link to unintersting page ignored")
            continue
        # Ignore links already searched
        if finalUrl in urls_visited:
            logging.debug("Link already discovered")
            currentCount = currentCount -1
            continue 
        logging.info("Processing %s url", ordinal(currentCount))
        logging.info("%s", finalUrl)

        logging.info("%s: %s", pageTitle, pageType)
        parse_page(finalUrl)
    
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
        loop_search()
    else:
        logging.debug("Starting New Run fresh from %s", testUrl)
        DBTools.add_url(dbconnection, testUrl)
        recur_search(testUrl)

