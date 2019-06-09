import re
import time
import sys
import argparse
import asyncio
import aiohttp
import ProxyPool
import html2text
from bs4 import BeautifulSoup
from urllib.parse import unquote

ordinal = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth'}

class PixnetCrawler:
    """
    This is a customized crawler for the Pixnet blog.
    It crawls the titles and contents of each search result according to
    the searching keywords.

    There are generally two types of websites from the search results, one
    is Pixnet's blog, the other is the Hares.
    We simply use integers to represent the two websites:
    { 0: 'Pixnet', 1: 'Hares }
    """

    def __init__(self):
        self._start = 0
        self._end = 0
        self._keyword = ''
        self._timeout = 0
        self._recon = 0
        self._filename = ''
        self._urls = []
        self._re_urls = []
        self._pool = ProxyPool.ProxyPool()
        self._searchURL = ''
        self._punc = ',.!?:;~\'\"，。！？：；、～…⋯()<>「」［］【】＜＞〈〉《》（）﹙﹚『』«»“”’{}\\[\\]'   # the '[]' needs to be the last one
        self._stop_words = 'ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄧㄨㄩㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ \
                            ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ \
                            ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ \
                            １２３４５６７８９０1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?©@#$%^&*．…⋯→‧•◎※■＋・ˇˋˊ˙ \
                            ()_+=-\\[]/,.;:`~|{}<>\'\"\n\t\r\xa0，。、！？「」［］【】＜＞〈〉《》（）：；«»＊˙●／＿—『』×＠＃＄％︿＆－＝〜～≡｜│║★☆Ⓡ➠†§– \
                            ♥❤“”’￣▽😊😆😋😏😅😀😍😎📍👍🚫🐍💟🎉⊙◢◤˚ﾟ･｡｀↑↓﹙﹚▲▼◆◈▣✥▒👉►⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬〝〞▌☀ღ▶➦ⓞ☎▋♡▂▃▄▅▆▊▩⇓✽�🕘㊣╳'
        self._sw_no_punc = re.sub('([{}])'.format(self._punc), '', self._stop_words)
        self._sw_dict = {w : True for w in self._stop_words}
        self._sw_no_punc_dict = {w : True for w in self._sw_no_punc}
        self._websites = {'Unknown': -1, 'Pixnet': 0, 'Hares': 1}
        self._title_tags = ['title', 'entry-title']                       # {0: 'Pixnet', 1: 'Hares}
        self._content_tags = ['article-content-inner', 'entry-content']   # {0: 'Pixnet', 1: 'Hares}
        self._result = ''


    @property
    def start(self, value):
        return self._start


    @property
    def end(self, value):
        return self._end


    @property
    def keyword(self, value):
        return self._keyword

    
    @property
    def timeout(self, value):
        return self._timeout


    @property
    def recon(self, value):
        return self._recon


    @property
    def filename(self, value):
        return self._filename


    @start.setter
    def start(self, value):
        self._start = value


    @end.setter
    def end(self, value):
        self._end = value


    @keyword.setter
    def keyword(self, value):
        self._keyword = value

    
    @timeout.setter
    def timeout(self, value):
        self._timeout = value


    @recon.setter
    def recon(self, value):
        self._recon = value


    @filename.setter
    def filename(self, value):
        self._filename = value


    def set_searchURL(self):
        self._searchURL = 'https://www.pixnet.net/searcharticle?q={:s}&page='.format(self._keyword.replace(' ', '+'))


    async def _fetch(self, session, url, proxy=None, raw=False, which_site=False):
        """
        Issue a GET request for the given URL.

        :returns: a tuple
        """
        print(url)
        result = None
        site = None
        if 'hare' in url:   # {'Unknown': -1, 'Pixnet': 0, 'Hares': 1}
            site = self._websites['Hares']
        elif 'pixnet' in url:
            site = self._websites['Pixnet']
        else:
            site = self._websites['Unknown']

        count = 1
        while count <= 2:
            soup = ''
            status = 0
            try:
                async with session.get(url, proxy=proxy) as response:
                    source_code = await response.text('utf-8')
                    status = response.status
                    soup = source_code if raw else BeautifulSoup(source_code, 'lxml')
            except Exception as e:
                print('Connection error: ' + str(e))
                soup = None
            finally:
                result = (url, soup, status, site) if which_site else (url, soup, status)
                if status != 0:
                    return result
            if 'searcharticle' not in url:
                count += 1
        result = (url, soup, status, site) if which_site else (url, soup, status)
        return result


    async def _bound_fetch(self, semaphore, session, url, proxy=None, raw=False, which_site=False):
        """
        To set up a boundary for the open files limitation at the same time.
        
        :returns: a tuple
        """
        async with semaphore:
            return await self._fetch(session, url, proxy, raw, which_site)


    async def _connect(self, urls, proxy=None, raw=False, which_site=False):
        """
        Create a list of connection tasks.

        :param session: a aiohttp's ClientSession object
        :param url: the request url
        :param proxy: the proxy's url, none if using local IP address
        :param raw: True to get the source code, False to get the soup object of Beautifulsoup
        :param which_site: True to add a column in result to specify the types of websites
        :returns: a list of tuples
        e.g. [(url, soup, status), (url, soup, status)]
        """
        tasks = []
        semaphore = asyncio.Semaphore(1000)   # use Semaphore to avoid limitation number of Windows open files
        async with aiohttp.ClientSession(read_timeout=self._timeout) as session:   # read_timeout is the acceptable time
            for url in urls:                                                       # for waiting for the server's response
                task = asyncio.ensure_future(self._bound_fetch(semaphore, session, url, proxy, raw, which_site))
                tasks.append(task)
            await asyncio.gather(*tasks)
        return [task.result() for task in tasks]


    def _error(self, url, soup, status, site, log_url=False):
        """
        Check if error exists during connection.
        If there's an error, the type of error will be specified,
        and the error URL will be added into a reconnection queue.

        :param log_url: True to log the URLs to '_re_urls' with connection errors
        :returns: True if no error exists, else False
        """
        unexpect = False
        if status == 0:
            print('Unable to connect to website:' + url)
        elif status >= 400 or soup is None:
            print(str(status) + ' | Can\'t open website:' + url)
        else:
            if site < 0:
                print("Unexpected website:" + url)
                unexpect = True
            else:
                return False    # No error
        if log_url and not unexpect:
            self._re_urls.append(url)
        return True    # error


    async def _transform_hares(self, urls):
        """
        Get the real article URL of Hares website

        :param urls: the Hares URLs list
        :returns: a list of Hares URLs
        """
        transformed_links = []
        result_list = await self._connect(urls, raw=True)
        for result in result_list:
            url, source_code = result[:2]
            link = re.findall(r'(http://hares.tw/archives/.*?)\">繼續閱讀全文', source_code)
            if link:
                transformed_links.append(link[0])
            else:    # list is empty
                transformed_links.append(url)
        return transformed_links


    async def get_article_links(self):
        """
        Get all articles' links from the search results.

        :returns: a list of URLs
        """
        urls = []
        for page in range(self._start, self._end+1):
            urls.append(self._searchURL + str(page))
        result_list = await self._connect(urls)

        self._urls = []
        hares_links = []
        for result in result_list:
            soup = result[1]
            search_links = soup.find_all(class_='search-title')
            article_links = re.findall(r'url=(.*?)\"', str(search_links))
            for l in article_links:
                l = unquote(l)
                if 'hare48.pixnet.net' in l:
                    hares_links.append(l)
                else:
                    self._urls.append(l)
        self._urls.extend(await self._transform_hares(hares_links))


    async def get_contents(self):
        """
        Get the contents of all articles from the search results.
        It will repeat for _recon + 1 times. Thus, if _recon is 0, it will
        terminate after the initial connection is finished.
        The result will be stored in the '_result' variable.
        """
        if self._recon < 0:
            raise ValueError('Reconnection time needs to be positive!')
        urls = self._urls
        proxy_list = await self._pool.get_proxies(self._recon + 1)
        
        for count in range(self._recon + 1):
            proxy = proxy_list[count]
            if count > 0:     # perform reconnection
                if not self._re_urls:
                    print('No need to reconnect.')
                    break
                else:
                    if count == 1:
                        print('Reconnecting...')
                    print('\n----------------------------------------------------------')
                    print(ordinal[count].capitalize() + ' reconnection...\n')
                    urls = self._re_urls

            result_list = await self._connect(urls, proxy=proxy, which_site=True)

            self._re_urls.clear()      # empty the reconnect urls list 
            for result in result_list:
                url, soup, status, site = result
                if not self._error(url, soup, status, site, True):
                    self._result += self._get_plain_text(url, soup, site)
            fail_num = len(self._re_urls)
            if count == self._recon:
                print('Failed to crawl ' + str(fail_num) + (' website.' if fail_num==1 else ' websites.'))

        self._result = re.sub(r'\s+', '', self._result)   # trim whitespaces
        self._result = self._rm_duplicate(self._result)


    def _get_plain_text(self, url, soup, site):
        """
        Get the text in titles and articles.
        
        :returns: a string
        """
        print('Get plaint text: ' + url)
        title = str(soup.find(class_=self._title_tags[site]))
        content = str(soup.find(class_=self._content_tags[site]))
        # h = html2text.HTML2Text()    # uncomment this segment of code
        # h.ignore_links = True        # if you want to get plain text
        # h.ignore_images = True
        # title = h.handle(title)
        # content = h.handle(content)
        if title == None or content == None:
            print("Different website structure:")
            print(url)
            return ''
        return self._clean(title + content, no_punc=True)    # with symbols
        # return title + content               # without symbols


    def _clean(self, texts, no_punc=False):
        """
        Clean the symbols in a string.
        If no_punc is True, no symbols will remain in the text.
        Otherwise, only the symbols specified in '_punc' will be reserved.

        :param texts: a string with symbols
        :param no_punc: a boolean value to determine the removal of punctuation marks
        :returns: a string
        """
        result = ''
        sw = self._sw_no_punc_dict if no_punc else self._sw_dict
        for t in texts:
            if t not in sw:
                result += t
        return result


    def _rm_duplicate(self, s):
        """
        Replace the symbols specified in '_punc' with '，'.
        Two symbols or more that are adjacent will be consider
        as one symbol.

        :param s: a string with punctuation marks
        :returns: a string
        """
        punc_re = '([{}]+)'.format(self._punc)
        result = re.sub(punc_re, r'，', s)
        return result


    def output(self):
        with open(self._filename, 'w', encoding='UTF-8') as f:
            f.write(self._result)
        print('\n----------------------------------------------------------')
        print('Successfully writed output file: \"{}\"'.format(self._filename))


    async def crawl(self):
        self.set_searchURL()
        print('Start crawling for ' + self._keyword + '...')
        start = time.time()
        await self.get_article_links()
        link = time.time()
        await self.get_contents()
        content = time.time()
        self.output()
        output = time.time()
        print('\n----------------------------------------------------------')
        print('Time measurement:')
        print('Get all articles\' links: ' + str(round(link - start, 2)) + ' sec')
        print('Get all articles\' contents: ' + str(round(content - link, 2)) + ' sec')
        print('Writing output file: ' + str(round(output - content, 2)) + ' sec')
        print('Total: ' + str(round(output - start, 2)) + ' sec')


    def process_command(self):
        parser = argparse.ArgumentParser(description='This is an asyncronous crawler for Pixnet\'s blog posts.')
        g1 = parser.add_argument_group('search options')
        g1.add_argument('-k', '--keyword', type=str, required=True, help='Keywords to search on Pixnet\'s blog')
        g1.add_argument('-s', '--start', type=int, default=1, help='The starting page index for crawling, default is 1.')
        g1.add_argument('-e', '--end', type=int, default=10, help='The ending page index for crawling, default is 10.')
        g2 = parser.add_argument_group('time related options')
        g2.add_argument('-t', '--timeout', type=int, default=25, help='The acceptable time for the server\'s response.')
        g2.add_argument('-r', '--recon', type=int, default=3, help='The reconnection times if reconnection is needed.')
        g3 = parser.add_argument_group('output options')
        g3.add_argument('-o', '--output', type=str, help='The name of the output file.')
        return parser.parse_args()

    def show_options(self):
        print('\n----------------------------------------------------------')
        print('{:20}{}{}'.format('OPTIONS', '| ', 'VALUES'))
        print('----------------------------------------------------------')
        print('{:20}{}{}'.format('keyword', '| ', self._keyword))
        print('{:20}{}{}'.format('start page', '| ', self._start))
        print('{:20}{}{}'.format('end page', '| ', self._end))
        print('{:20}{}{}'.format('timeout', '| ', self._timeout))
        print('{:20}{}{}'.format('reconnection times', '| ', self._recon))
        print('{:20}{}{}'.format('output filename', '| ', self._filename))
        print('----------------------------------------------------------\n')


async def main():
    pc = PixnetCrawler()
    args = pc.process_command()
    if args.keyword:
        pc.keyword = args.keyword
    if args.start:
        pc.start = args.start
    if args.end:
        pc.end = args.end
    if args.timeout:
        pc.timeout = args.timeout
    if args.recon:
        pc.recon = args.recon
    if args.output:
        pc.filename = args.output
    else:
        pc.filename = args.keyword + '.txt'
    pc.show_options()
    print('Press ENTER to continue. Otherwise, press \'!\' to exit.')
    while True:
        k = input()
        if k == '':
            await pc.crawl()
            return
        elif k == '!':
            sys.exit()
        else:
            print('Only ENTER and \'!\' are acceptable.')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(main())
    loop.run_until_complete(future)