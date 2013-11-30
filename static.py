from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

somelist = ['foo','bar','baz']

class Simple(Resource):
    isLeaf = True
    def render_GET(self, request):
        top = "<table>"
        bottom = "</table>"
        content = top
        for x in somelist:
            content += "<tr><td>%s</td></tr>" % x
        content += bottom
        return ("<html>dang it, world! %s</html>" % content) 

resource = Simple()
site = Site(resource)
reactor.listenTCP(8081, site)
reactor.run()
