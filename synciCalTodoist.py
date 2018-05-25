#!/usr/bin/env python3

# Synchronise some Todoist and Reminders tasks
# Create and complete tasks in either
# Show tasks with a date in Reminders
# Editing is not possible in Reminders

# Fetch ical_tasks in inbox
# Fetch todoist_tasks in inbox or with due date
# Fetch sqlite_tasks

# For tasks in ical_tasks
    # if in sqlite_tasks
        # pass
    # else
        # create new todoist task
# For tasks in todoist_tasks
    # if in sqlite_tasks
        # compare to linked ical_tasks
        # if identical
            # pass
        # if different
            # delete ical tasks
            # create new ical task
            # update database
    # if not in sqlite_tasks
        # create new ical task

import calendar
import os
import sys
import configparser
import caldav
import requests
import sqlite3
import uuid

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

conn = sqlite3.connect('synciCalTodoist.sqlite3')
c = conn.cursor()

def todoist_post(command, data):
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    request_id = str(uuid.uuid4())
    headers = {'Content-Type': 'application/json',
               'X-Request-Id': request_id}
    ret = requests.post(url, json=data, headers=headers)
    return ret.json()


def todoist_get(command, params):
    
    url = "%s/%s?token=%s" % (TODOIST_API_URL, command, TODOIST_API_TOKEN)
    return requests.get(url, params=params).json()

# test
# data = {'content': "content"}
# j = todoist_post("tasks", data)
# print(j)
# sys.exit()

# Get all Todoist tasks in inbox or with a due date/time

params = { 'filter': '30 days | #inbox'}
todoist_tasks = todoist_get('tasks', params)

# Get all iCal tasks in default list

ical_client = caldav.DAVClient(url=ICAL_URL,
                               username=ICAL_USERNAME,
                               password=ICAL_PASSWORD)
print(ical_client.server_params)
urls = None
cal_found = None
for cal in ical_client.principal().calendars():
    if cal.name == DEFAULT_CALENDAR:
        # print(cal.todos())
        task_urls = [x[0] for x in cal.children()]
        cal_found = True
        break
if not cal_found: 
    raise Exception('Default list "%s" not found' % DEFAULT_CALENDAR)

ical_tasks = []
for task_url in task_urls:
    task = requests.get(task_url, auth=(ICAL_USERNAME, ICAL_PASSWORD))
    # Make it easier to inspect
    lines = [x.strip() for x in task.text.strip().split('\n')]
    vals = [x.split(':', 1) for x in lines]
    task_data = {key: value for (key, value) in vals}
    ical_tasks.append(task_data)


for i in ical_tasks:
    t = (i['UID'],)
    c.execute('SELECT * FROM linked_tasks WHERE ical_id=?', t)
    if c.fetchone() == None:
        # Ignore completed
        if i['STATUS'] == 'COMPLETED':
            continue
        # New task, create matching task in Todoist
        content = i['SUMMARY']
        content = ' '.join(content.split())
        data = {
            'content': content
        } 
        if 'TRIGGER;VALUE=DATE-TIME' in i:
            d = i['TRIGGER;VALUE=DATE-TIME']
            d = "%s-%s-%sT%s:%s:%sZ" % (d[0:4], d[4:6], d[6:8], d[9:11], d[11:13], d[13:15])
            data['due_datetime'] = d
        if 'PRIORITY' in i:
            ical_priority = i['PRIORITY']
            priority = 1
            if ical_priority == "9":
                priority = 2
            elif ical_priority == "5":
                priority = 3
            elif ical_priority == "1":
                priority = 4
            data['priority'] = priority
        new_todoist_task = todoist_post("tasks", data)
        t = (new_todoist_task['id'], i['UID'])
        c.execute('INSERT INTO linked_tasks (todoist_id, ical_id) VALUES (?,?)', t)
        conn.commit()

for t in todoist_tasks:
    t = (t['id'],)
    c.execute('SELECT * FROM linked_tasks WHERE todoist_id=?', t)
    if c.fetchone() == None:
        pass
        # Create task in iCal







# todoist_projects_json = todoist_get("projects")
# todoist_projects = {}
# for i in todoist_projects_json:
# if TODOIST_PROJECT.lower() in todoist_projects:
#     default_project_id = todoist_projects[TODOIST_PROJECT.lower()]
# else:
#     default_project_id = None



