from __future__ import print_function

from datetime import datetime, timedelta
import os.path
import json
import asyncio
import websockets

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


class Tabs2Calendar():
    def __init__(self, googleCalendar):
        self.creds = None # credential authorization
        self.service = None # object that manipulates google calendar API
        self.CALENDAR_ID = None # ID url of google calendar
        self.urlHistory = {} # a dict that records all urls traveled to
        self.currentUrl = None # current url we're on
        self.startTime = None # start time for google calendar event

        # get google calendar id/url
        if googleCalendar.lower().endswith('.json'):
            try:
                file = open(googleCalendar)
                tempJson = json.load(file)
                self.CALENDAR_ID = tempJson["CALENDAR_ID"]
            except KeyError:
                print("File does not contain valid key.")
                print("Please provide json file with key 'CALENDAR_ID'")
            finally:
                file.close()
        else:
            print("Incorrect file type.")
            print("Please provide json file with key 'CALENDAR_ID'")

        # token.json file stores the user's access and refresh tokens
        # created automatically when the authorization flow completes for the first time
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # if there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        try:
            self.service = build('calendar', 'v3', credentials=self.creds)
            print("Service Built")
        except HttpError as error:
            self.service = None
            print('An error occurred: %s' % error)

    def logCurrentUrl(self, message):
        self.currentUrl = message["url"]

    def logStartTime(self, startTime):
        self.startTime = startTime

    def convertDate(self, recordedTime):
        newDate = datetime.strptime(recordedTime, "%m/%d/%Y, %H:%M:%S %p")
        if "PM" in recordedTime:
            if newDate.hour != 12:
                newDate += timedelta(hours=12)
        else:
            if newDate.hour == 12:
                newDate = newDate.replace(hour=0)
        return newDate


    def createEvent(self, endTime):
        timeDifference = endTime - self.startTime
        print(timeDifference)
        if timeDifference >= timedelta(minutes=5):
            # confirms google api is connected
            if self.service:
                event = {
                    'summary': self.currentUrl,  # 'Replace with websiteName',
                    # 'description': 'Can maybe put specific website url',
                    'start': {
                        'dateTime': self.startTime.strftime("%Y-%m-%dT%H:%M:%S"),  # '2023-08-09T09:00:00',
                        'timeZone': 'America/Los_Angeles',
                    },
                    'end': {
                        'dateTime': endTime.strftime("%Y-%m-%dT%H:%M:%S"),
                        'timeZone': 'America/Los_Angeles',
                    },
                }
                self.service.events().insert(calendarId=self.CALENDAR_ID, body=event).execute()
                print(f"{self.currentUrl} ended at {endTime}")
                print("Event Added!")

            else:
                print("Authentication Error")


    def recordUrlHistory(self, endTime):
        timeDifference = endTime - self.startTime
        if self.currentUrl not in self.urlHistory:
            self.urlHistory[self.currentUrl] = timeDifference
        else:
            self.urlHistory[self.currentUrl] += timeDifference
        # print(f"Total time for {self.currentUrl}: {self.urlHistory[self.currentUrl]}")


async def messageHandler(websocket):
    while True:
        try:
            message = await websocket.recv()
            msgParse = json.loads(message)
            recordedTime = tabs.convertDate(msgParse["recordedTime"])

            if msgParse["timeType"] == "end":
                tabs.createEvent(recordedTime)
                tabs.recordUrlHistory(recordedTime)

            tabs.logCurrentUrl(msgParse)
            tabs.logStartTime(recordedTime)
            print(f"Current Url: {msgParse['url']} at {recordedTime}")
        except websockets.ConnectionClosedOK:
            break


async def webServer():
    async with websockets.serve(messageHandler, "localhost", 3000):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    tabs = Tabs2Calendar("googleCalendar.json")
    try:
        asyncio.run(webServer())
    except KeyboardInterrupt as error:
        print("Program Ended")