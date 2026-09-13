"""Interactive standard W&B login. The SDK stores credentials in the user's netrc."""
import getpass
import os
import wandb

if __name__ == "__main__":
    key = getpass.getpass("W&B API key (hidden; obtain from https://wandb.ai/authorize): ")
    if not key.strip():
        raise SystemExit("No credential supplied; no changes made.")
    os.environ["WANDB_API_KEY"] = key.strip()
    try:
        wandb.login(key=key.strip(), verify=True, relogin=True)
        print("W&B login verified. Return to Optara and click Verify connections.")
    except Exception as error:
        # Report only the exception class, never its message/request/headers.
        print(f'Verification failed ({type(error).__name__}); credential contents were not logged.')
        raise SystemExit('Use a fresh W&B API key from https://wandb.ai/authorize and retry secure sign-in.')
