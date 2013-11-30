from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log
import sys
import gzip
import cStringIO
from BeautifulSoup import BeautifulSoup

log.startLogging(sys.stdout)

class MyProxyClient(proxy.ProxyClient):
    def __init__(self,command, rest, version, headers, data, father):
        self.grabit = False
        self.buf = cStringIO.StringIO()
        self.father = father
        self.command = command
        self.rest = rest
        if "proxy-connection" in headers:
            del headers["proxy-connection"]
            headers["connection"] = "close"
            headers.pop('keep-alive', None)
            self.headers = headers
            self.data = data
    # def handleHeader(self,key,value):
    #     if key == 'Content-Type':
    #         print "got a Content-Type"
    #         if value.startswith('text'):
    #             print "yes, we can grab text out of this one!"
    #             self.grabit = True
    #     proxy.ProxyClient.handleHeader(key,value)
    def handleResponsePart(self,buffer):
        #print "buffer is %s" % buffer
        self.buf.write(buffer)
        self.buf.seek(0,0)
        self.father.write(buffer)

    def handleResponseEnd(self):
        """2013-11-30 16:29:31-0600 [MyProxyClient,client] headers are Headers({'content-length': ['253'], 
        'content-encoding': ['gzip'], 'vary': ['Accept-Encoding'], 
        'server': ['Yaws/1.84 Yet Another Web Server'], 'connection': ['close'], 
        'date': ['Sat, 30 Nov 2013 22:43:56 GMT'], 'content-type': ['text/html']})"""
        if not self._finished:
            self._finished = True
            self.father.finish()
            #print "headers are",self.father.responseHeaders
            for h in self.father.responseHeaders:
                if (h.key.lower() == 'content-type') and h.value.startswith('text'):
                    self.grabit = True
                if (h.key.lower() == 'content-encoding' and h.value == 'gzip':
                    self.gunzipit = True
        if self.gunzipit:
            try:
                g = gzip.GzipFile(mode="rb",fileobj=self.buf)
                rawtext = g.read()
            except IOError:
                rawtext=self.buf.read() # might work, why not?
        soup = BeautifulSoup(rawtext)
        #print "soup text is ",soup.getText(separator=u' ')
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
        print "Content is %s" % val
        print "Request from %s for %s\nContent is %s" % (
            self.getClientIP(), self.getAllHeaders()['host'],self.content.getvalue())
        try:
            proxy.ProxyRequest.process(self)
        except KeyError:
            print "HTTPS is not supported"

class LoggingProxy(proxy.Proxy):
    requestFactory = LoggingProxyRequest

class LoggingProxyFactory(http.HTTPFactory):
    def buildProtocol(self,addr):
        return LoggingProxy()

reactor.listenTCP(8080, LoggingProxyFactory())
reactor.run()
