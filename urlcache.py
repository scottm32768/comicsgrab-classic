#!/usr/bin/python
# Comics Grabber by Tom Parker <palfrey@bits.bris.ac.uk>
# http://www.bits.bris.ac.uk/palfrey/
#
# URL Caching class
# Caches retrieved URLs, with some comic-optimised sections
#
# Released under the GPL Version 2 (http://www.gnu.org/copyleft/gpl.html)

import os, hashlib
from pickle import dump, load
import urllib.request
import urllib.error
import urllib.parse
from URLTimeoutCommon import URLTimeoutError
import subprocess

try:
    import requests
except ImportError:
    requests = None

debug = True


class CacheError(Exception):
    pass


class RequestsInfoAdapter:
    def __init__(self, content_type):
        if content_type is None:
            content_type = ""
        self.content_type = content_type.split(";", 1)[0].strip().lower()

    def getmaintype(self):
        if "/" in self.content_type:
            return self.content_type.split("/", 1)[0]
        return ""

    def getsubtype(self):
        if "/" in self.content_type:
            return self.content_type.split("/", 1)[1]
        return ""


class RequestsResponseAdapter:
    def __init__(self, response):
        self.response = response

    def read(self):
        return self.response.content

    def info(self):
        return RequestsInfoAdapter(self.response.headers.get("content-type", ""))


def get_url_with_requests(url, ref=None, proxy="", timeout=120):
    if requests is None:
        raise URLTimeoutError("The requests module is required for HTTPS support")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    if ref is not None:
        headers["Referer"] = ref

    proxies = None
    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy,
        }

    response = requests.get(
        url,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
        allow_redirects=True,
        verify=True,
    )

    if response.status_code == 403:
        return get_url_with_curl(url, ref=ref, timeout=timeout)

    response.raise_for_status()
    return RequestsResponseAdapter(response)


def url_exists(url, ref=None, proxy="", timeout=120):
    if requests is None:
        raise URLTimeoutError("The requests module is required for HTTPS support")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    if ref is not None:
        headers["Referer"] = ref

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}

    try:
        response = requests.head(
            url,
            headers=headers,
            proxies=proxies,
            timeout=timeout,
            allow_redirects=True,
            verify=True,
        )
    except requests.RequestException as err:
        raise URLTimeoutError(str(err))

    if response.status_code == 403:
        return url_exists_with_curl(url, ref=ref, timeout=timeout)

    if response.status_code == 404:
        return False

    response.raise_for_status()
    return True


def url_exists_with_curl(url, ref=None, timeout=120):
    cmd = [
        "curl",
        "-I",
        "-L",
        "--silent",
        "--show-error",
        "--max-time",
        str(timeout),
        "-o",
        "/dev/null",
        "-w",
        "%{http_code}",
    ]

    if ref is not None:
        cmd.extend(["-e", ref])

    cmd.append(url)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode != 0:
        raise URLTimeoutError("curl failed: " + err.decode("utf-8", errors="replace"))

    try:
        status = int(out.decode("ascii"))
    except ValueError:
        raise URLTimeoutError("curl returned invalid HTTP status while checking " + url)

    if status == 404:
        return False

    if 200 <= status < 300:
        return True

    raise URLTimeoutError("HTTP status %d while checking %s" % (status, url))


def get_url_with_curl(url, ref=None, timeout=120):
    cmd = [
        "curl",
        "-L",
        "--silent",
        "--show-error",
        "--fail",
        "--max-time",
        str(timeout),
    ]

    if ref is not None:
        cmd.extend(["-e", ref])

    cmd.append(url)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode != 0:
        raise URLTimeoutError("curl failed: " + err.decode("utf-8", errors="replace"))

    return CurlResponseAdapter(out)


class URLCache:
    STAT_START = 1
    STAT_NEW = 2
    STAT_UNCHANGED = 3
    STAT_FAILED = 4

    def __init__(self, cache_dir, proxy=""):
        self.store = {}
        self.cache = cache_dir
        self.proxy = proxy
        if not os.path.exists(self.cache):
            os.makedirs(self.cache)
        else:
            for f in os.listdir(self.cache):
                try:
                    old = load(open(os.path.join(self.cache, f), "rb"))
                    if old.mime[0] == "image":
                        old.status = self.STAT_UNCHANGED
                    else:
                        old.status = self.STAT_START
                    old.used = False
                    self.store[self.md5(old.url, old.ref)] = old

                except (EOFError, ValueError):  # ignore and discard
                    os.unlink(os.path.join(self.cache, f))

    def cleanup(self):
        for h in list(self.store.keys()):
            if self.store[h].status != self.STAT_FAILED and self.store[h].used == False:
                os.unlink(os.path.join(self.cache, h))

    def md5(self, url, ref):
        m = hashlib.md5()
        m.update(url.encode("utf-8"))
        m.update(str(ref).encode("utf-8"))
        return m.hexdigest()

    def set_varying(self, url, ref=None):
        hash = self.md5(url, ref)
        if hash in self.store:
            self.store[hash].status = self.STAT_START

    def used(self, url, ref=None):
        hash = self.md5(url, ref)
        if hash in self.store:
            self.store[hash].used = True

    def get(self, url, ref=None):
        hash = self.md5(url, ref)
        if hash in self.store:
            old = self.store[hash]
        else:
            old = URLData(url, ref)
            self.store[hash] = old
        if old.status == self.STAT_FAILED:
            return None

        if old.status == self.STAT_START:
            try:
                # if ref==None:
                # 	data = urllib2.urlopen(url)
                # else:
                # 	r = urllib2.Request(url)
                # 	r.add_header("Referer",ref)
                # 	data = urllib2.urlopen(r)
                data = get_url_with_requests(url, ref, proxy=self.proxy)

            except requests.exceptions.HTTPError as err:
                if err.response is not None and err.response.status_code == 404:
                    return None
                else:
                    if ref != None:
                        refpath = os.path.join(self.cache, self.md5(ref, None))
                        if os.path.exists(refpath):
                            os.unlink(refpath)
                            print("Destroyed", refpath, "because of error!")
                    self.gen_failed(old)
                    raise CacheError(
                        str(err)
                        + ' while getting <a href="'
                        + url
                        + '">'
                        + url
                        + "</a>"
                    )

            except requests.exceptions.RequestException as err:
                self.gen_failed(old)
                raise CacheError(
                    str(err) + ' while getting <a href="' + url + '">' + url + "</a>"
                )

            except urllib.error.HTTPError as err:
                if err.code == 404:
                    return None
                else:
                    if ref != None:
                        refpath = os.path.join(self.cache, self.md5(ref, None))
                        if os.path.exists(refpath):
                            os.unlink(refpath)
                            print("Destroyed", refpath, "because of error!")
                    self.gen_failed(old)
                    raise CacheError(
                        err.msg + ' while getting <a href="' + url + '">' + url + "</a>"
                    )
            except urllib.error.URLError as err:
                self.gen_failed(old)
                raise CacheError(
                    err.reason[1]
                    + ' while getting <a href="'
                    + url
                    + '">'
                    + url
                    + "</a>"
                )

            except URLTimeoutError as err:
                # self.gen_failed(old)
                raise CacheError(
                    str(err) + ' while getting <a href="' + url + '">' + url + "</a>"
                )

            content = data.read()
            mime = (data.info().getmaintype(), data.info().getsubtype())

            if mime[0] == "text" and isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")

            if old.content != content:
                old.status = self.STAT_NEW
                old.content = content
                old.length = len(content)
                old.mime = mime
                f = open(os.path.join(self.cache, hash), "wb")
                dump(old, f, False)
            else:
                old.status = self.STAT_UNCHANGED
        old.used = True
        return old

    def gen_failed(self, old):
        old.status = self.STAT_FAILED
        old.content = ""
        old.length = 0
        old.mime = ("", "")

    def get_mult(self, url, ref=None, count=1):
        retry = 0
        last_err = None

        while retry < count:
            try:
                return self.get(url, ref)
            except CacheError as err:
                last_err = err
                if str(err).find("Timed out") == -1:
                    break
                retry += 1
                if retry != count:
                    print("retrying...")

        hash = self.md5(url, ref)
        self.store[hash] = URLData(url, ref)
        self.gen_failed(self.store[hash])
        raise last_err


class URLData:
    def __init__(self, url, ref):
        self.url = url
        self.ref = ref
        self.content = ""
        self.status = URLCache.STAT_START


class CurlInfoAdapter:
    def __init__(self, content):
        c = content.lstrip()
        if c.startswith(b"<"):
            self.mime = ("text", "html")
        elif c.startswith(b"\xff\xd8"):
            self.mime = ("image", "jpeg")
        elif c.startswith(b"\x89PNG"):
            self.mime = ("image", "png")
        elif c.startswith(b"GIF87a") or c.startswith(b"GIF89a"):
            self.mime = ("image", "gif")
        else:
            self.mime = ("", "")

    def getmaintype(self):
        return self.mime[0]

    def getsubtype(self):
        return self.mime[1]


class CurlResponseAdapter:
    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content

    def info(self):
        return CurlInfoAdapter(self.content)
