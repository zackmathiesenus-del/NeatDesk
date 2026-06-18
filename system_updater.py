import win32com.client
import os
def smart_update_flow():
    print("--- Checking for updates... ---")
    session = win32com.client.Dispatch("Microsoft.Update.Session")
    searcher = session.CreateUpdateSearcher()
    search_result = searcher.Search("IsInstalled=0")
    if search_result.Updates.Count == 0:
        print("Everything is up to date.")
        return
    print(f"Found {search_result.Updates.Count} updates.")
    print("Downloading all available updates in the background...")
    downloader = session.CreateUpdateDownloader()
    downloader.Updates = search_result.Updates
    downloader.Download()
    print("Attempting silent installation...")
    installer = session.CreateUpdateInstaller()
    installer.Updates = search_result.Updates
    try:
        result = installer.Install()
        if result.ResultCode == 2:
            print("Updates installed successfully!")
        else:
            print("Some updates require manual interaction.")
            print("Opening Windows Update Settings now...")
            os.system("start ms-settings:windowsupdate")
    except Exception as e:
        print(f"Manual intervention required. Opening Settings. Error: {e}")
        os.system("start ms-settings:windowsupdate")
if __name__ == "__main__":
    smart_update_flow()
    input("\nTask complete. Press Enter to exit.")