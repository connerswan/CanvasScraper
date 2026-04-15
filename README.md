# CanvasScraper

Scrape your Canvas LMS course materials and upload them to Google Drive, organized by course and module.

**Grabs:** Files/documents, your assignment submissions, and the course syllabus.
**Organizes:** One folder per course in Drive, with subfolders matching Canvas modules.
**Safe to re-run:** Already-uploaded files are skipped automatically.

---

## Setup

### 1. Download and install Python

You need Python 3.10 or newer. To check if you already have it:

- **Mac:** Open Terminal (press `Cmd + Space`, type "Terminal", press Enter) and run:
  ```
  python3 --version
  ```
- **Windows:** Open Command Prompt (press the Windows key, type "cmd", press Enter) and run:
  ```
  python --version
  ```

If Python isn't installed or the version is below 3.10, download it from [python.org/downloads](https://www.python.org/downloads/) and run the installer. On Windows, check **"Add Python to PATH"** during installation — this is easy to miss and will cause problems if skipped.

---

### 2. Download CanvasScraper

1. Go to the CanvasScraper GitHub page
2. Click the green **Code** button, then click **Download ZIP**
3. Once downloaded, unzip the file — you should end up with a folder called `CanvasScraper-main` (on Mac, double-click the zip; on Windows, right-click > Extract All)
4. Move that folder somewhere you'll remember, like your Desktop or Documents

---

### 3. Open a terminal in the CanvasScraper folder

This step tells your computer to "look inside" the CanvasScraper folder for the next commands.

**Mac:**
1. Open Terminal (`Cmd + Space`, type "Terminal", press Enter)
2. Type `cd ` (with a space after it), then drag the `CanvasScraper-main` folder from Finder into the Terminal window — it will fill in the path for you
3. Press Enter

**Windows:**
1. Open the `CanvasScraper-main` folder in File Explorer
2. Click on the address bar at the top of the window (where it shows the folder path), type `cmd`, and press Enter — this opens Command Prompt already pointed at that folder

---

### 4. Install CanvasScraper

In your terminal, run:

```
pip install -e .
```

> **Mac:** If that doesn't work, try `pip3 install -e .`

This installs the tool and its dependencies. You only need to do this once.

---

### 5. Get your Canvas API token

1. Log into Canvas at [canvas.uw.edu](https://canvas.uw.edu)
2. Click your profile picture (top-left) > **Settings**
3. Scroll down to **Approved Integrations** and click **+ New Access Token**
4. Give it a name like "CanvasScraper" — leave the expiry date blank
5. Click **Generate Token**, then copy it immediately — you won't be able to see it again

---

### 6. Create your config file

In the `CanvasScraper-main` folder, find the file called `.env.example`. Make a copy of it and name the copy `.env` (no `.example` at the end).

**Mac:** In your terminal, run:
```
cp .env.example .env
```

**Windows (Command Prompt):**
```
copy .env.example .env
```

**Windows (PowerShell):**
```
Copy-Item .env.example .env
```

Now open `.env` in a text editor (Notepad on Windows, TextEdit on Mac) and fill in your token:

```
CANVAS_API_TOKEN=paste_your_token_here
CANVAS_BASE_URL=https://canvas.uw.edu
```

Save the file. Make sure your editor doesn't add `.txt` to the end — it must stay named exactly `.env`.

---

### 7. Get Google Drive credentials

You need a file called `client_secret.json` to allow the app to upload to your Google Drive.

**Option A — Get it from a classmate who already set this up (easiest)**

Ask them to share their `client_secret.json` file with you. Once you have it:

1. Inside `CanvasScraper-main`, create a folder called `credentials` (if it doesn't already exist)
2. Place `client_secret.json` inside that folder, so the path looks like:
   ```
   CanvasScraper-main/credentials/client_secret.json
   ```
3. Ask your classmate to go to their Google Cloud Console > **APIs & Services > OAuth consent screen > Test users** and add your Google or school email address

> **Note for whoever owns the Google Cloud project:** There is no cost for sharing this, and files always upload to each person's own Google Drive — never yours. The only limit is that "Testing" mode supports up to 100 test users total. If more than 100 people need access, the project owner would need to go through Google's app verification process.

---

**Option B — Set up your own Google Cloud project (takes ~10 min)**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in
2. Click **Select a project** at the top, then **New Project**:
   - **Project name:** `CanvasScraper` (or anything you like)
   - **Organization:** `uw.edu` (pick this over "No organization" if you see it)
   - **Parent resource:** Under `uw.edu`, select `Self-Managed` > `Students`
   - Click **Create**
3. Go to **APIs & Services > Library**, search for **"Google Drive API"**, click it, then click **Enable**
4. Go to **APIs & Services > OAuth consent screen**:
   - User type: **External** > **Create**
   - Fill in an app name and your email for support
   - Click **Save and Continue** through the Scopes page without changing anything
   - On the **Test users** page, click **Add Users** and add your school email
   - Click **Save and Continue**, then **Back to Dashboard**
5. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**:
   - Application type: **Desktop app**
   - Click **Create**, then **Download JSON**
   - Rename the downloaded file to `client_secret.json` and place it at:
     ```
     CanvasScraper-main/credentials/client_secret.json
     ```

---

### 8. Run

In your terminal (make sure you're still in the `CanvasScraper-main` folder), run:

```
canvas-scraper
```

The first time you run it, a browser window will open asking you to sign into Google. Sign in with your school Google account and click **Allow**. After that, your login is saved and no browser window will appear on future runs.

You'll then see a list of your Canvas courses and can choose which ones to scrape.

---

## Options

```
canvas-scraper --dry-run    # Show what would be uploaded, without actually uploading
canvas-scraper --help
```

---

## Troubleshooting

**"CANVAS_API_TOKEN is not set"**
Make sure your `.env` file exists (not `.env.example` or `.env.txt`) and contains your token.

**"Google OAuth credentials not found"**
Make sure `client_secret.json` is inside a `credentials` folder in `CanvasScraper-main`.

**"Canvas API token is invalid or expired"**
Generate a new token in Canvas (Account > Settings > Approved Integrations) and update your `.env` file.

**Google login fails with "Access blocked"**
Your email hasn't been added as a test user. Ask the Google Cloud project owner to add you under **APIs & Services > OAuth consent screen > Test users**.

**Re-running after a partial scrape**
Just run `canvas-scraper` again. Already-uploaded files are tracked automatically and will be skipped.

**Can't find the `.env` file in Finder or File Explorer**
Files starting with a period are hidden by default on some systems. To show them:
- **Mac:** Open the `CanvasScraper-main` folder in Finder and press `Cmd + Shift + .` (period) — hidden files will appear. Press the same shortcut again to hide them.
- **Windows:** In File Explorer, click the **View** tab and check **Hidden items**.

**`canvas-scraper` command not found**
Re-run `pip install -e .` (or `pip3 install -e .` on Mac) from inside the `CanvasScraper-main` folder.

---

## What gets scraped

| Content | Where it lands in Drive |
|---------|------------------------|
| Files in modules | `CanvasScraper / Course Name / Module Name / file.pdf` |
| Syllabus | `CanvasScraper / Course Name / Syllabus` (as Google Doc) |
| Your submissions | `CanvasScraper / Course Name / Assignments / Assignment Name — file.pdf` |

---

## Security notes

- Your Canvas token and Google credentials are stored locally and never leave your machine
- The app only has permission to see files it created (`drive.file` scope) — it cannot access anything else in your Drive
