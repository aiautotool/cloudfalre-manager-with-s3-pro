import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleSearchConsole:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = [
            'https://www.googleapis.com/auth/siteverification',
            'https://www.googleapis.com/auth/webmasters'
        ]
        self.service_site_verification = None
        self.service_webmasters = None
        self.is_authenticated = False

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Credentials file {self.credentials_file} not found.")
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.service_site_verification = build('siteVerification', 'v1', credentials=creds)
        self.service_webmasters = build('searchconsole', 'v1', credentials=creds) 
        
        self.is_authenticated = True
        return True

    def get_verification_token(self, site_url, method='DNS'):
        """
        Get the verification token content for a site.
        method: "DNS" or "FILE" (HTML file upload).
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")

        body = {
            "verificationMethod": method.upper()
        }
        if method.upper() == 'DNS':
             body["site"] = {"identifier": site_url, "type": "INET_DOMAIN"}
        else:
             # For FILE, identifier is the full URL e.g. http://example.com/
             body["site"] = {"identifier": site_url, "type": "SITE"}

        # webResource.getToken
        result = self.service_site_verification.webResource().getToken(body=body).execute()
        return result.get('token')

    def verify_site(self, site_url, method='DNS'):
        """
        Verify the site after placing the token.
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")

        body = {
            "verificationMethod": method.upper()
        }
        if method.upper() == 'DNS':
             body["site"] = {"identifier": site_url, "type": "INET_DOMAIN"}
        else:
             body["site"] = {"identifier": site_url, "type": "SITE"}
             
        # webResource.insert
        result = self.service_site_verification.webResource().insert(verificationMethod=method.upper(), body=body).execute()
        return result

    def add_site_to_search_console(self, site_url):
        """
        Add site to Search Console (if not already added by verification).
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")
            
        # sites.add
        self.service_webmasters.sites().add(siteUrl=site_url).execute()

    def submit_sitemap(self, site_url, feed_path):
        """
        Submit a sitemap for a site.
        site_url: URL of the property (e.g. https://example.com/)
        feed_path: Path to sitemap relative to site_url (e.g. "sitemap.xml" or "sitemap.html")
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")
        
        full_sitemap_url = feed_path
        if not feed_path.startswith("http"):
            # Construct full URL if relative path given
             full_sitemap_url = site_url.rstrip('/') + '/' + feed_path.lstrip('/')
             
        self.service_webmasters.sitemaps().submit(siteUrl=site_url, feedpath=full_sitemap_url).execute()

    def list_sites(self):
        """
        List all sites in the Search Console account.
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")
            
        # sites.list
        result = self.service_webmasters.sites().list().execute()
        return result.get('siteEntry', [])

    def delete_site(self, site_url):
        """
        Remove a site from the Search Console account.
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")
            
        # sites.delete
        self.service_webmasters.sites().delete(siteUrl=site_url).execute()

    def get_site_analytics(self, site_url, start_date, end_date):
        """
        Get search analytics data (clicks, impressions, CTR, position) for a site.
        """
        if not self.is_authenticated:
            raise Exception("Not authenticated")

        body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['date'],  # Group by date to get total aggregation implicitly or just query totals
            'rowLimit': 1  # We only really need the totals, but the API doesn't give totals directly without query
            # Actually, to get site-wide totals, we can request no dimensions but usually aggregationType defaults to auto.
            # Let's request no dimensions to get a single row of totals if possible, or just sum up locally if needed.
        }
        # Better approach for totals: don't specify dimensions, just get the totals for the date range.
        body = {
            'startDate': start_date,
            'endDate': end_date
        }

        try:
            result = self.service_webmasters.searchanalytics().query(siteUrl=site_url, body=body).execute()
            rows = result.get('rows', [])
            
            # If no rows, return 0s
            if not rows:
                return {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0}
            
            # If we didn't specify dimensions, it returns one row with the aggregates
            # (Wait, if no dimensions are specified, it aggregates over the entire period)
            row = rows[0]
            return {
                'clicks': row.get('clicks', 0),
                'impressions': row.get('impressions', 0),
                'ctr': round(row.get('ctr', 0) * 100, 2), # Convert to percentage
                'position': round(row.get('position', 0), 1)
            }
        except Exception as e:
            print(f"Error fetching analytics for {site_url}: {e}")
            return {'clicks': '-', 'impressions': '-', 'ctr': '-', 'position': '-'}
