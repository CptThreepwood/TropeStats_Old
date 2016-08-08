""" Identify errors in the DB and log. """
import re
import settings
import site_corrections
import urllib
import difflib

from bs4 import BeautifulSoup

from DataHandler import DataHandler

class ScrapeDiagnostics(object):
    known_media = []
    known_tropes = []
    known_media_names = []
    known_media_types = []
    error_types = {}
    error_count = {}

    datahandler = None

    def __init__(self, verbosity = 1):
        self.data_handler = DataHandler()
        self.known_media = self.data_handler.get_media()
        self.known_media_names = [elem.split('/')[1] for elem in self.known_media]
        self.known_media_types = [elem.split('/')[0] for elem in self.known_media]
        self.known_tropes = self.data_handler.get_tropes()
        self.verbosity = verbosity

    def classify_error(self, error, working_page):
        url =  error[13:]
        url_components = url.split('/')
        url_type = url_components[-2]
        url_name = url_components[-1]
        if (any(url_type.lower() == media for media in settings.ALLOWED_MEDIA)
         or any(url_type.lower() == media for media in settings.IGNORED_TYPES)):
            self.add_error('missing_type_on_run')
            if self.verbosity > 1:
                print
                print "Url missed assigned type: ", url_type.lower()
                print "On page: ", working_page
        elif (any(url_name.lower() == media for media in settings.ALLOWED_MEDIA)
           or any(url_name.lower() == media for media in settings.IGNORED_TYPES)):
            self.add_error('missing_type_on_run')
            if self.verbosity > 1:
                print
                print "Sub-page Url missed assigned type: ", url_type.lower()
                print "On page: ", working_page
        elif re.search("[A-Za-z][tT]o[A-Z][a-z]$", error):
            self.add_error('bad_regexp')
            if self.verbosity > 1:
                print
                print "Mistaken SubPage ",  error
                print "On page: ", working_page
        elif (url_type in self.known_tropes
          and url_name in self.known_media_names):
            self.add_error('specific_media_trope')
            if self.verbosity > 1:
                print
                print "Media specific subpage for trope: ", url
                print "On page: ", working_page
        #elif (url_type in settings.special_subpages
        #  and any(re.match(test+'$', url_name) for test in
        #    settings.special_subpages[url_type][0])):
        #    self.add_error('unrecognized_special_subpage')
        #    if self.verbosity > 1:
        #        print  error
        #        print "Special subpage of ", url_type
        elif url in site_corrections.corrections:
            self.add_error('spelling_errors_fixed')
            if self.verbosity > 1:
                print
                print "Corrected ", url
                print "to        ", site_corrections.corrections[url]
                print "On page: ", working_page
        else:
            error_type, potential_fixes = self.check_url(url)
            #error_type, potential_fixes = None, None
            if error_type:
                self.add_error(error_type)
                if error_type == "misspelled_url" and self.verbosity > 0:
                    print
                    print "On page: ", working_page
                    print "Misspelled Url: ", url
                    print "Most likely fix: ", potential_fixes[0]
                    if self.verbosity > 1:
                        print "Other fixes: "
                        for fix in potential_fixes[1:]:
                            print fix
                elif self.verbosity > 1:
                    print
                    print "Url has no matching page"
                    print  error
                    print "On page: ", working_page
            else:
                self.add_error('unknown_error')
                if self.verbosity > 0:
                    print
                    print "Unknown Error"
                    print  error
                    print "On page: ", working_page


    def add_error(self, error):
        if error in self.error_count:
            self.error_count[error] += 1
        else:
            self.error_count[error] = 1

    def check_url(self, url):
        html = BeautifulSoup(urllib.urlopen(url))
        textblock = html.find(attrs={"id": "wikitext"})
        if not textblock:
            return None, None
        text = textblock.text.strip()
        if text.startswith("We don't have an article"):
            return 'non_existant_page', None
        elif text.startswith("Inexact title"):
            potential_urls = [i['href'] for i in html.find(attrs={"id": "wikitext"}).find_all('a')]
            ranked_urls = difflib.get_close_matches(url, potential_urls, len(potential_urls), 0)
            return 'misspelled_url', ranked_urls
        return None, None

    def database_stats(self):
        type_hist = {}
        for media_type in self.known_media_types:
            if media_type.lower() in type_hist:
                type_hist[media_type.lower()] += 1
            else:
                type_hist[media_type.lower()] = 1
        return type_hist

    def scan_errors(self):
        '''
        Scan for errors in the log file
        '''
        log = open("Scrape.log", "r")

        for line in log:
            msg = line.split('-')[-1].strip()
            if re.search("Processing [0-9].* url$", msg):
                working_page = next(log).split('-')[-1].strip()
            if "ERROR" in line:
                if "Unknown Url" in msg:
                    error_type = self.classify_error(msg, working_page)
        print
        for error_type in self.error_count:
            print error_type, '\t', self.error_count[error_type]
#        print missing_type_on_run, "\t errors due to a type error which is now fixed."
#        print specific_media_trope, "\t pages which are dedicated to a specific media and trope combination"
#        print spelling_errors_fixed, "\t spelling errors which have been corrected."
#        print mistaken_subpage, "\t errors due to bad regexp"
#        print unknown_error, "\t unknown errors"

def main():
    """ Default run """
    verbosity = 1

    diagnostics = ScrapeDiagnostics(verbosity)
    diagnostics.scan_errors()

if __name__ == "__main__":
    main()

