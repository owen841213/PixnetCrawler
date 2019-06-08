import re
import sys
import asyncio
import aiohttp
import ProxyPool
import html2text
from bs4 import BeautifulSoup
from urllib.parse import unquote
from aiohttp.client_exceptions import (ServerDisconnectedError, ClientConnectorError,
                                       ClientOSError, ClientResponseError)

ordinal = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh'}

class PixnetCrawler:
    """
    This is a customized crawler for the Pixnet blog.
    It crawls the titles and contents of each search results according to
    the searching keywords.

    There are generally two types of websites from the search results, one
    is Pixnet's blog, the other is the Hares.
    We simply use integers to represent the two websites:
    {
        0: 'Pixnet',
        1: 'Hares
    }
    """

    def __init__(self, maxPage=1, keyword='台南 美食'):
        self._maxPage = maxPage
        self._keyword = keyword
        self._urls = []
        self._re_urls = []
        self._pool = ProxyPool.ProxyPool()
        self._url = 'https://www.pixnet.net/searcharticle?q={:s}&page='.format(self._keyword.replace(' ', '+'))
        self._punc = ',.!?:;~\'\"，。！？：；、～…⋯()<>「」［］【】＜＞〈〉《》（）﹙﹚『』«»“”’{}\\[\\]'   # the [] needs to be the last one
        self._stop_words = 'ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄧㄨㄩㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ \
                            ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ \
                            １２３４５６７８９０1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?©@#$%^&*．…⋯→‧•◎※■＋・ˇˋˊ˙ \
                            ()_+=-\\[]/,.;:`~|{}<>\'\"\n\t\r\xa0，。、！？「」［］【】＜＞〈〉《》（）：；«»＊˙●／＿—『』×＠＃＄％︿＆－＝〜～≡｜│║★☆Ⓡ➠†§– \
                            ♥❤“”’￣▽😊😆😋😏😅😀😍😎📍👍🚫🐍💟🎉⊙◢◤˚ﾟ･｡｀↑↓﹙﹚▲▼◆◈▣✥▒👉►①③〝〞▌☀ღ▶➦ⓞ☎ⒶⓁⒾⓉⓉⓁⒺⓂⓄⒺ▋♡▂▃▄▅▆▊▩⇓✽�🕘㊣'
        self._sw_no_punc = re.sub('([{}])'.format(self._punc), '', self._stop_words)
        self._sw_dict = {w : True for w in self._stop_words}
        self._sw_no_punc_dict = {w : True for w in self._sw_no_punc}
        self._title_tags = ['title', 'entry-title']                       # {0: 'Pixnet', 1: 'Hares}
        self._content_tags = ['article-content-inner', 'entry-content']   # {0: 'Pixnet', 1: 'Hares}
        self._result = ''


    async def _connect(self, url, proxy=None, raw=False, which_site=False):
        print(url)
        soup = ''
        status = 0
        async with aiohttp.ClientSession(read_timeout=50) as session:
            try:
                async with session.get(url, proxy=proxy) as response:
                    source_code = await response.text('utf-8')
                    status = response.status
                    soup = source_code if raw else BeautifulSoup(source_code, 'lxml')
            except Exception as e:
                print(e)
                print('ERROR!!!!!!!!!!!!!!')
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


    def _error(self, url, soup, status, site, log_url=False):
        unexpect = False
        if status == 0:
            print('soup:')
            print(soup)
        elif status >= 400 or soup is None:
            print(str(status) + ' Can\'t open website:')
            print(url)
        else:
            if site < 0:
                print("Unexpected website:")
                print(url)
                unexpect = True
            else:
                return False    # No error
        if log_url and not unexpect:
            self._re_urls.append(url)
        return True    # error


    async def _transform_hares(self, urls):
        tasks = []
        for url in urls:
            task = asyncio.ensure_future(self._connect(url, raw=True))
            tasks.append(task)
        await asyncio.gather(*tasks)

        transformed_links = []
        for task in tasks:
            url, source_code, status = task.result()
            link = re.findall(r'(http://hares.tw/archives/.*?)\">繼續閱讀全文', source_code)
            if link:
                transformed_links.append(link[0])
            else:    # list is empty
                transformed_links.append(url)
        return transformed_links


    async def get_article_links(self):
        tasks = []
        for page in range(1, self._maxPage+1):
            url = self._url + str(page)
            task = asyncio.ensure_future(self._connect(url))
            tasks.append(task)
        await asyncio.gather(*tasks)

        self._urls = []
        hares_links = []
        for task in tasks:
            soup = task.result()[1]
            search_links = soup.find_all(class_='search-title')
            article_links = re.findall(r'url=(.*?)\"', str(search_links))
            for l in article_links:
                l = unquote(l)
                if 'hare48.pixnet.net' in l:
                    hares_links.append(l)
                else:
                    self._urls.append(l)
        self._urls.extend(await self._transform_hares(hares_links))


    def _clean(self, texts, no_punc=False):
        result = ''
        sw = self._sw_no_punc_dict if no_punc else self._sw_dict
        for t in texts:
            if t not in sw:
                result += t
        return result


    def rm_duplicate(self, s):
        punc_re = '([{}]+)'.format(self._punc)
        result = re.sub(punc_re, r'，', s)
        return result


    def _get_plain_text(self, url, soup, site):
        print('get plaint text: ' + url)
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


    async def get_contents(self, recon=0):
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
                    print(ordinal[count].capitalize() + ' reconnection...')
                    urls = self._re_urls

            tasks = []
            for url in urls:
                task = asyncio.ensure_future(self._connect(url, proxy=proxy, which_site=True))
                tasks.append(task)
            await asyncio.gather(*tasks)

            self._re_urls.clear()      # empty the reconnect urls list 
            for task in tasks:
                url, soup, status, site = task.result()
                if not self._error(url, soup, status, site, True):
                    self._result += self._get_plain_text(url, soup, site)
            fail_num = len(self._re_urls)
            if count == recon:
                print('Failed to crawl ' + str(fail_num) + (' website.' if fail_num==1 else ' websites.'))

        self._result = re.sub(r'\s+', '', self._result)   # trim whitespaces
        self._result = self.rm_duplicate(self._result)


    def output(self):
        with open(self._keyword + '.txt', 'w', encoding='UTF-8') as f:
            f.write(self._result)
        print('\n----------------------------------------------------')
        print('Done!')


    async def crawl(self):
        print('Start crawling for ' + self._keyword + '...')
        await self.get_article_links()
        await self.get_contents(3)   # set max reconnection times to 3
        self.output()


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