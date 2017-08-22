''' High level run analysis script'''
import json
import luigi
from bs4 import BeautifulSoup

from parse_page import ParsePage
from download_page import DownloadPageTask

#pylint: disable=I0011,E1101

TVTROPES_MAIN = "http://tvtropes.org"

class GetTropeIndex(luigi.Task):
    '''Get the list of tropes from the index'''
    trope_index = luigi.Parameter()

    def requires(self):
        return DownloadPageTask(
            page_url=self.trope_index
        )

    def output(self):
        return luigi.LocalTarget(
            './luigi_data/trope_index.json'
        )

    def run(self):
        with self.input().open('r') as input_file:
            index_soup = BeautifulSoup(input_file.read())
            trope_lists = index_soup.find_all("div", class_="index-list")
            tropes = [trope['href']
                      for trope_list in trope_lists
                      for trope in trope_list.find_all('a', class_='twikilink')]
        with self.output().open('w') as output_file:
            json.dump(tropes, output_file)

class FindAllTropes(luigi.Task):
    '''Launch the whole damn thing'''
    def requires(self):
        return GetTropeIndex(
            trope_index='http://tvtropes.org/pmwiki/index_report.php'
        )

    def output(self):
        return luigi.LocalTarget(
            './luigi_data/all_page_index.json'
        )

    def run(self):
        with self.input().open('r') as input_file:
            trope_list = json.load(input_file)
            downloaded_pages = yield [
                ParsePage(
                    page_url=TVTROPES_MAIN + trope
                ) for trope in trope_list
            ]

        with self.output().open('w') as output_file:
            all_pages = []
            for page in downloaded_pages:
                with page.open('r') as page_file:
                    json_text = json.loads(page_file.read())
                    all_pages += [
                        link[1] for link in json_text['page_links']
                    ]
                    all_pages += [
                        link[1] for link in json_text['sub_pages']
                    ]
            all_pages = list(set(all_pages))
            json.dump(all_pages, output_file)
