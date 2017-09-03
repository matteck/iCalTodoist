#!/usr/bin/env python3

# TODO: capture the description as a note
# TODO: look for labels using "@"

import caldav
import requests
import configparser
import datetime
import uuid
import calendar
import re
import smtplib

config = configparser.ConfigParser(defaults = {'TODOIST_DUE': '', 'TODOIST_PRIORITY': '', 'TODOIST_LABEL': '', 'TODOIST_PROJECT': ''})
config.read("iCalTodoist.ini")

ICAL_USERNAME = config['icloud']['email']
ICAL_PASSWORD = config['icloud']['password']
ICAL_URL = config['icloud']['url']
ICAL_TIMEZONE = config['icloud']['timezone']
DEFAULT_CALENDAR = config['icloud']['default_list']

SMTP_USERNAME = config['smtp']['username']
SMTP_PASSWORD = config['smtp']['password']
SMTP_SERVER = config['smtp']['server']
OMNI_EMAIL_ADDRESS = config['omni']['email']

ical_client = caldav.DAVClient(url=ICAL_URL,
                          username=ICAL_USERNAME,
                          password=ICAL_PASSWORD)
found = False
for cal in ical_client.principal().calendars():
    if cal.name == DEFAULT_CALENDAR:
        urls = [x[0] for x in cal.children()]
        found = True
        break
if not found:
    print('Default list "%s" not found')
    sys.exit(1)

for task_url in urls:
    task = requests.get(task_url, auth=(ICAL_USERNAME, ICAL_PASSWORD))
    lines = [x.strip() for x in task.text.strip().split('\n')]
    vals = [x.split(':', 1) for x in lines]
    task_data = {key: value for (key, value) in vals}
    
    # Don't import completed
    if ('STATUS' in task_data and task_data['STATUS'] == 'COMPLETED'):
        ical_client.delete(task_url)
        continue

    # Can't continue without a summary, should never happen so throw an exception
    subject = task_data['SUMMARY']

    if 'DESCRIPTION' in task_data and task_data['DESCRIPTION'] != "Reminder":
        body = task_data['DESCRIPTION']
    else:
        body = ''

    msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (SMTP_USERNAME,
                                                            OMNI_EMAIL_ADDRESS,
                                                            subject,
                                                            body)
    server = smtplib.SMTP_SSL(SMTP_SERVER)
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(SMTP_USERNAME, OMNI_EMAIL_ADDRESS, msg)

    # Sendmail() raises an exception if it fails
    ical_client.delete(task_url)

    
