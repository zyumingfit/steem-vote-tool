from  urllib.parse import urlparse
import json
import steem
import time
import random

import yaml

def initconfig():
    f = open('steem.yaml')
    content = yaml.safe_load(f)
    return content

class BulkLike():
    def __init__(self):
        self.content = initconfig()
        self.username = self.content['username']
        self.posting_key = self.content['keys']['posting']

        self.s = steem.Steem(nodes=['https://api.steemit.com'], keys=[self.posting_key])

    def get_articles(self, filename):
        with open(filename, 'r') as f:
            urls = f.readlines()
        articles = {}
        for url in urls:
            url  = url.strip('\n')
            if url == '':
                continue
            parms = urlparse(url).path.lstrip('/').strip('/').split('/')
            name = parms[1].lstrip('@')
            title = parms[2]
            articles[title] = {'name':name, 'url':url}
        return articles


    def is_exclude(self, voters):
        exclude_voters = self.content['exclude']
        for voter in voters:
            if voter in exclude_voters:
                return True
        return False

    def bulk_vote(self, articles, weight):
        index = 0
        for permlink in articles.keys():
            index += 1
            name = articles[permlink]['name']
            url = articles[permlink]['url']

            detail = self.s.get_content(name, permlink)

            votes = detail['active_votes']
            voters = [vote['voter'] for vote in votes]

            created_time = detail['created']
            timearray = time.strptime(created_time, "%Y-%m-%dT%H:%M:%S")
            timestamp = int(time.mktime(timearray))
            current_timestamp = int(time.time())

            random_weight = random.randint(weight - 5, weight + 5)

            threshold_time = 7*24*60*60 # 7 days
            if current_timestamp - timestamp >= threshold_time:
                print('%-5s %6s %s %s' % ('[%d]' % index,'[FAIL]', '[Time Expired]', url))
                continue

            if self.is_exclude(voters):
                print('%-5s %6s %s %s' % ('[%d]' % index,'[FAIL]', '[Voter Exclude]', url))
                continue

            identifier = ('@' + name + '/' + permlink)
            try:
                self.s.commit.vote(identifier, float(random_weight), self.username)
            except Exception as err:
                print('%-5s %6s %s %s' % ('[%d]' % index,'[FAIL]', '[Vote Failed]', url))
                continue

            print('%-5s %9s %s' % ('[%d]' % index,'[SUCCESS]', url))


    def vote(self):
        post_level = ['general', 'medium', 'quality']
        for level in post_level:
            if self.content[level]['filename'] != None:
                filename = self.content[level]['filename']
                weight = self.content[level]['weight']

                print('Vote for %s posts...' % level)
                articles = self.get_articles(filename)
                self.bulk_vote(articles, weight)
                print('\n')

    def auto_classification_vote(self):
        filename = self.content['auto']['filename']
        articles = self.get_articles(filename)

        classified = {}
        classified['general'] = {}
        classified['medium'] = {}
        classified['quality'] = {}

        for permlink in articles.keys():
            article = articles[permlink]
            name = article['name']

            detail = self.s.get_content(name, permlink)
            body = detail['body']
            length = len(body)

            if length <= 2000:
                classified['general'][permlink] = article
            elif length <= 4000:
                classified['medium'][permlink] = article
            else:
                classified['quality'][permlink] = article


        for type in classified.keys():
            weight = self.content['auto'][type]
            arts = classified[type]
            print('Vote for %s posts...[%d]' % (type, weight))
            self.bulk_vote(arts, weight)

    def start(self):
        auto = self.content['config']['auto']
        if auto:
            self.auto_classification_vote()
        else:
            self.vote()




if __name__ == "__main__":
    bl = BulkLike()
    bl.start()

