import select

import Pyro4.core
import Pyro4.naming
import Pyro4.socketutil


def pyro_event_loop(name, obj, timeout=3.0, callback=None):
    Pyro4.config.SERVERTYPE = 'thread'
    my_ip = Pyro4.socketutil.getIpAddress(None, workaround127=True)

    nameserverUri, nameserverDaemon, broadcastServer = Pyro4.naming.startNS(host=my_ip)
    assert broadcastServer is not None
    daemon = Pyro4.core.Daemon(host=my_ip)
    serverUri = daemon.register(obj)
    nameserverDaemon.nameserver.register(name, serverUri)

    # Event loop
    while True:
        # Create sets of the socket objects we will be waiting on
        nameserverSockets = set(nameserverDaemon.sockets)
        pyroSockets = set(daemon.sockets)
        rs = [broadcastServer]  # only the broadcast server is directly usable as a select() object
        rs.extend(nameserverSockets)
        rs.extend(pyroSockets)
        rs, _, _ = select.select(rs, [], [], timeout)
        eventsForNameserver = []
        eventsForDaemon = []
        for s in rs:
            if s is broadcastServer:
                broadcastServer.processRequest()
            elif s in nameserverSockets:
                eventsForNameserver.append(s)
            elif s in pyroSockets:
                eventsForDaemon.append(s)
        if eventsForNameserver:
            nameserverDaemon.events(eventsForNameserver)
        if eventsForDaemon:
            daemon.events(eventsForDaemon)

        if callback is not None and callable(callback):
            callback()

    nameserverDaemon.close()
    broadcastServer.close()
    daemon.close()