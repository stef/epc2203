#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# (C) 2012, Stefan Marsiske <stefan.marsiske@gmail.com>

import urllib2, cookielib, sys, time
from lxml.html.soupparser import parse
from optparse import OptionParser

host='http://192.168.100.1'
keyurl="http://192.168.100.1/_aslvl.asp"
username="admin"
password="W2402"
passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
passman.add_password(None, host, username, password)

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
                              urllib2.HTTPBasicAuthHandler(passman))

static=[ "system/Name",
         "system/Modem Serial Number",
         "system/Cable Modem MAC Address",
         "system/Hardware Version",
         "system/Software Version",
         "system/Vendor",
         "system/Boot Revision",
         "system/Software Revision",
         "system/MTA Serial Number",
         "system/Firmware Name",
         "system/Firmware Build Time",
         "status/Configuration File",
         "signal/Modulation",
         ]

dynamic=[ "system/Receive Power Level",
          "system/Transmit Power Level",
          "system/Cable Modem Status",
          "signal/Downstream Status",
          "signal/Channel ID",
          "signal/Downstream Frequency",
          "signal/Bit Rate",
          "signal/Power Level",
          "signal/Signal to Noise Ratio",
          "signal/Upstream Status",
          "signal/Channel ID",
          "signal/Upstream Frequency",
          "signal/Modulation",
          "signal/Symbol Rate",
          "signal/Power Level",
          "status/Cable Modem Status",
          "status/IP Address",
          "status/Current Time",
          "status/Time Since Last Reset",
          "status/Cable Modem Certificate",
          "status/Computers Detected",
          "status/WAN Isolation",
          ]

ifs=[ "status/Cable: Cable Modem Interface",
      "status/MTA: PacketCable Embedded Interface",
      "status/LAN: Ethernet Interface",
      "status/USB: USB Interface"]

def split(txt):
    return txt.split(' ')[0]

def bool(txt):
    return txt.lower() in ['operational', 'on', 'installed']

def fetch(url, retries=5, params=None):
    try:
        f=opener.open(url, params)
    except (urllib2.HTTPError, urllib2.URLError), e:
        if retries>0:
            time.sleep(4*(6-retries))
            f=fetch(url, retries-1, params=params)
        else:
            raise
    return f

def totext(node):
    return u' '.join(u' '.join([x.strip() for x in node.xpath(".//text()") if x.strip()]).replace(u"\u00A0",' ').split())

def dump(pages=['system','signal','status','log','emta']):
    for page in pages:
        root=parse(fetch("%s/%s.asp" % (host, page)))
        for x in root.xpath(".//tr"):
            fields=[totext(t) for t in x.xpath('./td')]
            if filter(None,fields) and fields!=['']:
                print ':'.join(fields)
        print

def getvals(keys):
    for page in ['system','signal','status']:
        root=parse(fetch("%s/%s.asp" % (host, page)))
        for x in root.xpath(".//tr"):
            fields=[totext(t) for t in x.xpath('./td')]
            if "%s/%s" % (page, fields[0]) in keys:
                print fields[0], fields[1]

def getfields(keys):
    for page in ['system','signal','status']:
        root=parse(fetch("%s/%s.asp" % (host, page)))
        for x in root.xpath(".//tr"):
            fields=[totext(t) for t in x.xpath('./td')]
            if "%s/%s" % (page, fields[0]) in keys:
                print fields[0], fields[1]

def interfaces():
    print "Interface Name\tProvisioned\tState\tSpeed\tMAC Address"
    root=parse(fetch("%s/status.asp" % host))
    for x in root.xpath(".//tr"):
        fields=[totext(t) for t in x.xpath('./td')]
        if "status/%s" % fields[0] in ifs:
            print fields[0], '\t', '\t'.join(fields[1:])

def munin():
    muninfields=["system/Receive Power Level", "system/Transmit Power Level", "signal/Signal to Noise Ratio"]
    for page in ['system','signal','status']:
        root=parse(fetch("%s/%s.asp" % (host, page)))
        for x in root.xpath(".//tr"):
            fields=[totext(t) for t in x.xpath('./td')]
            key="%s/%s" % (page, fields[0])
            if key in muninfields:
                print "%s.value %s" % (fields[0].lower().replace(' ','_'), split(fields[1]))

def munin_freq():
    root=parse(fetch("%s/signal.asp" % host))
    for x in root.xpath(".//tr"):
        fields=[totext(t) for t in x.xpath('./td')]
        if fields[0].endswith("stream Frequency"):
            print "%s.value %s" % (fields[0].lower().replace(' ','_'), split(fields[1]))

def munin_speed():
    root=parse(fetch("%s/signal.asp" % host))
    modmap={'BPSK': 1, 'QPSK': 2, '8PSK': 3, '16QAM': 4, '32QAM': 5, '64QAM': 6, '256QAM': 8, }
    c=0
    for x in root.xpath(".//tr"):
        fields=[totext(t) for t in x.xpath('./td')]
        if fields[0]=="Modulation":
            c=modmap[fields[1]]
            continue
        if fields[0]=="Bit Rate":
            print "downstream_bitrate.value %.3f" % (int(split(fields[1]))/8000000.0)
            continue
        if fields[0]=="Symbol Rate":
            print "upstream_bitrate.value %.3f" % (int(split(fields[1]))*c/8000.0)
            continue

def display_config():
    print "graph_title cable modem power levels"
    print "graph_vlabel dBmV"
    print "graph_category network"
    print "graph_info This graph shows receive and transmit power levels of the Scientific-Atlanta cable modem."
    print "receive_power_level.label receive"
    print "receive_power_level.info Receive power level"
    print "receive_power_level.draw LINE2"
    print "receive_power_level.type GAUGE"
    print "transmit_power_level.label transmit"
    print "transmit_power_level.info Transmit power level"
    print "transmit_power_level.draw LINE2"
    print "transmit_power_level.type GAUGE"
    print "signal_to_noise_ratio.label signal_to_noise_ratio"
    print "signal_to_noise_ratio.info dBmV"
    print "signal_to_noise_ratio.draw LINE2"
    print "signal_to_noise_ratio.type GAUGE"

def freq_config():
    print "graph_title cable modem frequencies"
    print "graph_vlabel Hz"
    #print "graph_args --base 1000000"
    print "graph_category network"
    print "graph_info This graph shows receive and transmit frequencies of the Scientific-Atlanta cable modem."
    print "downstream_frequency.label receive"
    print "downstream_frequency.info RX freq"
    print "downstream_frequency.draw LINE2"
    print "downstream_frequency.type GAUGE"
    print "upstream_frequency.label transmit"
    print "upstream_frequency.info TX freq"
    print "upstream_frequency.draw LINE2"
    print "upstream_frequency.type GAUGE"

def freq_speed():
    print "graph_title cable modem speeds"
    print "graph_vlabel MB/s"
    print "graph_category network"
    print "graph_info This graph shows receive and transmit speeds of the Scientific-Atlanta cable modem."
    print "downstream_bitrate.label receive"
    print "downstream_bitrate.info RX speed"
    print "downstream_bitrate.draw LINE2"
    print "downstream_bitrate.type GAUGE"
    print "upstream_bitrate.label transmit"
    print "upstream_bitrate.info TX speed"
    print "upstream_bitrate.draw LINE2"
    print "upstream_bitrate.type GAUGE"

if __name__ == "__main__":
    # login
    auth=fetch(keyurl)
    # change access level
    params={'SAAccessLevel': '3', 'SAUsername': username, 'SAPassword': password}
    authurl="http://192.168.100.1/goform/_aslvl"
    auth=fetch(authurl,params='&'.join(['='.join(x) for x in params.items()]))

    # munin config mode
    if len(sys.argv)==2 and sys.argv[1]=='config':
        if __file__.endswith('_freq'):
            freq_config()
        elif __file__.endswith('_speed'):
            freq_speed()
        else:
            display_config()
        sys.exit(0)

    # munin mode
    if len(sys.argv)==1:
        if __file__.endswith('_freq'):
            # report frequencies if ending in _freq
            munin_freq()
        elif __file__.endswith('_speed'):
            # report speeds if ending in _speed
            munin_speed()
        else:
            munin()
        sys.exit(0)

    usage = "usage: %prog [options] | config"
    parser = OptionParser(usage)
    parser.add_option("-a", "--all", dest="all",
                      help="display all readings", action="store_true")
    parser.add_option("-i", "--interfaces", dest="interfaces",
                      help="display interfaces", action="store_true")
    parser.add_option("-s", "--static", help="display static properties",
                      action="store_true", dest="static")
    parser.add_option("-l", "--log", help="display log entries",
                      action="store_true", dest="log")
    parser.add_option("-e", "--emta", help="display emta entries",
                      action="store_true", dest="emta")
    parser.add_option("-m", "--metrics", help="display metrics",
                      action="store_true", dest="metrics")
    parser.add_option("-g", "--get", help="get metric",
                      action="append", dest="get")
    (options, args) = parser.parse_args()

    if options.all or options.interfaces:
        interfaces()
    if options.all or options.static:
        getvals(static)
    if options.all or options.log:
        dump(['log'])
    if options.all or options.emta:
        dump(['emta'])
    if options.all or options.metrics:
        getvals(dynamic)
    if options.get:
        getfields(options.get)
