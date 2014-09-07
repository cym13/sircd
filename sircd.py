#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# LICENSE
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# END_OF_LICENSE

#
# Interesting stuff: http://www.networksorcery.com/enp/protocol/irc.htm
#                    http://www.networksorcery.com/enp/rfc/rfc2812.txt
#                    http://www.irchelp.org/irchelp/rfc/chapter2.html
"""
Usage: sircd.py [PORT]

Option:
    PORT        Port on which the server will listen. Default is 6667
"""

import sys
import socketserver
from docopt import docopt
from collections import defaultdict


class IrcHandler(socketserver.StreamRequestHandler):
    channels = defaultdict(set)
    clients  = defaultdict()

    def __init__(self, *args):
        self.nick      = None
        self.identity  = None
        self.host      = None
        self.real_name = None

        socketserver.StreamRequestHandler.__init__(self, *args)

    def handle(self):
        """
        Analyse and handle the IRC requests, see RFC2812 and RFC1459
        """

        while True:
            data = self.rfile.readline().decode("utf8").lstrip().rstrip("\r\n")
            print(self.nick, "->", data)

            if data.startswith("NICK"):
                if self.nick is not None:
                    IrcHandler.pop(self.nick)

                self.nick = data.split()[-1]
                IrcHandler.clients[self.nick] = self


            elif data.startswith("USER"):
                splitted       = data.split()
                self.identity  = splitted[1]
                self.host      = splitted[2]
                self.real_name = splitted[4]

                self.send(self.nick, "001 %s Welcome!" % self.nick)

            elif data.startswith("JOIN"):
                chan = data.split()[-1]
                IrcHandler.channels[chan].add(self.nick)
                self.send(None, "JOIN %s %s: %s" % (chan, chan, chan))
                self.send(self.nick, "332 %s:" % chan)

                user_list = ' '.join(x for x in IrcHandler.channels[chan])
                self.send(self.nick, "322 %s : %s" % (chan, user_list))


            elif data.startswith("PRIVMSG"):
                data    = data.lstrip("PRIVMSG ")
                sep     = data.find(' ')

                if sep == -1:
                    target  = data
                    message = ""
                else:
                    target  = data[:sep]
                    message = data[sep+1:]

                self.send(target, message)


            elif data.startswith("WHOIS"):
                target  = data.split()[1]

                client  = IrcHandler.clients[target]
                message = str("311 %s %s %s %s" % (client.nick,
                                                   client.identity,
                                                   client.host,
                                                   client.real_name))

                self.send(self.nick, message)


            elif data.startswith("PART"):
                data    = data.lstrip("PART ")
                sep     = data.find(' ')

                message = "PART "
                if sep == -1:
                    chan    = data
                    message += self.nick
                else:
                    chan    = data[:sep]
                    message += data[sep+1:]

                if not chan.startswith("#"):
                    chan = "#" + chan

                self.send(chan, message)
                try:
                    IrcHandler.channels[chan].remove(self.nick)
                except KeyError:
                    pass


            elif data.startswith("QUIT"):
                message = "ERROR " + data[5:]
                self.send(None, message)
                IrcHandler.clients.pop(self.nick)

                for chan in IrcHandler.channels:
                    if self.nick in chan:
                        chan.remove(self.nick)

                self.finish()
                break


            elif data.startswith("PING"):
                self.send(self.nick, "PONG")


            elif data.startswith("WHO"):
                self.send("352")

            else:
                # Well... can't really implement error gestion as all valid
                # requests are not handled yet and that might confuse clients
                pass


    def send(self, target, message):
        """
        Used to send a message between clients
        """
        message  = ":%s!sircd " % self.nick + message
        message += "\r\n"
        message  = message.encode("utf8")


        if target is None:  # Convention here to say everybody in sight
            nicks = set()
            for chan, users in IrcHandler.channels.items():
                if self.nick in users:
                    nicks = nicks.union(users)

        elif target.startswith("#"):
            nicks = IrcHandler.channels[target]

        else:
            nicks = [target]

        for nick in nicks:
            client = IrcHandler.clients[nick]

            if client is not None:
                print(nick, "<-", message)
                client.wfile.write(message)


def main():
    args = docopt(__doc__)
    host = "localhost"
    port = int(args["PORT"] or 6667)

    try:
        server = socketserver.TCPServer((host, port), IrcHandler)
    except OSError as e:
        print(e, ":", port, "on", host)
        sys.exit(1)

    server.serve_forever()

if __name__ == "__main__":
    main()
