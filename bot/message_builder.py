__author__ = 'gabte_000'


class MessageBuilder:
    def __init__(self):
        self.template = '''{header:s}\n\n---\n\n{body:s}\n\n\n---\n\n{footer:s}'''
        self.header = ''
        self.footer = '^(/u/{user:s} can reply with \'+delete\' or) [^message ^me]({link:s}) ^(to delete this comment.)'
        self.footer_link = 'https://www.reddit.com/message/compose?' \
                           'to={botname:s}&subject=Delete+Comment+{botname:s}&message=%2Bdelete+{comment_id:s}'

    def build_message(self, user_to, bot_from):
        link = self.footer_link.format(botname=bot_from, comment_id='____id____')
        footer = self.footer.format(user=str(user_to), link=link)
        message = self.template.format(header='header', body='body', footer=footer)
        return message
