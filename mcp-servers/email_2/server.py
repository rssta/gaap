# https://github.com/HeurisTech/gmail-mcp-server/blob/main/server.py

import os
from base64 import urlsafe_b64encode
from email.message import EmailMessage  # <-- Safe MIME construction
from typing import Any, Optional, Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

import sys
with open("arriving_path_file.txt", "r") as file:
    arriving_path = file.read()
sys.path.insert(1, arriving_path + 'agent_helpers')

import database

mcp = FastMCP(
    "gmail-mcp-server"
)

class GoogleClient:
    """Encapsulates a Gmail API client."""
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        # It's recommended to build this dynamically or handle thread safety if reused globally
        self.gmail = build("gmail", "v1", credentials=self._creds, cache_discovery=False)

def get_google_client(env_override: Optional[Dict[str, str]] = None) -> GoogleClient:
    source = env_override if env_override is not None else os.environ
    client_id = source.get("CLIENT_ID")
    client_secret = source.get("CLIENT_SECRET")
    refresh_token = source.get("REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        raise RuntimeError("Required Google OAuth credentials not found in environment")
    return GoogleClient(client_id, client_secret, refresh_token)

@mcp.tool(name="sign_in", description="Sign in to email server")
async def sign_in(
    client_id: str,
    client_secret: str, 
    refresh_token: str
) -> bool: 

    try:
        database.insert_internal_data("client_id", "email_real", client_id)
        database.insert_internal_data("client_secret", "email_real", client_secret)
        database.insert_internal_data("refresh_token", "email_real", refresh_token)
    except Exception as e:
        return False
    
    return True

@mcp.tool(name="send_mail", description="Send a new email to recipient(s) with a subject and body")
async def send_mail(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    #env_override: Optional[Dict[str, str]] = None,
) -> dict[str, Any]:
    try:
        # --- SECURE HACK PREVENTIONS USING EmailMessage ---
        msg = EmailMessage()
        msg.set_content(body)
        
        # EmailMessage protects against \r\n injection in headers
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        # Base64url encode the safe message byte string
        raw = urlsafe_b64encode(msg.as_bytes()).decode("ascii")

        # Get google client safely
        env_override = {"CLIENT_ID": database.access_internal_data("client_id", "email_real"), "CLIENT_SECRET": database.access_internal_data("client_secret", "email_real"), "REFRESH_TOKEN": database.access_internal_data("refresh_token", "email_real")}
        google_client = get_google_client(env_override)
        # Send via Gmail API
        sent = (
            google_client.gmail
            .users()
            .messages()
            .send(
                userId="me",
                body={"raw": raw},
            )
            .execute()
        )

        return {
            "content": [
                {"type": "text", "text": f"Email sent successfully. Message ID: {sent['id']}"}
            ]
        }
    except Exception as e:
        # Production Note: Don't return raw exception strings to users if they contain secrets.
        # This generic message is okay as long as 'e' doesn't leak credentials.
        return {
            "content": [
                {"type": "text", "text": f"Error sending email: {str(e)}"}
            ],
            "isError": True,
        }

if __name__ == "__main__":
    mcp.run(transport=os.getenv("TRANSPORT", "stdio"))
