'''Download the html for a page if we haven't already'''
import requests
import luigi
import os

#pylint: disable=I0011,E1101

TVTROPES_MAIN = "http://tvtropes.org"
TVTROPES_PAGE = "%s/pmwiki/pmwiki.php" % TVTROPES_MAIN

class DownloadPageTask(luigi.ExternalTask):
    '''Download the Page Raw (no parsing)'''
    page_url = luigi.Parameter()

    def output(self):
        file_path = self.page_url.replace(TVTROPES_PAGE, '')
        target_path = './raw_html/{0}.html'.format(file_path)
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        return luigi.LocalTarget(
            target_path
        )

    def run(self):
        req = requests.get(self.page_url)
        with self.output().open('w') as output_file:
            output_file.write(req.text.encode('utf-8'))
