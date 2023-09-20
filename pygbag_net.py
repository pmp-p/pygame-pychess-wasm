import pygbag.aio as asyncio

import sys
import aio
import time
import socket
import select
import json
import base64


import io, socket


# TODO: use websockets module when on desktop to connect to service directly.


async def aio_sock_open(sock, host, port):
    print(f"20:aio_sock_open({host=},{port=}) {aio.cross.simulator=}")
    if aio.cross.simulator:
        host, trail = host.strip(":/").split("/", 1)
        port = int(trail.rsplit("/", 1)[-1])
        print(f"21:aio_sock_open({host=},{port=})")

    while True:
        try:
            sock.connect(
                (
                    host,
                    port,
                )
            )
        except BlockingIOError:
            await aio.sleep(0)
        except OSError as e:
            # 30 emsdk, 106 linux means connected.
            if e.errno in (30, 106):
                return sock
            sys.print_exception(e)


class aio_sock:
    def __init__(self, url, mode, tmout):
        host, port = url.rsplit(":", 1)
        self.port = int(port)
        # we don't want simulator to fool us
        if __WASM__ and __import__("platform").is_browser:
            if not url.startswith("://"):
                pdb(f"switching to {self.port}+20000 as websocket")
                self.port += 20000
            else:
                _, host = host.split("://", 1)

        self.host = host

        self.socket = socket.socket()
        # self.sock.setblocking(0)

    # overload socket directly ?

    def fileno(self):
        return self.sock.fileno()

    def send(self, *argv, **kw):
        self.sock.send(*argv, **kw)

    def recv(self, *argv):
        return self.sock.recv(*argv)

    # ============== specific ===========================

    async def __aenter__(self):
        # use async
        print("64: aio_sock_open", self.host, self.port)
        await aio_sock_open(self.socket, self.host, self.port)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        aio.protect.append(self)
        aio.defer(self.socket.close, (), {})
        del self.port, self.host, self.socket

    def read(self, size=-1):
        return self.recv(0)

    def write(self, data):
        if isinstance(data, str):
            return self.socket.send(data.encode())
        return self.socket.send(data)

    def print(self, *argv, **kw):
        kw["file"] = io.StringIO(newline="\r\n")
        print(*argv, **kw)
        self.write(kw["file"].getvalue())

    def __enter__(url, mode, tmout):
        # use softrt (wapy)
        return aio.await_for(self.__aenter__())

    def __exit__(self, exc_type, exc, tb):
        # self.socket.close()
        pass


# TODO: get host url and lobby name from a json config on CDN
# to allow redirect to new server without breaking existing games.

# from enum import auto ?


class Node:
    CONNECTED = 0
    RX = 1
    PING = 2
    PONG = 3
    RAW = 4
    LOBBY = 5
    GAME = 6
    B64JSON = "b64json"

    host = "://pmp-p.ddns.net/wss/6667:443"
    lobby = "#pygbag"

    events = []

    def __init__(self, gid=0, host="", offline=False):
        self.aiosock = None
        self.gid = gid
        self.rxq = []
        self.txq = []
        self.offline = offline
        self.alarm_set = 0
        if not offline:
            aio.create_task(self.connect(host or self.host))

    async def connect(self, host):
        self.peek = []
        async with aio_sock(host, "a+", 5) as sock:
            self.host = host
            self.events.append(self.CONNECTED)
            self.aiosock = sock
            self.alarm()
            while not aio.exit:
                rr, rw, re = select.select([sock.socket], [], [], 0)
                if rr or rw or re:
                    while not aio.exit and self.aiosock:
                        try:
                            # emscripten does not honor PEEK
                            # peek = sock.socket.recv(1, socket.MSG_PEEK |socket.MSG_DONTWAIT)
                            one = sock.socket.recv(1, socket.MSG_DONTWAIT)
                            if one:
                                self.peek.append(one)
                                # full line let's send that to event processing
                                if one == b"\n":
                                    self.rxq.append(b"".join(self.peek))
                                    self.peek.clear()
                                    self.events.append(self.RX)
                                    break
                            else:
                                # lost con.
                                print("HANGUP", self.peek)
                                return
                        except BlockingIOError as e:
                            if e.errno == 6:
                                await aio.sleep(0)
                else:
                    await aio.sleep(0)
            sock.print("DISCONNECT")

    # default for data is speak into lobby with gameid>0
    def tx(self, obj):
        ser = json.dumps(obj)
        self.out(self.B64JSON + ":" + base64.b64encode(ser.encode("ascii")).decode("utf-8"), gid=self.gid)

    def lobby_cmd(self, *cmd, hint=""):
        data = ":".join(map(str, cmd))

        if hint:
            self.out(f"{data}§{hint}")
        else:
            self.out(data)

    # default for text is speak into lobby (gameid == 0)

    def out(self, *blocks, gid=-1):
        if gid < 0:
            gid = 0

        self.wire(f"PRIVMSG {self.lobby} :{gid}:{' '.join(map(str, blocks))}")

    # TODO: handle hangup/reconnect nicely (no flood)
    def wire(self, rawcmd):
        if self.offline:
            print("WIRE:", rawcmd)
        else:
            self.txq.append(rawcmd)
            if self.aiosock:
                while len(self.txq):
                    self.aiosock.print(self.txq.pop(0))

    def quit(self, msg="DISCONNECT"):
        self.out(msg)
        self.aiosock.socket.close()
        self.aiosock = None

    def process_data(self, line):
        if line.find(" PONG ") >= 0:
            self.proto, self.data = line.split(" PONG ")
            yield self.PONG
            return

        if line.find("PING :") >= 0:
            self.proto, self.data = line.split(":", 1)
            self.wire(line.replace("PING :", "PONG :"))
            yield self.PING
            return

        room = f" {self.lobby} :"

        self.proto = ""

        if line.find(room) > 0:
            self.proto, data = line.split(room, 1)
            game = f"{self.gid}:"

            if data.startswith(game):
                b64json = f"{self.B64JSON}:"
                data = data[len(game) :]
                if data.startswith(b64json):
                    data = data[len(b64json) :]
                    data = base64.b64decode(data.encode())
                try:
                    self.proto = "json"
                    self.data = json.loads(data.decode())
                except:
                    self.proto = "?"
                    self.data = data

                yield self.GAME
            else:
                self.data = data
                yield self.LOBBY

            return

        maybe_hint = line.rsplit("§", 1)

        if len(maybe_hint) > 1:
            self.hint = maybe_hint[-1]
            print("HINT", maybe_hint[-1])
        else:
            self.hint = ""

        self.data = line
        yield self.RAW

    def alarm(self):
        t = time.time()

        if t >= self.alarm_set:
            self.alarm_set = t + 30
            return self.alarm_set
        return 0

    def get_events(self):
        alarm = self.alarm()

        if alarm:
            self.wire(f"PING :{alarm}")

        while len(self.events):
            ev = self.events.pop(0)
            if ev == self.RX:
                while len(self.rxq):
                    data = self.rxq.pop(0).decode("utf-8").strip()
                    yield from self.process_data(data)
                continue

            elif ev == self.CONNECTED:
                nick = "pygamer_" + str(time.time())[-5:].replace(".", "")
                d = {"nick": nick, "channel": self.lobby}
                self.aiosock.print(
                    """CAP LS\r\nNICK {nick}\r\nUSER {nick} {nick} localhost :wsocket\r\nJOIN {channel}""".format(**d)
                )
                self.lobby_cmd(self.CONNECTED, hint="CONNECTED")

            else:
                print(f"? {ev=}")

            yield ev


async def main():
    global node
    global data
    data = {1: 2, "some": "data", "array": [1, 2, 3, "four"]}

    node = Node()

    while not aio.exit:
        node.get_events()
        await aio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
