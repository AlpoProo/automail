# BEST Club Email Automation

## 📝 Project Description
This project is an email automation application developed for the BEST club. It automatically sends emails to addresses listed in an Excel file. The application controls daily email sending limits and tracks sending status.

## 🚀 Features
- Bulk email sending from Excel file
- HTML format email content support
- Attachment and signature image support
- Daily email sending limit (300)
- Sending status tracking
- Configuration save and load
- Music player integration
- Detailed logging with console output
- Sending records with database

## 🛠️ Technologies Used
- Python
- Tkinter (GUI)
- SQLite3 (Database)
- PyQt5 (Music Player)
- SMTP (Email Sending)
- OpenPyXL (Excel Operations)

## 📦 Installation
1. Install required Python packages:
```bash
pip install -r requirements.txt
```

2. Start the application:
```bash
python main.py
```

## 🔧 Usage
1. Enter sender email address and application password
2. Set email subject and content
3. Select attachment and signature image
4. Select Excel file containing recipient emails
5. Click "Start" to begin sending

## ⚠️ Important Notes
- Two-factor authentication must be enabled on your Google account
- To get application password: https://myaccount.google.com/apppasswords
- Emails must be in column A of the Excel file
- Daily email limit: 300
- When sending is stopped, check the last sent email to continue from where it left off

## 🔄 Configuration
- Save current settings with "Save Config" button
- Load saved settings with "Load Config" button
- Reset database with "Reset" button

## 🎵 Music Player
- Built-in music player functionality
- Previous/Next track controls
- Mute mode

## 📊 Database
- Sending records with SQLite database
- Daily limit tracking
- Last sent email information

## 👨‍💻 Developer
- Alperen Gökdeniz
- Contact: alperen@gokdeniz.tr

## 📝 License
This project is specifically developed for the BEST club.

## 🔄 Updates
- Application password support
- HTML content support
- Configuration save/load
- Music player integration
- Database integration
