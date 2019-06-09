# PixnetCrawler
This is a crawler for [Pixnet's blog posts](https://www.pixnet.net/blog).
It crawls the text in the title and the articles of each search results.
Proxies are used during the crawling to avoid the resource limitation from the server.

## Getting Started
### Prerequisites
There are some modules you need to install before running the program if they're not already on your machine.
- lxml: `pip install lxml`

   (references: <https://pypi.org/project/lxml/>)
- aiohttp: `pip install aiohttp`

   (references: <https://pypi.org/project/aiohttp/>)
- html2text: `pip install html2text`

   (references: <https://pypi.org/project/html2text/>)
- beautifulsoup4: `pip install BeautifulSoup4`

   (references: <https://pypi.org/project/beautifulsoup4/>)

### Installation
To get started, clone the repository to your machine.

`git clone https://github.com/owen841213/PixnetCrawler.git`

After that, set the arguments for your search following the tutorial down below.

## Usage
At first, you can check out for the available commands by typing `-h`.

**command**

```
python PixnetCrawler.py -h
```

**execution**
```
usage: PixnetCrawler.py [-h] -k KEYWORD [-s START] [-e END] [-t TIMEOUT]
                        [-r RECON] [-o OUTPUT]

This is an asyncronous crawler for Pixnet's blog posts.

optional arguments:
  -h, --help            show this help message and exit

search options:
  -k KEYWORD, --keyword KEYWORD
                        Keywords to search on Pixnet's blog
  -s START, --start START
                        The starting page index for crawling, default is 1.
  -e END, --end END     The ending page index for crawling, default is 10.

time related options:
  -t TIMEOUT, --timeout TIMEOUT
                        The acceptable time for the server's response.
  -r RECON, --recon RECON
                        The reconnection times if reconnection is needed.

output options:
  -o OUTPUT, --output OUTPUT
                        The name of the output file.
```

There multiple arguments that are available. It can be generally classify to three groups.

   1. search options:
   
      These are the arguments for customzing your search.
      
      `-k KEYWORD, --keyword KEYWORD`:
      This argument is required. KEYWORD specifies the phrases you want to search for.
      To search for two or more words, enclose them with double quotes `"`.
      
      **example**
      
      ```
      python PixnetCrawler.py -k "Deep Learning"
      ```
      
      - - -
      
      `-s START, --start START`:
      The page index you want to start for your search. Default is 1 and it must be an integer.
      
      **example**
      
      ```
      python PixnetCrawler.py -k "Deep Learning" -s 5
      ```
      
      - - -
         
      `-e END, --end END`:
      The page index you want to finish for your search. Default is 10 and it must be an integer.
      
      **example**
      
      ```
      python PixnetCrawler.py -k "Deep Learning" -e 20
      ```
      
   2. time related options:
   
      These arguments will have an impact on the excution time of the program.
      
      `-t TIMEOUT, --timeout TIMEOUT`:
      The maximum acceptable time (in seconds) for the program to wait for a server's response.
      Default is 25 seconds.
      
      **example**
      
      ```
      python PixnetCrawler.py -k "Deep Learning" -t 10
      ```
      
      - - -
      
      `-r RECON, --recon RECON`:
      The program will perform reconnections for "RECON" times.
      In some cases, unexpected errors may appear during connection.
      We can send the request again later through reconnection to get the response we expected.
      However, reconnection is a time consuming process.
      If you want a fast crawling regardless of the accuracy, you probably won't need reconnection.
      Otherwise, you may want to specify the maximum reconnection times according to your need.
      The default value is 3.
      
      If you don't need reconnection, set the argument to 0.
      
      ```
      python PixnetCrawler.py -k "Deep Learning" -r 0
      ```
      
      Otherwise, set it to the value you want.
      
      ```
      python PixnetCrawler.py -k "Deep Learning" -r 5
      ```
   
   3. output options:
      
      These arguments relate to your output files.
      
      `-o OUTPUT, --output OUTPUT`:
      OUTPUT is the name of your output file.
      Notice that it must includes the file extension.
      Enclose it with double quotes `"` if there're spaces contain in your filename.
      
      If there's no `-o` option , the default output will be "[your search keywords].txt"

      **example**
      
      ```python
      # the output file is "Deep Learning.txt"
      python PixnetCrawler.py -k "Deep Learning"
      ```
      
      **example**
      
      ```python
      python PixnetCrawler.py -k "Deep Learning" -o deep_learning.txt
      ```
      
      **example**
      
      ```python
      # enclose filename with quotes if spaces exists
      python PixnetCrawler.py -k "Deep Learning" -o "deep learning.txt"
      ```
      
