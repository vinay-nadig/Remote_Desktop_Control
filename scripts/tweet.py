import os
import argparse
import sqlite3
import sys
import tweepy
import traceback

sys.path.append("~/project")

_CMD_NAME = "Twt"
_CMD_LONG_NAME = "Tweet"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise

class Tweet(object):
    def __init__(self, options, sm, number, signature):
        self.flag=1
        self.privilaged =False        # Does this service need special privilages?
        self.parser = ArgumentParser()
        self.msg = ""                                   # The final msg that is sent
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.parser.add_argument("email_id",help="specify the email id",action="store")
        self.parser.add_argument("tweet_text",help="specify the tweet within double quotes",action="store")
        try:
            self.arguments = self.parser.parse_args(self.options)
            self.eid=(self.arguments.email_id,)
        except:
            self.msg="usage:tweet email_id tweet_text"
            self.flag=0
            return

    def postTweet(self):
        if len(self.arguments.tweet_text)>140:
            self.msg= "Tweet exceeded character limit. Try again"
            return
        if ('@' not in self.arguments.email_id) or ('.' not in self.arguments.email_id):
            self.msg="Email id entered is invalid. Try again"
            return
        con=sqlite3.connect("/home/sagarubuntu/project1/database/tweetdb.db")
        with con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            try:
                cur.execute('SELECT * FROM AccessTokens WHERE email_id=?', self.eid)
            except Exception,e:
                print str(e)
                self.msg=" Datababse access error"
                return
            row = cur.fetchone()
            if row == None:
                self.msg = "The email id is not yet registered!"
                return
            else:
                CONSUMER_KEY = row["consumer_key"]
                CONSUMER_SECRET = row["consumer_secret"]
                ACCESS_KEY = row["access_key"]
                ACCESS_SECRET = row["access_secret"]
            #    print "EMAIL_ID: {0}\nCONSUMER_KEY: {1}\nCONSUMER_SECRET: {2}\nACCESS_KEY: {3}\nACCESS_SECRET: {4}".format(self.eid,CONSUMER_KEY,CONSUMER_SECRET,ACCESS_KEY,ACCESS_SECRET)
                auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
                auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
                api = tweepy.API(auth)
                try:
                    api.update_status(self.arguments.tweet_text)
                    self.msg="Tweet sent"
                except Exception,e:
                    try:
                        self.msg= e[0][0]['message']
                    except:
                        self.msg="Internet connection error"


    def send_sms(self):
        if self.flag==1:
            self.postTweet()
            msg = {
                'Text' : self.msg,
                'SMSC' : {'Location' : 1},
                'Number' : self.to_no,
                }
        print self.msg
        self.sm.SendSMS(msg)
    

                    
#a=Tweet(['rockybal.68@gmail.com','sgasdg'],"123","123","123")
#a.send_sms()

        


