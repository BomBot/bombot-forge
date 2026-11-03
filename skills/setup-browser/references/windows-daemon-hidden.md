# Windows: bsk daemon at log on, with no window (reference for `setup-browser` Step 5b)

Evidence level, so nobody reads this as more than it is: the layout below was **observed on one Windows machine
(bsk 0.4.1, daemon 0.4.1, extension 0.4.1)** by a session doing a read-only inspection and reporting back in text. Task
`bsk-daemon` ran at log on with `LastTaskResult` 0, the daemon was up about 12 s later, `Get-Process bsk` showed
`MainWindowHandle` 0. **Not captured:** the Task's Settings/Principal XML, and whether a window flashes at the next
log on (nobody logged off and on). The Task settings under "Create or edit" are the intended design, not copied from
that machine.

## Why a launcher file

- On Windows `bsk` cannot start its own daemon (reported: it is caught by a Job Object), so something outside the
  command has to run `bsk daemon start --foreground` (the flag is documented as "owned by the current terminal or
  supervisor"). Task Scheduler is that something.
- `bsk.exe` straight in a Task opens a console window. `wscript.exe //B //Nologo <file>.vbs` that calls bsk with window
  style 0 does not (`MainWindowHandle` = 0 on the observed machine). `powershell -WindowStyle Hidden` was reported to flash a
  window at start; not tested here.
- `--daemon-idle 1440m` keeps the daemon from exiting after the default 10 minutes idle (flag exists in `bsk daemon start
  --help`, checked on 0.3.3).

## Runbook (Claude on the Windows machine)

1. **Look (read-only, do it now).**
   - `bsk --version`; `$env:BSK_AUTO_START='0'; bsk status --json` (daemon_version, pid, browsers, version_skew,
     unresponsive); `bsk update --check` (do not update).
   - Tasks that start bsk: `Get-ScheduledTask | Where-Object { $_.TaskName -match 'bsk' -or (($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -match 'bsk|wscript') }`;
     for each: `Export-ScheduledTask -TaskName '<name>'` and `Get-ScheduledTaskInfo`.
   - Duplicate starters: the Startup folder (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`) and the HKCU/HKLM `Run` keys.
   - How the running daemon was started: `Get-CimInstance Win32_Process -Filter "Name='bsk.exe'" | Select ProcessId,ParentProcessId,CommandLine`,
     then the parent's `Name`/`CommandLine`; `Get-Process bsk | Select Id,MainWindowHandle` (0 = no window).
2. **Show the plan and wait for OK.** Persistent change to the machine. Propose: Disable (never delete) any Task that
   opens a window; one Task `bsk-daemon`; how to undo. Default is No.
3. **After OK.**
   - Back up each existing Task first: `Export-ScheduledTask -TaskName '<name>' | Set-Content "<scratchpad>\task_<name>.backup.xml" -Encoding UTF8`.
   - `Disable-ScheduledTask -TaskName '<old window-opening task>'`.
   - Create `%USERPROFILE%\.local\bin\bsk-hidden.vbs` (ASCII; use the real path from `(Get-Command bsk).Source`):

     ```vbscript
     ' Launch bsk daemon with no visible window (window style 0)
     Set sh = CreateObject("WScript.Shell")
     sh.CurrentDirectory = "<user profile folder>"
     sh.Run """<path to bsk.exe>"" daemon start --foreground --daemon-idle 1440m", 0, False
     ```

   - Create or edit Task `bsk-daemon`: trigger At log on of this user, LogonType Interactive, RunLevel Limited, no execution
     time limit, MultipleInstances IgnoreNew:

     ```powershell
     $action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '//B //Nologo "<path to bsk-hidden.vbs>"'
     Set-ScheduledTask -TaskName 'bsk-daemon' -Action $action   # or Register-ScheduledTask with the trigger/settings above
     ```

   - If a daemon is already running: **ask the user before stopping it**; never kill it yourself (shared by several
     sessions); no `bsk session stop --all`. Only when none is running: `Start-ScheduledTask -TaskName 'bsk-daemon'`.
4. **Check and report evidence:** `Get-ScheduledTaskInfo -TaskName 'bsk-daemon'` -> `LastTaskResult` 0; `Get-Process bsk` exists with
   `MainWindowHandle` 0; `BSK_AUTO_START=0 bsk status --json` -> `daemon_version` equals `bsk --version`, a browser is
   connected, `unresponsive` false, `version_skew` false. Extension still says "Update the bsk browser service" -> the old daemon
   is still running: tell the user (see below).

Undo: `Enable-ScheduledTask` on the old Task and `Disable-ScheduledTask -TaskName 'bsk-daemon'` (or `Unregister-ScheduledTask`);
restore from the `.backup.xml` if a Task was edited.

## After `bsk update`

Reported on the Windows machine above: `bsk update` does **not** restart the daemon, so the CLI changes version while the
old daemon keeps running (the extension then asks to update the bsk browser service). The fix is to stop the old daemon
and let the Task bring up the new one. **Conflict not resolved:** on macOS 0.3.3 `bsk update --help` has
`--no-restart-daemon`, which suggests the default restarts it. Different OS and version; check `daemon_version` against
`bsk --version` after an update instead of assuming either. Stopping the old daemon needs the user's OK.
