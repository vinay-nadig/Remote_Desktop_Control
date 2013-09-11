import sys
import argparse
import urllib
import urlparse
import re

from mechanize import Browser
from BeautifulSoup import BeautifulSoup

sys.path.append("~/project")

_CMD_NAME = "Movie"
_CMD_LONG_NAME = "Movierating"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise

class MyOpener(urllib.FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'
   
class Movierating(object):
          
    def __init__(self, options, sm, number, signature):
        self.flag=1
        self.privilaged=False
        self.msg=""
        self.to_no=number
        self.sm=sm
        self.options=options
        self.sig=signature
        self.parser=argparse.ArgumentParser(description="Argument parser for obtaining IMDB rating")
        self.parser.add_argument("Title",help="specify movie title",action="store")
        try:
            self.arguments=self.parser.parse_args(self.options)
        except:
            self.msg="usage: Movierating Title"
            self.flag=0
            return				
        
    def getRating(self):
        self.found=False
        self.BASE_URL ='http://www.imdb.com'
        self.title = self.arguments.Title
        self.name= self.title
        self.movie = '_'.join(self.title.split())
        br = Browser()
        url = "%s/find?s=tt&q=%s" % (self.BASE_URL, self.movie)
        try:
            br.open(url)            
        except:
            self.msg="internet connection error or movie not found"
            return
        if re.search(r'/title/tt.*', br.geturl()):
            #self.url = "%s://%s%s" % urlparse.urlparse(br.geturl())[:3]
            soup = BeautifulSoup( MyOpener().open(url).read() )
        else:
            try:
                self.link = br.find_link(url_regex = re.compile(r'/title/tt.*'))
            except:
                self.msg="Movie not found"
                return
            res = br.follow_link(self.link)
            #self.url = urlparse.urljoin(self.BASE_URL, self.link.url)
            soup = BeautifulSoup(res.read())
        try:
            self.title=soup.find('h1',{'class':'header'}).find('span',{'class':'itemprop'}).contents[0]
            for span in soup.findAll('span'):
                if span.has_key('itemprop') and span['itemprop'] == 'ratingValue':
                    self.rating = span.contents[0]
                    break
            self.year=soup.find('span',{'class':'nobr'}).find('a').contents[0]
            self.nusers=soup.find('div',{'class':'star-box-details'}).find('a').find('span').contents[0]
            self.found=True
        except:
            pass
        if self.found:
            self.msg="{0} {1}, RATING: {2}/10.0 from {3} people ".format(self.title.upper(),self.year,self.rating,self.nusers)  
        else:
            self.msg="Movie Not found"

    def send_sms(self):
        if self.flag==1:
            self.getRating()
            msg = {
               'Text' : self.msg,
               'SMSC' : {'Location' : 1},
               'Number' : self.to_no,
                }
        print self.msg
  	self.sm.SendSMS(msg)
        


#a=Movierating(['django unchained'],"123","123","123")
#a.send_sms()
