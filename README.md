# TTYOverMSSQL [![license: MIT](https://img.shields.io/github/license/b0o/tmux-autoreload?style=flat&color=green)](https://mit-license.org)

## About the project
**TTYOverMSSQL** is an interactive shell tool that allows you to spawn a pseudo tty on a Microsoft SQL Server using `xp_cmdshell`. It provides a seamless command-line experience, enabling you to run commands and upload files directly to the server.

> **Note:** This project is entirely inspired by the original work of [Alamot](https://github.com/Alamot/code-snippets/blob/master/mssql/mssql_shell.py). 🙌

## Features

- **Interactive Shell:** Execute commands directly on the MSSQL server. 💻
- **PowerShell Support:** Option to use PowerShell for command execution. 🛠️
- **File Uploads:** Upload files to the server with integrity checks. 📁
- **Command History:** Maintains a history of commands for convenience. 📜
- **Rich Output:** Enhanced terminal output using the `rich` library. 🌈

##  Installation with pipx (recommended)

```bash
sudo apt install git python3 pipx -y
pipx ensurepath
source .bashrc # or your shell config file
pipx install git+https://github.com/T1erno/ttyOverMSSQL.git
```

### Manual installation and execution

```bash
sudo apt install git python3 python-pip -y
git clone https://github.com/T1erno/ttyOverMSSQL.git
cd ttyovermssql
pip install -r requirements.txt
./ttyOverMSSQL.py
```

### 🛠️ Usage

```bash
ttyOverMSSQL -s <IP> -u <user> -p <password> [--powershell]
```

**Options:**

- `-s`, `--server`: MSSQL server address.
- `-u`, `--user`: MSSQL username.
- `-p`, `--password`: MSSQL password.
- `--powershell`: Use PowerShell instead of cmd.

**Example:**

```bash
ttyOverMSSQL -s 10.10.14.33 -u sa -p P@ssW0rD
```

### 📤 Uploading Files

Within the interactive shell, you can upload files using the `UPLOAD` command:

```plaintext
UPLOAD local_path <remote_path>
```

- `local_path`: Path to the file on your local machine. 🖴
- `remote_path` (optional): Destination path on the server. If omitted, the file will be uploaded to the current working directory. 📂

**Example:**

```plaintext
UPLOAD /path/to/local/file.txt C:\remote\path\file.txt
```

### ⚠️ Prerequisites

- **MSSQL Server:** Ensure that `xp_cmdshell` is enabled on the server. ⚙️
- **Python 3.x:** Make sure Python is installed on your local machine. 🐍

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 📄

### To do

- DOWNLOAD function
- Implement port option
- Refactor code

### Contributing

Code contributions always are welcome :^)
For contributing, please use dev branch for your changes.

### Reporting a bug

Found a bug? Open an issue! To help others reproduce and resolve it, include:

 - Problem description
 - Steps to reproduce
 - Screenshots or recordings (if applicable)
 - OS and other software version
 - Error messages
 - Any additional context

The more information you provide, the easier it will be for others to understand and address the issue :^)

### Disclaimer
This tool is provided for educational and research purposes only. Use of this tool on any system without the explicit permission of the system owner is illegal and strictly prohibited. The author is not responsible for any damages or consequences that may arise from the use of this tool. The user is responsible for complying with all applicable local, state and federal laws and regulations. Use of this tool is at your own risk and responsibility.

### Sources

- A huge thank you to [Alamot](https://github.com/Alamot) for the original inspiration behind this project.
- https://github.com/Alamot/code-snippets/blob/master/mssql/mssql_shell.py
