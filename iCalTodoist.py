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

config = configparser.ConfigParser(defaults = {'TODOIST_DUE': '', 'TODOIST_PRIORITY': '', 'TODOIST_LABEL': '', 'TODOIST_PROJECT': ''})
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
TODOIST_PROJECT = config['todoist']['project']

def todoist_post(command, data):
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    request_id = str(uuid.uuid4())
    headers = {'Content-Type': 'application/json',
                'X-Request-Id': request_id}
    return requests.post(url, json=data, headers=headers)

def todoist_get(command):
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

if urls:
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
        due_string = "%s %s %s:%s" % (raw[6:8], calendar.month_name[int(raw[4:6])], raw[9:11], raw[11:13])
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
    
    resp = todoist_post("tasks",data)
    j = resp.json()
    if resp.status_code == 200 and "id" in j:
        print("Successfully submitted:", data)
        print("Todoist ID:", j["id"])    
        ical_client.delete(task_url)
    else:
        print("Failed")
        print(data)
        print(resp.json)
    
