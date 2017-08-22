import os

with open('download_log.txt') as log:
    for line in log:
        if 'failed' in line and 'FindMediaForTrope' in line:
            print line
            page_index = line.find('trope_page=')
            if page_index:
                url = line.strip()[page_index+len('trope_page='):-1]
                local_path = os.path.join('./raw_html', url.replace('/', '|') + '.hmtl')
                print local_path
                print os.path.exists(local_path)
            print 80 * '-'