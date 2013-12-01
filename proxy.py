from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log
import sys
import gzip
import cStringIO
from BeautifulSoup import BeautifulSoup
import collections
import pickle

log.startLogging(sys.stdout)

def jumbler(bigstring,url):
    listofwords = bigstring.split(u' ')
    listofwords.sort()
    counter = collections.Counter(listofwords)
    f = open(url,'wb')
    pickle.dump(counter,f)
    f.close()

class MyProxyClient(proxy.ProxyClient):
    def __init__(self,command, rest, version, headers, data, father):
        self.debug = True
        self.grabit = False
        self.gunzipit = False
        self.buf = cStringIO.StringIO()
        self.father = father
        self.command = command
        self.rest = rest
        if 'accept-encoding' in headers:
            del headers['accept-encoding']
        if "proxy-connection" in headers:
            del headers["proxy-connection"]
            headers["connection"] = "close"
            headers.pop('keep-alive', None)
            self.headers = headers
            self.data = data
            
    def handleResponsePart(self,buffer):
        #print "buffer is %s" % buffer
        print "handle response part has been called"
        self.buf.write(buffer)
        #self.buf.seek(0,0)
        #print "buffer is",buffer
        self.father.write(buffer)

    def handleResponseEnd(self):
        """2013-11-30 16:29:31-0600 [MyProxyClient,client] headers are Headers({'content-length': ['253'], 
        'content-encoding': ['gzip'], 'vary': ['Accept-Encoding'], 
        'server': ['Yaws/1.84 Yet Another Web Server'], 'connection': ['close'], 
        'date': ['Sat, 30 Nov 2013 22:43:56 GMT'], 'content-type': ['text/html']})"""
        self.buf.seek(0,0) #before read, go to start?
        rawtext = ''
        if not self._finished:
            self._finished = True
            try:
                self.father.finish()
            except RuntimeError:
                # badness with calling .finish where something should be done with notifyFinish instead
                pass
            #print "headers are",self.father.responseHeaders
        # If it's text, do something about it.
        if self.father.responseHeaders.hasHeader('Content-Type'):
            contype = self.father.responseHeaders.getRawHeaders('Content-Type')
            print 'content-type is',contype
            for e in contype:
                if (e.startswith('text/plain') or e.startswith('text/html')):
                    if self.debug: print "We got a text header",e
                    self.grabit = True
        else:
            if self.debug: 
                print "Didn't get a content-type, that can't be good, headers are",self.father.responseHeaders
        # don't grabit if it's not text!
        if self.grabit:
            if self.father.responseHeaders.hasHeader('content-encoding'):
                enc = self.father.responseHeaders.getRawHeaders('content-encoding')
                if self.debug: print "content-encoding is",enc
                if 'gzip' in enc:
                    try:
                        g = gzip.GzipFile(mode="rb",fileobj=self.buf)
                        rawtext = g.read()
                        if self.debug: print "gunzip PASSED!"
                    except IOError as e:
                        self.buf.seek(0,0)
                        print "gzip FAILED! THIS IS BAD!",e
                        #rawtext=self.buf.read() # might work, why not?
            if not rawtext: 
                rawtext=self.buf.read()
            soup = BeautifulSoup(rawtext)
            souptext = soup.body.getText(separator=u' ')
            
            # dump into pickle of happiness
            requrl = self.father.uri[7:].replace('/','.')
            
            jumbler(souptext,'webrequests/' + requrl)
            # BET THIS WON'T WORK!

            print "souptext is",type(souptext),"and looks like",souptext
            f = open('souptext.txt','a')
            f.write(souptext.encode('utf-8'))
            f.write('\n</request>\n')
            f.close()
            #print "rawtext is %s" % rawtext
        self.transport.loseConnection()

class MyProxyClientFactory(proxy.ProxyClientFactory):
    protocol = MyProxyClient

class ProxyFactory(http.HTTPFactory):
    protocol = proxy.Proxy

class LoggingProxyRequest(proxy.ProxyRequest):
    protocols = {'http':MyProxyClientFactory}
    def process(self):
        """print out requests"""
        self.content.seek(0,0)
        val = self.content.getvalue()
        #print "Content is %s" % val
        #print "Request from %s for %s\nContent is %s" % (
        #    self.getClientIP(), self.getAllHeaders()['host'],self.content.getvalue())
        try:
            proxy.ProxyRequest.process(self)
            f = open('souptext.txt','a')
            f.write('<request>')
            f.write(self.uri + '\n')
            f.close()
        except KeyError:
            print "HTTPS is not supported"

class LoggingProxy(proxy.Proxy):
    requestFactory = LoggingProxyRequest

class LoggingProxyFactory(http.HTTPFactory):
    def buildProtocol(self,addr):
        return LoggingProxy()

reactor.listenTCP(8080, LoggingProxyFactory())
reactor.run()
