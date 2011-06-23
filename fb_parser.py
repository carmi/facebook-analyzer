#!/usr/local/bin/python

# Author: Evan Carmi : ecarmi.org
# Version: 0.1 - 20110618

"""
A tool to parse and analyse a downloaded Facebook profile.

Instructions: execute `python fb_parser.py` in the same directory that Facebook's
index.html is located.
"""
import os, sys, re

from datetime import datetime
import json
from collections import Counter, defaultdict

from BeautifulSoup import BeautifulSoup

class Post:
  def __init__(self, profile, time, privacy, comment, text, count):
    self.profile = profile
    self.time = time
    self.privacy = privacy
    self.comment = comment
    self.text = text
    self.count = count

  def __str__(self):
    return 'Post by %s on %s' % (self.profile, self.time)

  def date(self):
    return self.time.date()

  def month_js(self):
    """
    Return a string for use in building a javascript Date object for month
    where post was created.
    Note: Months are (0 - 11) in JS.
    """
    return "%s-%s" % (self.time.strftime('%Y'), (int(self.time.strftime("%m")) - 1))


  def year_js(self):
    """
    Return a string for use in building a javascript Date object for year
    where post was created.
    """
    return "%s" % self.time.strftime('%Y')

  def date_js(self):
    """
    Return a string for use in building javascript Date objects.
    """
    return "%s" % self.date()

class Profile:
  def __init__(self, wall_file, js_data_file, posts=[]):
    self.wall_file = wall_file
    self.js_data_file = js_data_file
    self.posts = posts
    self.results = {'word_count' : 0,
                    'posts_by_date' : defaultdict(int),
                    'posts_by_month' : defaultdict(int),
                    'posts_by_year' : defaultdict(int)}
    self.js_output = defaultdict(str)
    self.word_counter = Counter()
    self.profile_counter = Counter()

  def add_post(self, post):
    self.posts.append(post)


  def read_file(self, path):
    f = open(path, 'r')
    return f.read()

  def analyze_wall(self):
    self.parse_wall(self.read_file(self.wall_file))

  def add_js(self, name, content):
    self.js_output[name] = content

  def get_json(self):
    # Encode in utf-8 to handle names with accents.
    # FIXME: strip single quotes - causing json greif.
    return json.dumps(self.js_output).encode('utf-8').replace("'","")

  def write_data(self):
    f = open(self.js_data_file, 'w')
    # Contstruct a javascript file that can be easily linked to.
    output = "var result_data = jQuery.parseJSON('"
    output += self.get_json()
    output += "')"
    f.write(output)

  def save_results(self):

    # build_data_file
    js_day = self.add_js('posts_data', self.results['posts_by_date'].items())
    js_month = self.add_js('posts_month_data', self.results['posts_by_month'].items())
    js_year = self.add_js('posts_year_data', self.results['posts_by_year'].items())
    js_words = self.add_js('word_pie', [(word[0], word[1]) for word in self.word_counter.most_common(50)])
    js_profiles = self.add_js('top_profile_pie', [(word[0], word[1]) for word in self.profile_counter.most_common(50)])

    # Some swear words found online - seem awfully British :).
    profanity_set = set(( 'arse', 'ass', 'arsehole', 'asshole', 'balls',
      'bastard', 'bitch', 'bloody', 'bollocks', 'bugger', 'christ', 'crap',
      'cunt', 'damn', 'goddamn', 'godamn', 'dickhead', 'fuck', 'fucking',
      'fucker', 'god', 'jesus', 'hell', 'motherfucker', 'piss', 'pissed',
      'prick', 'shag', 'shit', 'slag', 'sucks', 'twat', 'wanker', 'whore'))


    js_words_bad = self.add_js('bad_word_pie', [(word, self.word_counter[word]) for word in profanity_set if self.word_counter[word] > 0])

    self.write_data()

  def add_post_by_date(self, date):
    self.results['posts_by_date'][date] += 1

  def add_post_by_month(self, date):
    self.results['posts_by_month'][date] += 1

  def add_post_by_year(self, date):
    self.results['posts_by_year'][date] += 1

  def parse_wall(self, html):
    """
    Parse and analyze a wall-like piece of html
    """

    # Parse html with BeautifulSoup
    wall_soup = BeautifulSoup(self.read_file(self.wall_file))

    # Find all div.feedentry items
    entries = wall_soup.findAll(name='div', attrs={'class' : 'feedentry' })

    for entry in entries:
      # Parse and find entry information.
      profile = entry.findChild(name='span', attrs={'class' : 'profile'}).text

      # Update profile counter with wall post.
      self.profile_counter.update([profile])

      time_text = entry.findChild(name='span', attrs={'class' : 'time'}).extract().text
      time_object = datetime.strptime(time_text, "%B %d, %Y at %H:%M %p")

      privacy_img = entry.findChild(name='img', attrs={'class' : 'privacy'})
      if privacy_img:
        privacy = privacy_img.extract().attrMap['title']
      else:
        privacy = 'Default privacy'

      #TODO: create comment class
      comment_words = False
      comment_div = entry.findChild(name='div', attrs={'class' : 'comments'})
      if comment_div:
        comment_profiles = comment_div.findAll(name='span', attrs={'class' : 'profile'})
        if comment_profiles:
          self.profile_counter.update([profile.extract().text for profile in comment_profiles])

        comment_text = comment_div.findAll(name='div', attrs={'class' : 'comment' })
        if comment_text:
          for comment in comment_text:
            comment_time = comment.findNext(name='span', attrs={'class' : 'time'}).extract().text
            comment_words = re.findall('\w+', comment.extract().text.lower())
            self.word_counter.update(comment_words)

      text = entry.text

      post = Post(profile=profile, time=time_object, privacy=privacy,
                  comment=comment_words, text=text, count=len(self.posts))

      self.add_post_by_date(post.date_js())
      self.add_post_by_month(post.month_js())
      self.add_post_by_year(post.year_js())

      self.add_post(post)

      # Count occurences of words in posts
      words = re.findall('\w+', text.lower())
      self.word_counter.update(words)
      self.results['word_count'] += len(words)

def main():
  # Facebook's html file with wall posts
  wall_file = os.path.join(sys.path[0], 'html/wall.html')

  # File to store analysis data in.
  js_data_file = os.path.join(sys.path[0], 'analysis/result_data.js')

  profile = Profile(wall_file, js_data_file)
  print("Analyzing your Facebook wall file. This may take a minute...")
  profile.analyze_wall()
  profile.save_results()

if __name__== '__main__':
  main()
