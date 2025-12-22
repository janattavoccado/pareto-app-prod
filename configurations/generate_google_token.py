#!/usr/bin/env python3
"""
Generate Google OAuth2 tokens for users.
Run this script to authorize each user and generate their token file.

Usage:
    python generate_google_token.py
"""

import os
import json
import sys
from pathlib import Path

# Check for required Google libraries at startup
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_LIBS_AVAILABLE = True
except ImportError as e:
    GOOGLE_LIBS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Scopes required for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

def check_google_libs():
    """Check if Google libraries are installed."""
    if not GOOGLE_LIBS_AVAILABLE:
        print("\n" + "="*60)
        print("ERROR: Google libraries not installed!")
        print("="*60)
        print(f"\nImport Error: {IMPORT_ERROR}")
        print("\nTo install Google libraries, run:")
        print("  pip install google-auth-oauthlib google-api-python-client")
        print("\nOr install all requirements:")
        print("  pip install -r requirements.txt")
        print("\n" + "="*60)
        return False
    return True

def generate_token_for_user(user_email: str, client_secrets_file: str = 'client_secrets.json'):
    """
    Generate and save OAuth2 token for a user.

    Args:
        user_email (str): User's email address
        client_secrets_file (str): Path to client_secrets.json

    Returns:
        bool: True if successful, False otherwise
    """

    if not GOOGLE_LIBS_AVAILABLE:
        print(f"\nError: Google libraries not available")
        return False

    if not os.path.exists(client_secrets_file):
        print(f"\nError: {client_secrets_file} not found!")
        print("\nTo get client_secrets.json:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Go to APIs & Services → Credentials")
        print("3. Find your OAuth 2.0 Client ID (Desktop application)")
        print("4. Click the download button (⬇️)")
        print("5. Save the downloaded file as 'client_secrets.json' in this directory")
        return False

    try:
        # Create credentials directory if it doesn't exist
        os.makedirs('credentials', exist_ok=True)

        # Generate token filename
        token_filename = f'credentials/{user_email.replace("@", "_at_").replace(".", "_")}_token.json'

        # Create OAuth2 flow
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file,
            SCOPES
        )

        # Run local server for authorization
        print(f"\n{'='*60}")
        print(f"Authorizing: {user_email}")
        print(f"{'='*60}")
        print("\nA browser window will open for authorization...")
        print("After you authorize, you'll be redirected to localhost.")
        print("The token will be saved automatically.\n")

        creds = flow.run_local_server(port=8080)

        # Save credentials to file
        with open(token_filename, 'w') as token_file:
            token_file.write(creds.to_json())

        print(f"\n{'='*60}")
        print(f"✓ Success!")
        print(f"{'='*60}")
        print(f"Token saved to: {token_filename}")
        print(f"User {user_email} is now authorized!")
        print(f"\nUpdate users.json with:")
        print(f'  "google_credentials": {{')
        print(f'    "credentials_file": "{token_filename}"')
        print(f'  }}\n')

        return True

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure client_secrets.json is in the correct location")
        print("2. Check that you have internet connection")
        print("3. Verify the email address is correct")
        print("4. Check that Gmail API and Calendar API are enabled in Google Cloud Console")
        return False

def main():
    """Main function to generate tokens for multiple users."""

    print("\n" + "="*60)
    print("Google OAuth2 Token Generator for Pareto Chatwoot")
    print("="*60)

    # Check if Google libraries are installed
    if not check_google_libs():
        sys.exit(1)

    # Check if client_secrets.json exists
    if not os.path.exists('client_secrets.json'):
        print("\nError: client_secrets.json not found in current directory!")
        print("\nTo get client_secrets.json:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a new project or select existing one")
        print("3. Enable Gmail API and Google Calendar API")
        print("4. Go to APIs & Services → Credentials")
        print("5. Create OAuth 2.0 Client ID (Desktop application)")
        print("6. Click the download button (⬇️)")
        print("7. Save the downloaded file as 'client_secrets.json' in this directory")
        print("\nFor detailed instructions, see GOOGLE_SETUP_GUIDE.md")
        sys.exit(1)

    print("\nThis tool will help you authorize users for Gmail and Calendar access.")
    print("Each user will need to log in with their Google account.\n")

    # Try to load users from users.json
    users_to_authorize = []
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r') as f:
                users_data = json.load(f)

            print("Found users in users.json:")
            for user in users_data.get('users', []):
                email = user.get('email')
                if email:
                    print(f"  - {user.get('first_name')} {user.get('last_name')} ({email})")
                    users_to_authorize.append(email)

            if users_to_authorize:
                print("\nWould you like to authorize these users? (y/n): ", end='')
                choice = input().strip().lower()
                if choice != 'y':
                    users_to_authorize = []
        except Exception as e:
            print(f"Could not read users.json: {str(e)}\n")

    # If no users from file, ask for manual entry
    if not users_to_authorize:
        print("\nEnter email addresses to authorize (one per line)")
        print("Type 'done' when finished:\n")

        while True:
            email = input("Email: ").strip()

            if email.lower() == 'done':
                break

            if '@' not in email:
                print("Invalid email format. Please try again.")
                continue

            users_to_authorize.append(email)

    # Generate tokens for each user
    if users_to_authorize:
        print(f"\n{'='*60}")
        print(f"Authorizing {len(users_to_authorize)} user(s)...")
        print(f"{'='*60}")

        successful = 0
        failed = 0

        for email in users_to_authorize:
            if generate_token_for_user(email):
                successful += 1
            else:
                failed += 1

        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"\nNext steps:")
        print("1. Update users.json with the credentials_file paths")
        print("2. Restart your Flask app")
        print("3. Test by sending a message to your Chatwoot inbox")
        print(f"\nFor help, see: GOOGLE_SETUP_GUIDE.md")
    else:
        print("\nNo users to authorize.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
