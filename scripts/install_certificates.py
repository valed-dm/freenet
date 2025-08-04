"""
Install_certificates.py
A robust script to install root certificates for Python's SSL module.
"""

import os
import ssl
import sys
import certifi

def main():
    """
    Finds where Python's OpenSSL module expects to find certificates and
    ensures the 'certifi' bundle is available there.
    """
    print("Attempting to install/update root certificates for Python's SSL module...")

    try:
        # Get the path to the certifi certificate bundle
        certifi_path = certifi.where()
        print(f"Certifi bundle found at: {certifi_path}")

        # --- Find the target directory for SSL certificates ---
        # This is the most reliable way to find the correct path across different OSes
        # It gets the directory of the 'ssl' module and looks for a 'certs' subdir
        # If not found, it falls back to the directory of the Python executable

        ssl_module_path = os.path.dirname(ssl.__file__)
        potential_cert_path = os.path.join(ssl_module_path, "certs")

        # If the 'certs' directory doesn't exist, create it.
        # This is common on fresh Python installations.
        if not os.path.exists(potential_cert_path):
            print(f"Creating certificate directory at: {potential_cert_path}")
            try:
                os.makedirs(potential_cert_path)
            except OSError as e:
                print(f"Error creating directory: {e}. Try running as Administrator/sudo.")
                return

        # Define the final target file path
        target_pem_path = os.path.join(potential_cert_path, "cacert.pem")
        print(f"Target certificate file will be at: {target_pem_path}")

        # --- Create a symbolic link or copy the file ---
        # This makes the certifi bundle available at the location OpenSSL expects.
        if os.path.exists(target_pem_path):
            print("An existing certificate file was found. It will be replaced.")
            os.remove(target_pem_path)

        print("Creating link/copy...")
        # On Windows, copy the file. On macOS/Linux, create a symbolic link.
        if sys.platform == 'win32':
            import shutil
            shutil.copy(certifi_path, target_pem_path)
            action = "copied"
        else:
            os.symlink(certifi_path, target_pem_path)
            action = "linked"

        print(f"\nSUCCESS: Certificate bundle has been {action}.")
        print(f"'{certifi_path}' -> '{target_pem_path}'")
        print("\nSSL Certificate issue should now be resolved. You can run 'start.bat'.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        print("Could not complete the certificate installation.")
        print("Please ensure 'certifi' is installed (`pip install certifi`) and try again.")
        print("If errors persist, try running this script with administrator/sudo privileges.")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit.")
