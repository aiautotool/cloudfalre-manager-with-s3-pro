import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleSheetManager:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/siteverification',
            'https://www.googleapis.com/auth/webmasters'
        ]
        self.service = None
        self.is_authenticated = False

    def authenticate(self):
        creds = None
        # Try to load existing token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception:
                creds = None

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if not os.path.exists(self.credentials_file):
                print(f"Credentials file {self.credentials_file} not found.")
                # We can't auth without credentials
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
                
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"Authentication failed: {e}")
                return False

        try:
             self.service = build('sheets', 'v4', credentials=creds)
             self.is_authenticated = True
             return True
        except Exception as e:
             print(f"Failed to build service: {e}")
             return False

    def add_sheet(self, spreadsheet_id, title):
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        requests = [{
            'addSheet': {
                'properties': {
                    'title': title
                }
            }
        }]
        
        body = {
            'requests': requests
        }
        
        result = self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        return result

    def get_sheet_names(self, spreadsheet_id):
        """
        Returns a list of dictionaries with 'title' and 'id' for each sheet in the spreadsheet.
        """
        if not self.is_authenticated:
             raise Exception("Not authenticated")
        
        result = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = result.get('sheets', [])
        return [{'title': s['properties']['title'], 'id': s['properties']['sheetId']} for s in sheets]

    def get_sheet_values(self, spreadsheet_id, range_name):
        """
        Returns a list of lists containing the values in the specified range.
        range_name example: 'Sheet1!A1:E10' or just 'Sheet1'
        """
        if not self.is_authenticated:
             raise Exception("Not authenticated")
        
        result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        return result.get('values', [])

    def update_sheet_values(self, spreadsheet_id, range_name, values):
        """
        Updates values in a range.
        values: list of lists
        """
        if not self.is_authenticated:
             raise Exception("Not authenticated")
        
        body = {
            'values': values
        }
        
        result = self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='RAW', body=body).execute()
        return result
