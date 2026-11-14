# Facebook Auto-Reply Bot (Messages + Comments)

Replies automatically on your Facebook Page, in the same language the person writes in.
Uses Python, Flask and Google Gemini (free tier).

## Setup steps (about 45 minutes, no coding needed)

### Step 1: Get a free Gemini API key
1. Go to https://aistudio.google.com and sign in with Google.
2. Click "Get API key" and create a key. Copy it (this is GEMINI_API_KEY).

### Step 2: Put the code on GitHub
1. In your GitHub repo (Meer008/WHATS-BOT-), click "Add file" > "Upload files".
2. Upload: app.py, requirements.txt, .gitignore, README.md.
3. Do NOT upload .env.example with real keys. It only has placeholders, so it is safe.

### Step 3: Host it free on Render
1. Go to https://render.com and sign up with GitHub.
2. New > Web Service > choose your repo.
3. Runtime: Python. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Choose the Free plan.
6. Under Environment, add the variables from .env.example (VERIFY_TOKEN, PAGE_ACCESS_TOKEN, PAGE_ID, APP_SECRET, GEMINI_API_KEY, BUSINESS_INFO). Fill PAGE_ACCESS_TOKEN, PAGE_ID and APP_SECRET after Step 4.
7. Deploy. You get a URL like https://your-bot.onrender.com

Note: the free plan sleeps after 15 minutes of no traffic, so the first reply can be slow (up to a minute). Use a free uptime pinger (for example UptimeRobot, ping every 10 minutes) to keep it awake.

### Step 4: Create the Meta (Facebook) app
1. Go to https://developers.facebook.com > My Apps > Create App (type: Business).
2. Add the "Messenger" product and the "Webhooks" product.
3. Messenger > Settings > connect your Page and generate the Page Access Token. Copy it (PAGE_ACCESS_TOKEN).
4. Your Page ID: Facebook Page > About > Page transparency, or shown in the Messenger settings.
5. App settings > Basic: copy the App Secret (APP_SECRET).
6. Put these three values in Render's Environment and redeploy.

### Step 5: Connect the webhook
1. Meta dashboard > Webhooks > choose "Page" > Subscribe to this object.
2. Callback URL: https://your-bot.onrender.com/webhook
3. Verify token: the same VERIFY_TOKEN you set in Render.
4. Click Verify and Save.
5. Subscribe to the fields: `messages` and `feed`.
6. Make sure your Page is subscribed to the app (Messenger settings > Webhooks > add subscriptions for your Page).

### Step 6: Test
1. Message your Page from another Facebook account (add it as a Tester/Admin in the app roles while in Development mode).
2. Comment on a post of your Page from that account.
3. The bot should reply in the same language.

### Step 7: Go live for everyone
While the app is in Development mode, the bot only answers people with a role in the app. To answer the public:
1. Add a Privacy Policy URL and app icon in App settings > Basic.
2. Request Advanced Access (App Review) for: pages_messaging, pages_read_engagement, pages_manage_metadata, pages_manage_engagement (for comments).
3. Switch the app to Live mode after approval.

## Customize
Edit the BUSINESS_INFO variable in Render with your real services, prices and hours. The bot only uses what you write there, so it will not invent anything.

## Safety tips
- Never share your tokens or API keys with anyone, and never put them in the code.
- The bot replies to comments publicly, so keep BUSINESS_INFO professional.
- If you are on the free Gemini tier, very high traffic may hit rate limits. The bot then sends a polite fallback message.
