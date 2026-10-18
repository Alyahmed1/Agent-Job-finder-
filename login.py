"""Sign in to Gmail again (opens a browser once). Used when the saved login expires."""
from collect.gmail import get_service

get_service(interactive=True)
print("Gmail login saved. You can close this window.")
