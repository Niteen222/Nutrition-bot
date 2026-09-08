# NutriTrack AI Discord Bot 🥗🤖

An intelligent Discord bot powered by Google Gemini AI and Google Sheets integration for daily food photo analysis, macro tracking, and candidate attendance monitoring.

---

## 🌟 Features
- **Instant Nutrition Breakdown**: Analyzes food photos and estimates Portions, Calories, Protein, Carbs, Fats, and Fiber.
- **Health Rating**: Generates a 1-to-5 star rating with concise health tips.
- **Google Sheets Attendance Tracking**: Marks candidate status (`Present`/`Absent`) in real-time.
- **Daily Roster Check & Reminder**: Automated reminders at 8:00 AM and end-of-day absence check at 11:50 PM.

---

## 🚀 24/7 Cloud Deployment (Free)

### Step 1: Push Code to GitHub
1. Initialize git and commit:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for NutriTrack Bot"
   ```
2. Create a **Private Repository** on GitHub (e.g. `nutritrack-discord-bot`).
3. Push to your repo:
   ```bash
   git remote add origin https://github.com/<YOUR_USERNAME>/<REPO_NAME>.git
   git branch -M main
   git push -u origin main
   ```
   *(Note: `.gitignore` automatically protects your `.env` and `credentials.json` from being pushed).*

---

### Step 2: Deploy on Render.com (24/7 Free Hosting)
1. Go to [Render.com](https://render.com) and Sign Up / Log In with GitHub.
2. Click **New +** ➔ **Background Worker** (or **Web Service**).
3. Select your GitHub repository.
4. Set the following:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Under **Environment Variables**, add:
   - `DISCORD_BOT_TOKEN` = `your_discord_bot_token`
   - `DISCORD_MAIN_CHANNEL_ID` = `your_channel_or_thread_id`
   - `GEMINI_API_KEY` = `your_gemini_api_key`
   - `GOOGLE_SHEET_ID` = `your_google_sheet_id`
   - `GOOGLE_CREDENTIALS_JSON` = *(Copy and paste the entire text content of your `credentials.json`)*
6. Click **Create Background Worker**.

Your bot is now deployed and running **24/7**! 🎉
