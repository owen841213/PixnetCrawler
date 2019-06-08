import re
import time
import sys
import asyncio
import aiohttp
import ProxyPool
import html2text
from bs4 import BeautifulSoup
from urllib.parse import unquote
from aiohttp.client_exceptions import (ServerDisconnectedError, ClientConnectorError,
                                       ClientOSError, ClientResponseError)

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

    def __init__(self, maxPage=1, keyword='台南 美食'):
        self._maxPage = maxPage
        self._keyword = keyword
        self._urls = []
        self._re_urls = []
        self._pool = ProxyPool.ProxyPool()
        self._url = 'https://www.pixnet.net/searcharticle?q={:s}&page='.format(self._keyword.replace(' ', '+'))
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
        self._title_tags = ['title', 'entry-title']                       # {0: 'Pixnet', 1: 'Hares}
        self._content_tags = ['article-content-inner', 'entry-content']   # {0: 'Pixnet', 1: 'Hares}
        self._result = ''


    async def _fetch(self, session, url, proxy=None, raw=False, which_site=False):
        """
        Issue a GET request for the given URL.

        :returns: a tuple
        """
        print(url)
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
            if which_site:
                if 'hare' in url:  # {0: 'Pixnet', 1: 'Hares}
                    site = 1
                elif 'pixnet' in url:
                    site = 0
                else:
                    site = -1
                return (url, soup, status, site)
            else:
                return (url, soup, status)


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
        async with aiohttp.ClientSession(read_timeout=25) as session:   # read_timeout is the acceptable time for waiting for the server's response
            for url in urls:
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
        for page in range(1, self._maxPage+1):
            urls.append(self._url + str(page))
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


    async def get_contents(self, recon=0):
        """
        Get the contents of all articles from the search results.
        It will repeat for recon + 1 times so if recon is 0, it will
        terminate after the initial connection is finished.
        The result will be stored in the '_result' variable.

        :param recon: Reconnection times, needs to be a natural number.
        """
        if recon < 0:
            raise ValueError('Reconnection time needs to be positive!')
        urls = self._urls
        proxy_list = await self._pool.get_proxies(recon + 1)
        
        for count in range(recon + 1):
            proxy = proxy_list[count]
            if count > 0:     # perform reconnection
                if not self._re_urls:
                    print('No need to reconnect.')
                    break
                else:
                    if count == 1:
                        print('Reconnecting...')
                    print('\n\n----------------------------------------------------------')
                    print(ordinal[count].capitalize() + ' reconnection...\n')
                    urls = self._re_urls

            result_list = await self._connect(urls, proxy=proxy, which_site=True)

            self._re_urls.clear()      # empty the reconnect urls list 
            for result in result_list:
                url, soup, status, site = result
                if not self._error(url, soup, status, site, True):
                    self._result += self._get_plain_text(url, soup, site)
            fail_num = len(self._re_urls)
            if count == recon:
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
        with open(self._keyword + '.txt', 'w', encoding='UTF-8') as f:
            f.write(self._result)
        print('\n----------------------------------------------------------')
        print('Successfully writed output file: \"{}\"'.format(self._keyword + '.txt'))


    async def crawl(self):
        print('Start crawling for ' + self._keyword + '...')
        start = time.time()
        await self.get_article_links()
        link = time.time()
        await self.get_contents(3)   # set max reconnection times to 3
        content = time.time()
        self.output()
        output = time.time()
        print('\n----------------------------------------------------------')
        print('Time measurement:')
        print('Get all articles\' links: ' + str(round(link - start, 2)) + ' sec')
        print('Get all articles\' contents: ' + str(round(content - link, 2)) + ' sec')
        print('Writing output file: ' + str(round(output - content, 2)) + ' sec')
        print('Total: ' + str(round(output - start, 2)) + ' sec')


if __name__ == '__main__':
    try:
        int(sys.argv[1])
    except ValueError as e:
        print(type(e).__name__ + ': argv[1] must be in type \'int\'')
        sys.exit()
    loop = asyncio.get_event_loop()
    pc = PixnetCrawler(int(sys.argv[1]), ' '.join(sys.argv[2:]))
    future = asyncio.ensure_future(pc.crawl())
    loop.run_until_complete(future)