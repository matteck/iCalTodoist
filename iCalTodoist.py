#!/usr/bin/env python3

# TODO: capture the description as a note
# TODO: look for labels using "@"

import caldav
import requests
import configparser
import datetime
import sys
import uuid
import json
import calendar
import re

config = configparser.ConfigParser()
config.read("iCalTodoist.ini")
ICAL_USERNAME = config['icloud']['email']
ICAL_PASSWORD = config['icloud']['password']
ICAL_URL = config['icloud']['url']
ICAL_TIMEZONE = config['icloud']['timezone']
DEFAULT_CALENDAR = config['icloud']['default_list']
TODOIST_API_TOKEN = config['todoist']['api_token']
TODOIST_API_URL = config['todoist']['api_url']
TODOIST_DUE = config['todoist']['due']
TODOIST_PRIORITY = config['todoist']['priority']
TODOIST_LABEL = config['todoist']['label']

labels = {}

def mytodoist(command, method):
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    return requests.get(url).json()

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
        client.delete(task_url)
        continue
    # Can't continue without a summary, should never happen so throw an exception
    content = task_data['SUMMARY']
    datekey = "DUE;TZID=%s" % ICAL_TIMEZONE
    if datekey in task_data:
        raw = task_data[datekey]
        datestring = "%s %s %s:%s" % (raw[6:8], calendar.month_name[int(raw[4:6])], raw[9:11], raw[11:13])
    else:
        datestring = TODOIST_DUE
    if "PRIORITY" in task_data:
        p = int(task_data["PRIORITY"])
        if p <= 1:
            priority = "4"
        elif p <= 5:
            priority = "3"
        else:
            priority = "2"
    else:
        priority = TODOIST_PRIORITY
    
    # Search for labels using "#" because it's easy to add via Siri as "hashtag"
    m = re.search('#(\w+)', content)
    if m:
        label = m.group(1)
    elif TODOIST_LABEL:
        label = TODOIST_LABEL
    
    if label in labels:
        label_id = labels[label]
    else:
        label_id = ""
        if TODOIST_LABEL:
            for i in mytodoist("labels", "GET"):
                if i['name'].lower() == label.lower():
                    label_id = i['id']
                    break
            # If no matching labels, try a project instead
            if not label_id:
                for i in mytodoist("projects", "GET"):
                    if i['name'].lower() == label.lower():
                        label_id = i['id']
                        break
    labels[label] = label_id
    print (label_id, datestring, priority, content)