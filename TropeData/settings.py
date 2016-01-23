"""
Settings for the scraper and analyser
"""
import logging

LIMIT = -1
RUN_OPTIONS = {
        'run_mode' : 'loop',
        #'run_mode' : 'recursive',

        #'start_url' : None,
        'start_url' : "http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury",
        }
LOG_FILENAME = 'scrape_testNew.log'

LOG_FORMAT = '[%(asctime)s] %(filename)-20s %(levelname)8s - %(message)s'
CONSOLE_FORMAT = '%(filename)-20s %(levelname)8s : %(message)s'
LOG_LEVEL = logging.INFO


# Sometimes TvTropes doesn't refer to media with the right name
# This is dumb and requires hacks.  Probably I should make this a config file.  Maybe later.
KNOWN_ALIASES = {
    'BuffyTheVampireSlayer' : 'Buffy'
    }

ALLOWED_MEDIA = [
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
    'dcanimateduniverse',
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
IGNORED_TYPES = [
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

