from collections import defaultdict
import logging
import re

import requests

from regparser import content
from regparser.layer.layer import Layer
import settings


logger = logging.getLogger(__name__)


def check_url(url):
    """Verify that content exists at a given URL"""
    response = requests.head(url)

    if response.status_code == requests.codes.not_implemented:
        response = requests.get(url)

    if response.status_code == requests.codes.ok:
        return url


def gid_to_url(gid):
    """Take a few guesses as to where this image may be"""
    override = content.ImageOverrides().get(gid)
    if override and check_url(override):
        return override
    elif override:
        logger.warning("Overridden image 404s: %s->%s", gid, override)

    upper_url = settings.DEFAULT_IMAGE_URL % gid
    if check_url(upper_url):
        return upper_url

    lower_url = settings.DEFAULT_IMAGE_URL % gid.lower()
    if not check_url(lower_url):
        logger.warning("No image could be found for %s. Tried:\n%s\n%s",
                       gid, upper_url, lower_url)
    return lower_url


class Graphics(Layer):
    gid = re.compile(ur'!\[(?P<alt>[\w\s]*)\]\((?P<gid>[a-zA-Z0-9.\-]+?)\)')
    ext = re.compile(r'\.(png|gif|jpg)$')
    shorthand = 'graphics'

    def check_for_thumb(self, url):
        thumb_url = self.ext.sub(r'.thumb\g<0>', url)
        return check_url(thumb_url)

    def process(self, node):
        """If this node has a marker for an image in it, note where to get
        that image."""
        matches_by_text = defaultdict(list)
        for match in Graphics.gid.finditer(node.text):
            matches_by_text[match.group(0)].append(match)

        layer_el = []
        for text in matches_by_text:
            match = matches_by_text[text][0]
            url = gid_to_url(match.group('gid'))
            layer_el_vals = {
                'text': match.group(0),
                'url': url,
                'alt': match.group('alt'),
                'locations': list(range(len(matches_by_text[text])))
            }
            thumb_url = self.check_for_thumb(url)

            if thumb_url:
                layer_el_vals['thumb_url'] = thumb_url
            layer_el.append(layer_el_vals)

        if layer_el:
            return layer_el
