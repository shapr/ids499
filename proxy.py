from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log
import sys
import gzip
import cStringIO

log.startLogging(sys.stdout)

class MyProxyClient(proxy.ProxyClient):
    def __init__(self,command, rest, version, headers, data, father):
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
    def handleResponsePart(self,buffer):
        print "buffer is %s" % buffer
        self.buf.write(buffer)
        self.buf.seek(0,0)
        self.father.write(buffer)

    def handleResponseEnd(self):
        if not self._finished:
            self._finished = True
            self.father.finish()
            g = gzip.GzipFile(mode="rb",fileobj=self.buf)
            rawtext = g.read()
            print "rawtext is %s" % rawtext
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
