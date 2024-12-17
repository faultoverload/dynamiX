# 🎥 DynamiX - Plex Recommendations Manager

**DynamiX** is an automation tool for dynamically managing Plex collections. It pins and unpins library collections based on configurable time blocks, ensuring fresh and relevant content is featured. This repository includes the Python script and its packaged `.exe` version for easier execution.

---

## 🚀 **Features**

- **Dynamic Pinning**: Automatically pin collections based on time and day configurations.
- **Exclusion Handling**: Avoid re-pinning the same collection for a configurable period.
- **User Exemptions**: Allow manual exclusion of specific collections.
- **GUI Control**: Includes an intuitive graphical interface for configuration and monitoring.
- **Robust Logging**: Provides clear logs of actions and issues.

---

## 🛠️ **Requirements**

- Python 3.8+
- Plex Media Server
- Plex API Token
- Required Libraries (specified in `requirements.txt`)

---

## 🔧 **Installation**

### Option 1: Run the `.exe` File (Recommended for Non-Developers)
1. Download the latest `script.exe` from the [Releases Page](https://github.com/YourUsername/DynamiX/releases).
2. Place it in a directory of your choice.
3. Double-click the `script.exe` to run the application.

### Option 2: Run the Python Script
1. Clone this repository:
   ```bash
   git clone https://github.com/YourUsername/DynamiX.git
   cd DynamiX


📋 Configuration
Upon first run, fill in the required configuration fields using the missing information fields:

Plex URL: Address of your Plex Media Server.
Plex Token: A valid Plex API Token.
Libraries: List of libraries to manage, separated by commas.
The program will generate and manage the following files:

config.json: Main settings file.
used_collections.json: Tracks recently pinned collections.
user_exemptions.json: Manages collections manually excluded by the user.

🖥️ Usage
Launch the application.
Use the tabs to:
Configure the Plex server and dynamic settings.
Manage exclusions and exemptions.
View real-time logs of actions taken.
Press "Run Main Function" in the Logs tab to start the automation.

🧩 Dependencies
Required libraries:
plexapi
requests
ttkbootstrap

Install them with:
pip install -r requirements.txt

📝 License
This project is licensed under the MIT License. See the LICENSE file for details.

🛠️ Contributing
Contributions are welcome! Follow these steps:

Fork the repository.
Create a new branch: git checkout -b feature-name.
Commit your changes: git commit -m "Description of changes".
Push to the branch: git push origin feature-name.
Open a pull request.
See the full contributing guidelines in CONTRIBUTING.md.


Here is a complete set of files and documentation content needed for a GitHub repository for your script, packaged as an .exe application.

📁 Repository File Structure
plaintext
Copy code
/Repository Root
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CHANGELOG.md
├── requirements.txt
├── src/
│   └── script.py
├── build/
│   └── script.exe
└── config/
    ├── config.json
    ├── used_collections.json
    └── user_exemptions.json
📄 README.md
markdown
Copy code
# 🎥 DynamiX - Plex Recommendations Manager

**DynamiX** is an automation tool for dynamically managing Plex collections. It pins and unpins library collections based on configurable time blocks, ensuring fresh and relevant content is featured. This repository includes the Python script and its packaged `.exe` version for easier execution.

---

## 🚀 **Features**

- **Dynamic Pinning**: Automatically pin collections based on time and day configurations.
- **Exclusion Handling**: Avoid re-pinning the same collection for a configurable period.
- **User Exemptions**: Allow manual exclusion of specific collections.
- **GUI Control**: Includes an intuitive graphical interface for configuration and monitoring.
- **Robust Logging**: Provides clear logs of actions and issues.

---

## 🛠️ **Requirements**

- Python 3.8+
- Plex Media Server
- Plex API Token
- Required Libraries (specified in `requirements.txt`)

---

## 🔧 **Installation**

### Option 1: Run the `.exe` File (Recommended for Non-Developers)
1. Download the latest `script.exe` from the [Releases Page](https://github.com/YourUsername/DynamiX/releases).
2. Place it in a directory of your choice.
3. Double-click the `script.exe` to run the application.

### Option 2: Run the Python Script
1. Clone this repository:
   ```bash
   git clone https://github.com/YourUsername/DynamiX.git
   cd DynamiX
Install dependencies:
bash
Copy code
pip install -r requirements.txt
Run the script:
bash
Copy code
python src/script.py
📋 Configuration
Upon first run, fill in the required configuration fields:

Plex URL: Address of your Plex Media Server.
Plex Token: A valid Plex API Token.
Libraries: List of libraries to manage, separated by commas.
The program will generate and manage the following files:

config.json: Main settings file.
used_collections.json: Tracks recently pinned collections.
user_exemptions.json: Manages collections manually excluded by the user.
🖥️ Usage
Launch the application.
Use the tabs to:
Configure the Plex server and dynamic settings.
Manage exclusions and exemptions.
View real-time logs of actions taken.
Press "Run Main Function" in the Logs tab to start the automation.
🧩 Dependencies
Required libraries:

plaintext
Copy code
plexapi
requests
ttkbootstrap
Install them with:

bash
Copy code
pip install -r requirements.txt
📝 License
This project is licensed under the MIT License. See the LICENSE file for details.

🛠️ Contributing
Contributions are welcome! Follow these steps:

Fork the repository.
Create a new branch: git checkout -b feature-name.
Commit your changes: git commit -m "Description of changes".
Push to the branch: git push origin feature-name.
Open a pull request.
See the full contributing guidelines in CONTRIBUTING.md.

🕒 Changelog
See CHANGELOG.md for version history.

📞 Support
If you encounter any issues or have feature suggestions, please open an issue on GitHub.

yaml
Copy code

---

## 📄 **LICENSE** (MIT License)

MIT License

Copyright (c) 2024 [Connor Harrell]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so.
