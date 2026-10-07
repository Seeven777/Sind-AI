# Agent Mode Life v3.1 — Google OAuth hotfix

- `google-auth` no longer starts a second `ProductRuntime`.
- `google-disconnect` no longer starts a second `ProductRuntime`.
- Both operations now use only Jarvis config + encrypted Google token storage.
- This allows `Connect-Google.cmd` to be executed while the main Jarvis UI/process is already running and owns `instance.lock`.
- Added regression tests to prevent this single-instance conflict from returning.
