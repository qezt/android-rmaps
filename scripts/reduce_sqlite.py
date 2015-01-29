# coding: utf8

# pylint: disable=C0301,C0103,C0111,W0612,R0914,R0915,R0913,W0703

'''
sqlite> .schema
CREATE TABLE android_metadata (locale TEXT);
CREATE TABLE info(minzoom,maxzoom);
CREATE TABLE tiles (x int, y int, z int, s int, image blob,
    PRIMARY KEY (x,y,z,s));
CREATE INDEX IND on tiles (x,y,z,s);
sqlite> select count(*) from tiles;
271083
sqlite>

file size: 4866228224


'''

import os
import re
import time
import random
from Queue import Queue, Empty as QueueEmpty

import sqlite3

from utils0 import fetchurl, Imaging


HOSTS = [
    '74.125.235.66',
    '173.194.126.134',
    '74.125.31.82',
    '74.125.23.101',
    '74.125.235.170',
    '173.194.126.149',
    '74.125.235.183',
    '74.125.235.97',
    '173.194.127.223',
    '173.194.126.140',
    '74.125.23.91',
    '173.194.126.129',
    '173.194.126.132',
    '74.125.235.172',
    '173.194.38.84',
    '173.194.126.130',
    '173.194.126.190',
    '173.194.126.133',
    '173.194.126.137',
    '74.125.23.113',
    '74.125.235.184',
    '74.125.235.110',
    '173.194.38.81',
    '173.194.126.135',
    '74.125.235.99',
    '173.194.126.150',
    '173.194.127.215',
    '173.194.38.70',
    '173.194.38.69',
    '74.125.23.93',
    '74.125.23.102',
    '74.125.23.136',
    '173.194.38.68',
    '74.125.23.190',
    '74.125.31.115',
    '74.125.23.95',
    '74.125.235.103',
    '173.194.127.216',
    '173.194.126.131',
    '173.194.38.80',
    '173.194.38.73',
    '74.125.235.100',
    '173.194.38.82',
    '173.194.38.72',
    '173.194.126.136',
    '173.194.127.111',
    '173.194.38.67',
    '74.125.23.100',
    '74.125.23.138',
    '173.194.38.78',
    '173.194.126.142',
    '173.194.38.66',
    '173.194.38.64',
    '173.194.38.71',
    '173.194.38.65',
    '74.125.235.171',
    '173.194.126.128',
    '74.125.128.120',
    '74.125.235.96',
    '173.194.38.83',
    '74.125.235.143',
    '173.194.126.138',
    '74.125.235.191',
    '74.125.235.104',
    '74.125.235.69',
    '74.125.235.64',
    '74.125.235.65',
    '203.208.48.155',
    '203.208.48.156',
    '173.194.126.139',
    '74.125.235.98',
    '74.125.23.139',
    '74.125.235.67',
    '74.125.235.101',
    '74.125.235.105',
    '74.125.235.68',
    '74.125.235.73',
    '74.125.235.78',
    '74.125.235.72',
    '74.125.235.71',
    '74.125.235.102',
    '74.125.235.70',
    '74.125.128.94',
    ]


# TOD0: East-AU.sqlitedb is incomplete

BASE_NAME = '3ya'
#BASE_NAME = 'xiamen'
#BASE_NAME = 'toAU'
#BASE_NAME = 'Cairns'
#BASE_NAME = 'Sydney'
#BASE_NAME = 'Brisbane'

OUT_DIR = 'honeymoon_out'

config = {
    'ifn': 'honeymoon/' + BASE_NAME + '.sqlitedb',
    'ofn': OUT_DIR + '/' + BASE_NAME + '.sqlitedb',
    'bad_fn': OUT_DIR + '/' + BASE_NAME + '.bad',
    'log_fn': OUT_DIR + '/' + BASE_NAME + '.log',
    #'recompress_quality': 25,
    'fetchers': 3,
    'write_buffer': 50,
    # satelite
    #'url': 'http://mt1.google.cn/vt/lyrs=s@122&hl=zh-CN&gl=CN&src=app&x=%(x)s&y=%(y)s&z=%(z)s&s=Galileo',
    # satelite https
    #'url': 'https://mts2.google.com/vt/lyrs=s@128&hl=zh-CN&gl=CN&src=app&x=%(x)s&y=%(y)s&z=%(z)s&s=Galileo',
    #'url': 'https://khms0.google.com/kh/v=142&src=app&x=%(x)s&y=%(y)s&z=%(z)s&s=Galileo',

    # satelite
    'recompress_quality': None,
    'url': 'https://%(host)s/kh/v=142&src=app&x=%(x)s&y=%(y)s&z=%(z)s&s=Galileo',
    'host': 'khms0.google.com',

    # overlay
    #'recompress_quality': None,
    #'url': 'http://%(host)s/vt/imgtp=png32&lyrs=h@245218574&hl=en&gl=CN&src=app&x=%(x)s&y=%(y)s&z=%(z)s&s=Galileo',

    #'host': 'mt2.google.cn',
    }


class Hosts(object):
    def __init__(self, hosts):
        self._hosts = dict((host, 0.0001) for host in hosts)

    def add_weight(self, host, weight):
        self._hosts[host] = self._hosts[host] * 0.7 + weight * 0.3

    def pick(self):
        host_weights = self._hosts.copy().items()
        new_weights = []
        W = 0
        for host, weight in sorted(host_weights, key=lambda x: x[1]):
            w = pow(1 / (weight + 0.0001), 2)
            new_weights.append((host, w))
            W += w
        pos = random.random() * W
        #print new_weights[:10]
        for host, weight in new_weights:
            if pos <= weight:
                return host
            pos -= weight
        return new_weights[-1][0]


host_picker = Hosts(HOSTS)


def extract_xyz(source_conn):
    c = source_conn.cursor()
    c.execute('select x, y, z from tiles')
    return c.fetchall()


#def get_xyzs(f):
    #min_zoom, max_zoom = f.readline().split()
    #min_zoom = int(min_zoom)
    #max_zoom = int(max_zoom)

    #def itr():
        #max_z = max_zoom
        #for line in f:
            #x, y, z0 = line.split()
            #x = int(x)
            #y = int(y)
            #z0 = int(z0)
            #yield x, y, max_z - z0, z0
    #return min_zoom, max_zoom, itr


TILE_503_LIMIT = [len(HOSTS)]


def fetchtile(x, y, z):
    url = config['url']
    BAD_WEIGHT = 10

    if TILE_503_LIMIT[0] <= 0:
        return None

    for i in xrange(len(HOSTS)):
        host_ip = host_picker.pick()
        start_time = time.time()
        try:
            log('before fetch')
            new_url = url % {'x': x, 'y': y, 'z': z, 'host': host_ip}
            log('fetching:', new_url)
            code, content = fetchurl(
                new_url,
                method='GET',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.9 Safari/537.36',
                    'Referer': 'https://maps.google.com/',
                    'Host': config['host'],
                    },
                timeout=3)
            log('fetched:', code)
            if code == 200:
                host_picker.add_weight(host_ip, time.time() - start_time)
                return content
            if code == 404:
                log('Tile 404:', x, y, z)
                host_picker.add_weight(host_ip, time.time() - start_time)
                return None
            if code == 503:
                TILE_503_LIMIT[0] -= 1
                host_picker.add_weight(host_ip, BAD_WEIGHT * 10)
            else:
                host_picker.add_weight(host_ip, BAD_WEIGHT)
            log('Bad host ip: ', host_ip)
            continue
        except Exception, e:
            time.sleep(1)
            log('Bad host ip:', host_ip)
            host_picker.add_weight(host_ip, BAD_WEIGHT)
            log_exception()
            continue
    return None


def compress(img_content, quality):
    img = Imaging.gen_image(img_content)
    if not img:
        return None
    return Imaging.get_image_buffer(
        img,
        format='JPEG',
        quality=quality,
        optimize=True,
        subsampling='4:4:4')

########################################################################
#
# logger
#
########################################################################
_log_queue = Queue(10)


def _logd(fn):
    log_file = open(fn, 'a', 0)

    while True:
        args = _log_queue.get()
        try:
            log_file.write(time.strftime('[%Y-%m-%d %H:%M:%S]') + ' [%d]' % (_log_queue.qsize()))
            for arg in args:
                log_file.write(' %s' % (arg, ))
            log_file.write('\n')
        except:
            log_exception()
            raise
        finally:
            _log_queue.task_done()


def log(*args):
    _log_queue.put(args)


def log_exception():
    import traceback
    info = traceback.format_exc()
    for idx, line in enumerate(info.splitlines()):
        log(line)


def writer(tile_queue, db_filename):
    result_conn = sqlite3.connect(db_filename)
    result_conn.text_factory = str
    c = result_conn.cursor()

    _id = 0
    dirty_writes = 0
    while True:
        img = None
        try:
            img_data = tile_queue.get(block=True, timeout=0.1)
            if img_data != -1:
                x, y, z, z0, img = img_data
        except QueueEmpty, e:
            continue

        if img:
            c.execute('INSERT INTO tiles VALUES (?, ?, ?, ?, ?)', (x, y, z0, 0, buffer(img)))
            dirty_writes += 1
            _id += 1

        if img_data == -1:
            tile_queue.task_done()

        if ((img_data == -1) or (dirty_writes % config['write_buffer'] == 0)) and dirty_writes:
            result_conn.commit()
            for i in xrange(dirty_writes):
                tile_queue.task_done()
            dirty_writes = 0


def proc_tile(x, y, z, z0, out_q, recompress_quality):
    try:
        img_content = fetchtile(x, y, z)
    except Exception as e:
        log_exception()
        return
    if img_content is None:
        log(x, y, z, z0, '[Bad]')
        return
    if recompress_quality:
        compressed = compress(img_content, recompress_quality)
        if compressed is None:
            log(x, y, z, z0, '[Bad Image]')
        else:
            #base = '%s_%s_%s' % (z, x, y)
            #with open('tmp/' + base + '.jpg', 'wb') as f:
                #f.write(img_content)
            #with open('tmp/' + base + '_raw.jpg', 'wb') as f:
                #f.write(compressed)
            log(x, y, z, z0, '[OK: %d -> %d]' % (len(img_content), len(compressed)))
            out_q.put((x, y, z, z0, compressed))
    else:
        log(x, y, z, z0, '[OK]')
        out_q.put((x, y, z, z0, img_content))


def fetcher(in_q, out_q, recompress_quality=True):
    while True:
        log('before get')
        x, y, z, z0 = in_q.get()
        log('got', x, y, z, z0)
        #log(in_q.qsize(), out_q.qsize())
        #in_q.task_done()
        #continue
        try:
            proc_tile(x, y, z, z0, out_q, recompress_quality)
        except Exception as e:
            log_exception()
        in_q.task_done()
        log('in_q:', in_q.qsize(), 'out_q', out_q.qsize())


def get_xyzs(conn):
    c = conn.cursor()
    c.execute('select minzoom, maxzoom from info')
    minzoom, maxzoom = c.fetchall()[0]

    c.execute('select x, y, z from tiles')
    xyzs = []
    for x, y, z0 in c.fetchall():
        xyzs.append((x, y, 17 - z0, z0))
    return minzoom, maxzoom, xyzs


def get_404_from_log(filename):
    bad_line_patt = re.compile(r'^\[[^]]+\] \[\d+\] Tile 404: (\d+ \d+ \d+)$')
    bad_ones = set()
    if not os.path.isfile(filename):
        return set()
    for line in open(filename).read().splitlines():
        m = bad_line_patt.match(line)
        if not m:
            continue
        x, y, z = [int(c) for c in m.groups()[0].split()]
        bad_ones.add((x, y, z, 17 - z))
    return bad_ones


def main():
    conn = sqlite3.connect(config['ifn'])
    minzoom, maxzoom, xyzs = get_xyzs(conn)
    conn.close()
    print 'Got from input:', len(xyzs)

    result_conn = sqlite3.connect(config['ofn'])
    result_conn.text_factory = str
    c = result_conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS android_metadata (locale TEXT);')
    c.execute('INSERT INTO android_metadata VALUES (\'zh_CN\');')
    c.execute('CREATE TABLE IF NOT EXISTS info(minzoom, maxzoom);')
    c.execute('DELETE FROM info')
    c.execute('INSERT INTO info VALUES (?, ?)', (minzoom, maxzoom))
    c.execute('CREATE TABLE IF NOT EXISTS tiles (x int, y int, z int, s int, image blob, PRIMARY KEY (x,y,z));')
    result_conn.commit()
    result_conn.close()

    fetch_queue = Queue(100)
    store_queue = Queue(100)

    from threading import Thread
    N = config['fetchers']
    fetchers = []
    for i in xrange(N):
        fetcher_thread = Thread(
            target=fetcher,
            kwargs={
                'in_q': fetch_queue,
                'out_q': store_queue,
                'recompress_quality': config['recompress_quality'],
                })
        fetcher_thread.daemon = True
        fetcher_thread.start()
        fetchers.append(fetcher_thread)

    log_thread = Thread(target=_logd, kwargs={'fn': config['log_fn']})
    log_thread.daemon = True
    log_thread.start()

    conn = sqlite3.connect(config['ofn'])
    tmp1, tmp1, got_xyzs = get_xyzs(conn)
    conn.close()
    got_xyzs = set(got_xyzs)
    print 'got xyzs:', len(got_xyzs)

    bad_xyzs = get_404_from_log(config['log_fn'])
    print '404s:', len(bad_xyzs)

    store_thread = Thread(target=writer, kwargs={'tile_queue': store_queue, 'db_filename': config['ofn']})
    store_thread.daemon = True
    store_thread.start()

    start_time = time.time()
    SPEED_MON_LENGTH = 512
    speed_mon = []
    fetch_counter = 0
    total_count = len(xyzs)
    for i, dot in enumerate(xyzs):
        if dot in got_xyzs or dot in bad_xyzs:
            continue
        fetch_counter += 1
        x, y, z, z0 = dot
        try:
            fetch_queue.put((x, y, z, z0))
            now = time.time()
            if speed_mon:
                current_speed = len(speed_mon) / (now - speed_mon[0])
                average_speed = fetch_counter / (now - start_time)
                log('put %s @ %.2f, %.2f avg, %.1f%%, done in %.0f secs' % (
                    dot, current_speed, average_speed,
                    i * 1000 / total_count / 10.0,
                    (total_count - i) / average_speed
                    ))
            speed_mon = speed_mon[-SPEED_MON_LENGTH:] + [now]
            #print('puted %s' % (dot, ))
        except KeyboardInterrupt as e:
            break

    print 'all pushed'
    log('all coordinates pushed')
    log('joining fetch queue')

    print 'joining fetcher'
    fetch_queue.join()

    print 'joining storage'
    store_queue.put(-1)
    log('joining store queue')
    store_queue.join()

    print 'joining logging'
    log('joining log queue')
    _log_queue.join()
    log('all set')


if __name__ == '__main__':
    main()
