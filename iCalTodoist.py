#!/usr/bin/env python3

# TODO: capture the description as a note
# TODO: look for labels using "@"

import uuid
import calendar
import re
import os
import sys
import configparser
import caldav
import requests

myconfig = configparser.ConfigParser(defaults={
                                   'TODOIST_DUE': '', 'TODOIST_PRIORITY': '', 'TODOIST_LABEL': '', 'TODOIST_PROJECT': ''})
myconfig.read("iCalTodoist.ini")
ICAL_USERNAME = myconfig['icloud']['email']
ICAL_PASSWORD = myconfig['icloud']['password']
ICAL_URL = myconfig['icloud']['url']
ICAL_TIMEZONE = myconfig['icloud']['timezone']
DEFAULT_CALENDAR = myconfig['icloud']['default_list']
TODOIST_API_TOKEN = myconfig['todoist']['api_token']
TODOIST_API_URL = myconfig['todoist']['api_url']
TODOIST_DUE = myconfig['todoist']['due']
TODOIST_PRIORITY = myconfig['todoist']['priority']
TODOIST_LABEL = myconfig['todoist']['label']
TODOIST_PROJECT = myconfig['todoist']['project']


def debug(msg):
    if 'DEBUG' in os.environ:
        print(msg)


def todoist_post(command, data):
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    request_id = str(uuid.uuid4())
    headers = {'Content-Type': 'application/json',
               'X-Request-Id': request_id}
    debug(url)
    debug(headers)
    debug(data)
    ret = requests.post(url, json=data, headers=headers)
    if str(ret.status_code)[0] != '2':
        # WORKAROUND API is currently broken
        if 'WORKAROUND' in os.environ and ret.status_code == 400 and ret.content == b'Invalid argument value\n':
            print('WORKAROUND')
            return {"id": "workaround"}
        raise Exception("Post failed: %s\n%s" % (ret.status_code, ret.content))
    return ret.json()


def todoist_get(command):
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    return requests.get(url).json()


ical_client = caldav.DAVClient(url=ICAL_URL,
                               username=ICAL_USERNAME,
                               password=ICAL_PASSWORD)
urls = None
cal_found = None
for cal in ical_client.principal().calendars():
    debug(cal.name)
    if cal.name == DEFAULT_CALENDAR:
        urls = [x[0] for x in cal.children()]
        cal_found = True
        break
if not cal_found: 
    raise Exception('Default list "%s" not found' % DEFAULT_CALENDAR)
if not urls:
    sys.exit(0)

todoist_labels_json = todoist_get("labels")
todoist_labels = {}
for i in todoist_labels_json:
    todoist_labels[i['name'].lower()] = i['id']
if TODOIST_LABEL.lower() in todoist_labels:
    default_label_id = todoist_labels[TODOIST_LABEL.lower()]
else:
    default_label_id = None

todoist_projects_json = todoist_get("projects")
todoist_projects = {}
for i in todoist_projects_json:
    todoist_projects[i['name'].lower()] = i['id']
if TODOIST_PROJECT.lower() in todoist_projects:
    default_project_id = todoist_projects[TODOIST_PROJECT.lower()]
else:
    default_project_id = None

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
    content = task_data['SUMMARY']
    datekey = "DUE;TZID=%s" % ICAL_TIMEZONE
    if datekey in task_data:
        raw = task_data[datekey]
        due_string = "%s %s %s:%s" % (
            raw[6:8], calendar.month_name[int(raw[4:6])], raw[9:11], raw[11:13])
    else:
        due_string = TODOIST_DUE
    if "PRIORITY" in task_data:
        p = int(task_data["PRIORITY"])
        if p <= 1:
            priority = 4
        elif p <= 5:
            priority = 3
        else:
            priority = 2
    else:
        priority = int(TODOIST_PRIORITY)

    # Search for both labels and projects using "#" because it's easy to add via Siri as "hashtag"
    ical_tags = re.findall('#(\w+)', content)

    project_id = None
    for t in ical_tags:
        if t.lower() in todoist_projects:
            project_id = todoist_projects[t.lower()]
            content = content.replace('#' + t, '')
            break
    if not project_id:
        project_id = default_project_id

    if default_label_id:
        label_ids = [default_label_id]
    else:
        label_ids = []
    for t in ical_tags:
        if t.lower() in todoist_labels:
            label_ids.append(todoist_labels[t.lower()])
            content = content.replace('#' + t, '')

    content = ' '.join(content.split())

    data = {'content': content}
    if project_id:
        data['project_id'] = project_id
    if label_ids:
        data['label_ids'] = label_ids
    if due_string:
        data['due_string'] = due_string
    if priority:
        data['priority'] = priority

    j = todoist_post("tasks", data)
    if "id" in j:
        debug("Successfully submitted: %s" % data)
        debug("Todoist ID: %s" % j["id"])
        ical_client.delete(task_url)
    else:
        print("iCalTodoist.py failed")
        print(data)
        print(resp.json)
