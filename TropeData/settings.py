"""
Settings for the scraper and analyser
"""
import logging

limit = 10
run_options = {
        #'run_mode' : 'loop',
        'run_mode' : 'recursive',

        #'start_url' : None,
        'start_url' : "http://tvtropes.org/pmwiki/pmwiki.php/Main/ChekhovsArmoury",
        }
log_filename = 'scrape_testNew.log'

log_format = '[%(asctime)s] %(filename)-20s %(levelname)8s - %(message)s'
console_format = '%(filename)-20s %(levelname)8s : %(message)s'
log_level = logging.INFO


# Sometimes TvTropes doesn't refer to media with the right name
# This is dumb and requires hacks.
known_aliases = {
    'BuffyTheVampireSlayer' : 'Buffy'
    }

# Similarly certain tropes have uniquely named sub-pages.
# Such sub-pages should remember the sub-type.  It's not like they are media.
# Again an algorithmic way to generate this might be preferable.
# Look for links on trope page which look like /trope/anything?
# 'MainPageName': (ListOfSubPages, Allowed)
special_subpages = {
    'ApocalypseHow'     : (['Class0', 'Class1', 'Class2', 'Class3a', 'Class3b', 'Class4', 'Class5',
                            'Class6', 'ClassX', 'ClassX2', 'ClassX3', 'ClassX4', 'ClassX5', 'ClassZ'
                            ,], True),
    'AnachronismStew'   : (['FilmsWithNoGoodExcuse'], True),
    'BatmanGambit'      : (['BatmanGambitsInvolvingBatman'], True),
    'DwarfFortress'     : (['.*'], False),
    }

allowed_media = [
    'advertisements',
    'advertising',
    'anime',
    'animeandmanga',
    'animatedfilm',
    'animatedfilms',
    'animation',
    'arg',
    'art',
    'asiananimation',
    'audio',
    'audioplay',
    'author',
    'blog',
    'boardgames',
    'bollywood',
    'book',
    'cardgame',
    'cardgames',
    'comicbook',
    'comicbooks',
    'comic',
    'comics',
    'comicsbook',
    'comicstrip',
    'comicstrips',
    'composer',
    'creator',
    'creators',
    'dcanimateduniverse',
    'discworld',
    'disco',
    'disney',               # Apparently big enough to be it's own type of media.  Who knew?
    'disneyandpixar',
    'dreamworks',
    'dungeonsanddragons',
    'easternanimation',
    'fairytales',
    'fanfic',
    'fanfics',
    'fanfiction',
    'fansubs',
    'fanwork',
    'fanworks',
    'film',
    'films',
    'fokelore',
    'folklore',
    'folkloreandfairytales',
    'franchise',
    'franchises',
    'gamebooks',
    'gameshow',
    'graphicnovel',
    'jokes',
    'larp',
    'letsplay',
    'letsplays',
    'lightnovel',
    'lightnovels',
    'literature',
    'liveaction',
    'liveactionfilm',
    'liveactionfilms',
    'liveactiontv',
    'machinima',
    'manga',
    'mangaandanime',
    'manhua',
    'manhwa',
    'manhwaandmanhua',
    'magazine',
    'magazines',
    'marvelcinematicuniverse',
    'media',
    'meta',
    'music',
    'musical',
    'musicvideos',
    'myth',
    'mythandlegend',
    'mythandreligion',
    'mythology',
    'mythologyandfolklore',
    'mythologyandreligion',
    'mythsandreligion',
    'newmedia',
    'newspapercomic',
    'newspapercomics',
    'oraltradition',
    'other',
    'othermedia',
    'pinball',
    'podcast',
    'podcasts',
    'poetry',
    'pop',
    'printmedia',
    'professionalwrestling',
    'prosports',
    'prowrestling',
    'puppetshows',
    'radio',
    'reallife',
    'recordedandstandupcomedy',
    'religion',
    'religionandmythology',
    'roleplay',
    'roleplayinggames',
    'script',
    'series',
    'sports',
    'standup',
    'standupcomedy',
    'tabletop',
    'tabletoprpg',
    'tabletopgame',
    'tabletopgames',
    'tabletopgaming',
    'television',
    'televisionnetworks',
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
    'websitesandsoftwaredesigns',
    'webvideo',
    'webvideos',
    'westernanimation',
    'wiki',
    'wrestling',
    ]

# Can I work out a way to scrape this?
# Maybe using the full list and hardcode some specific allowed types?
# This will do for now
ignored_types = [
    # Ignore languages other than English (for now)
    'de', 'eo', 'es', 'fi', 'fr', 'hu', 'it', 'itadministrivia',
    'itdarthwiki', 'itsugarwiki', 'no', 'pl', 'pt', 'ro', 'se',

    # Ignore YMMV type namespaces
    'aatafovs', 'accidentalnightmarefuel', 'alternativecharacterinterpretation',
    'andthefandomrejoiced', 'analysis', 'awesome', 'awesomebosses', 'awesomebutimpractical',
    'awesomemusic', 'badass', 'betterthanitsounds', 'dethroningmoment', 'fetishfuel', 'fridge',
    'fridgebrilliance', 'fridgehorror', 'funny', 'headscratchers', 'heartwarming',
    'highoctanenightmarefuel', 'horrible', 'narm', 'nightmarefuel', 'shockingelimination',
    'tearjerker', 'thatoneboss', 'thescrappy', 'whatanidiot', 'ymmv',

    # Ignored types that we may add in future
    'allblue', 'shoutout', 'usefulnotes', 'whamepisode',

    # Ignore TVtropes pages not relevant to project
    'administrivia', 'charactersheets', 'characters', 'community', 'cowboybebopathiscomputer',
    'creatorkiller', 'crimeandpunishmentseries', 'darthwiki', 'dieforourship',
    'directlinetotheauthor', 'drinkinggame', 'encounters', 'fanficrecs', 'fannickname',
    'fishytheascendant', 'funwithacronyms', 'gush', 'haiku', 'hellisthatnoise', 'hoyay',
    'imagelinks', 'images', 'imagesource', 'justforfun', 'madmanentertainment', 'masseffect',
    'memes', 'namesthesame', 'pantheon', 'quotes', 'recap', 'referencedby', 'ride', 'sandbox', 'selfdemonstrating',
    'slidingscale', 'soyouwantto', 'sugarwiki', 'thatoneboss', 'trivia', 'tropeco', 'tropers',
    'tropertales', 'troper', 'troubledproduction', 'turnofthemillennium', 'warpthataesop', 'wmg',
    'workpagesinmain', 'monster', 'wallbangers',

    # Ignored media type - Try to keep this as short as possible
    'tvtropes',
    ]

