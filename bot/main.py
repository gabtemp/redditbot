#
# Finds reddit comments with a particular tag and replies with the desired message
#
# Based on the 'Massdrop-Reddit-Bot' from DarkMio: https://github.com/DarkMio/Massdrop-Reddit-Bot
#
import configparser
import logging
import threading
from time import sleep, time
import sqlite3

import praw
import praw.helpers

from bot.message_builder import MessageBuilder


__author__ = 'gabriel.carneiro'


class MessageFinder:
    def __init__(self):

        config = configparser.ConfigParser()
        config.read('redditbot.ini')

        self.bot_username = config.get('Authentication', 'bot.username')
        self.bot_password = config.get('Authentication', 'bot.password')
        self.monitored_subteddit = config.get('Configuration', 'bot.monitored.subreddit')
        self.keyword = config.get('Configuration', 'bot.summon.keyword')
        self.delete_comment_command = config.get('Configuration', 'bot.delete.comment.command')

        self.message_builder = MessageBuilder()
        self.r = self.login()
        self.running = True

    def login(self):
        r_praw = praw.Reddit('windows:carneiro.gabriel.proposter:v0.1 (by /u/Gabrieltc')
        r_praw.login(username=self.bot_username, password=self.bot_password)
        return r_praw

    def monitor_comments(self):
        log.info("Starting comment browser on subreddit /r/%s." % self.monitored_subteddit)
        while True:
            try:
                comment_stream = praw.helpers.comment_stream(self.r, self.monitored_subteddit, limit=None, verbosity=0)
                while self.running:
                    comment = next(comment_stream)  # Retrieve the next comment
                    if ((self.keyword in comment.body
                         and not check_comment(comment.id)
                         and not str(comment.author) == self.bot_username)):
                        message = self.create_message(comment.author, self.bot_username)
                        self.post_message(comment, message)
                        save_replied_comment(comment)
            except Exception as e:
                log.info("Comment stream broke. Retrying in 60s.")
                log.info(repr(e))
                sleep(60)
                pass

    def monitor_inbox(self):
        log.info("Starting inbox message browser on %s." % self.bot_username)
        while True:
            try:
                while self.running:
                    for comment in self.r.get_unread():
                        if comment.body.startswith(self.delete_comment_command):
                            self.check_and_delete_comment(comment)
                        comment.mark_as_read()
                    sleep(5)
            except Exception as e:
                log.info("Inbox stream broke. Retrying in 60s.")
                log.info(repr(e))
                sleep(60)
                pass

    def post_message(self, comment, message):
        log.info('Replying to comment %s.' % comment.id)
        reply = comment.reply(message)
        if not reply:
            log.error('Failed to reply comment %s.' % comment.id)
        else:
            edit = self.r.get_info(thing_id=str(reply.id)).edit(reply.body.replace('____id____', str(reply.id)))
            if not edit:
                log.warn('Failed to update the comment ID on comment %s.' % str(reply.id))

    def create_message(self, user_to, bot_from):
        if self.message_builder:
            return self.message_builder.build_message(user_to, bot_from)
        else:
            log.fatal('Message builder object is Null!')

    def check_and_delete_comment(self, comment):
        if comment.was_comment:
            comment_id = comment.parent_id
        else:
            comment_id = 't1_' + comment.body[len(self.delete_comment_command) + 1:]
        target = self.r.get_info(thing_id=comment_id)  # Comment to be deleted
        parent = self.r.get_info(thing_id=target.parent_id)  # Original (parent) comment replied to
        if target.author.name == self.bot_username and comment.author.name == parent.author.name:
            target.delete()
            log.info('Comment %s was deleted.' % target.id)


def check_comment(comment_id):
    # Uncomment after SQL support
    check = cur.execute(u'SELECT id FROM replied_comments WHERE id = "{0:s}" LIMIT 1'.format(comment_id))
    for line in check:
        sleep(2)
        if line:
            log.debug('Comment %s already replied.' % comment_id)
            return True
    return False


def save_replied_comment(comment):
    log.info('Adding comment %s to history.' % comment.id)
    cur.execute(u'INSERT INTO replied_comments (id, created_time, reply_time)'
                u' VALUES ("{0:s}", "{1:d}", "{2:d}")'.format(comment.id, int(comment.created), int(time())))


def create_db():
    log.info('Creating required tables if not exists...')
    cur.execute('CREATE TABLE IF NOT EXISTS replied_comments'
                '(id TEXT PRIMARY KEY ASC, created_time INTEGER, reply_time INTEGER);')


def start():
    t1_finder = MessageFinder()
    t2_finder = MessageFinder()

    t1 = threading.Thread(target=t1_finder.monitor_comments)
    t2 = threading.Thread(target=t2_finder.monitor_inbox)

    t1.daemon = True
    t2.daemon = True

    t1.start()
    t2.start()

    threads.append(t1)
    threads.append(t2)


def join_threads(threads):
    """
    Join threads in interruptable fashion.
    From http://stackoverflow.com/a/9790882/145400
    """
    for t in threads:
        while t.isAlive():
            t.join(5)


if __name__ == "__main__":
    # SET UP LOGGER
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%X', level=logging.INFO)
    log = logging.getLogger(__name__)

    # SET UP DATABASE
    db = sqlite3.connect('redditbot.db', check_same_thread=False, isolation_level=None)
    cur = db.cursor()
    create_db()

    threads = []
    start()
    try:
        join_threads(threads)
    except KeyboardInterrupt:
        log.info("Stopping process entirely.")