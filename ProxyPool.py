import re
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup

class ProxyPool:

    def __init__(self):
        self._sources = ['https://free-proxy-list.net/', 'https://www.us-proxy.org/', 'https://www.socks-proxy.net/', 'https://www.sslproxies.org/',
                         'https://free-proxy-list.net/uk-proxy.html', 'https://free-proxy-list.net/anonymous-proxy.html']
        self._limits = [300, 200, 80, 100, 100, 100]
        self._ip_test = 'https://httpbin.org/ip'
        self._pool = {}

    @property
    def num(self):
        return len(self._pool)


    @property
    def pool(self):
        return self._pool


    def _fetch(self, site, start=1, end=10):
        print('Fetching proxies...')
        number = end - start
        response = requests.get(self._sources[site])
        soup = BeautifulSoup(response.text, 'lxml')
        first_proxy = soup.find(id='proxylisttable').find('tbody').find('tr')
        for i in range(start-1):
            first_proxy = first_proxy.find_next_sibling('tr')            # get the proxy of index 'start'
        proxylist = first_proxy.find_next_siblings('tr', limit=number)   # find the next n-1 proxies
        proxylist.insert(0, first_proxy)                # insert the first proxy to the start of the list
        for item in proxylist:
            proxy = item.find('td').find(text=True) + ':' + item.find('td').find_next_sibling('td').find(text=True)
            self._pool[proxy] = False


    async def _connect(self, url, proxy, raw=False):
        soup = ''
        status = 0
        async with aiohttp.ClientSession(read_timeout=5) as session:
            try:
                async with session.get(url, proxy='http://'+proxy) as response:
                    source_code = await response.text('utf-8')
                    status = response.status
                    soup = source_code if raw else BeautifulSoup(source_code, 'lxml')
            except:
                soup = None
            finally:
                return (soup, status, proxy)


    async def _update(self):
        if len(self._pool) == 0:
            print('Need to fetch proxies first.')
            return
        print('Updating proxy list...')
        tasks = []
        for proxy in self._pool:
            task = asyncio.ensure_future(self._connect(self._ip_test, proxy))
            tasks.append(task)
        await asyncio.gather(*tasks)

        for task in tasks:
            (soup, status, proxy) = task.result()
            if soup is not None and status < 400:
                self._pool[proxy] = True
            else:
                del self._pool[proxy]


    async def _available(self, number):
        if number <= 0:
            return
        print('Need ' + str(number) + (' proxy' if number==1 else ' proxies'))
        await self._update()
        if self.num >= number:
            print('Found ' + str(self.num) + (' proxy' if self.num==1 else ' proxies'))
            return
        for i in range(len(self._sources)):
            self._fetch(i, 1, self._limits[i])
            await self._update()
            if self.num >= number:
                print('Found ' + str(self.num) + (' proxy' if self.num==1 else ' proxies'))
                return
        print('No available proxies')


    async def get_proxy(self):
        await self._available(1)
        return 'http://' + list(self.pool)[0]   # returns the url of a proxy


    async def get_proxies(self, number):
        await self._available(number)
        proxies = ['http://'+p for p in list(self.pool)[0:number]]
        return proxies   # returns a list of the url of proxies


async def test():
    pool = ProxyPool()
    print(await pool.get_proxy())
    print(await pool.get_proxy())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(test())
    loop.run_until_complete(future)