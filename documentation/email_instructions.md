
## Email Instructions

### Email (`email` server)

Server to send mock emails. With this server, you can sign in with the credentials `password == "password"` and `email == "alice@example.com"`. The agent must sign in before it can send an email. Results of sent emails can be accessed through the command of `/check_queries` and then checking recent requests, in the agent. 

### Email Real (`email_real` server)

Server to send emails through Gmail. This requires a Gmail account, and a valid `client_id`, `client_secret`, and `refresh_token`. This can be achieved through the following steps:

1. Create a new Google Cloud project at the [Google Cloud console](https://console.cloud.google.com). 

2. In this project, enable the [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com). 

3. In the [APIs & Services](https://console.cloud.google.com/apis/api/gmail.googleapis.com) page, visit `OAuth Consent Screen` on the left. Go to `Audience`, and set `User Type` to `external`.

4. In the [APIs & Services](https://console.cloud.google.com/apis/api/gmail.googleapis.com) page, visit `Credentials` on the left. Create a new credential for an OAuth Client ID. Select a `Web application`. As an `Authorized redirect URI`, add the URL to the Google OAuth Playground, `https://developers.google.com/oauthplayground`. Save the client ID and secret created. 

5. At the [OAuth Playground](https://developers.google.com/oauthplayground/), go to the gear at the right, and click the checkbox to `Use your own OAuth credentials`. Add the ID and secret obtained in step 3. 

6. On the left of the screen, under `Step 1`, scroll down and select under `Gmail APIv1` the `gmail.send` scope. Then, go to `Step 2` and `Exchange authorization code` for tokens. You should see a refresh token. Save this value. 

Now, you should have all you need to send emails with `email_real`. You can add these three values to the database, or allow GAAP to prompt you for them. Emails sent should show up in your Gmail `Sent` box. 
