import socket
import paramiko
import time
import nmap
from colorama import *

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

init(convert=True)

# Get the user's LAN IP to use for the nmap scan.
# This can be weird sometimes, and only works for /24 subnets. I will add an override for this in the coming GUI release.
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("1.1.1.1", 80))
local_ip = s.getsockname()[0]
split_ip = local_ip.rsplit(".", 1)
target_ip = split_ip[0] + ".0/24"

print(f"Searching for Ubiquiti Devices in {bcolors.HEADER}{target_ip}{bcolors.ENDC}...")

mac_prefixes = [
    "00:15:6D", "00:27:22", "00:50:C2", "04:18:D6", "18:E8:29", "24:5A:4C",
    "24:A4:3C", "28:70:4E", "44:D9:E7", "60:22:32", "68:72:51", "68:D7:9A",
    "70:A7:41", "74:83:C2", "74:AC:B9", "78:45:58", "78:8A:20", "80:2A:A8",
    "94:2A:6F", "9C:05:D6", "AC:8B:A9", "B4:FB:E4", "D0:21:F9", "D8:B3:70",
    "DC:9F:DB", "E0:63:DA", "E4:38:83", "F0:9F:C2", "F4:92:BF", "F4:E2:C6",
    "FC:EC:DA"
]

# Also for some reason, sometimes I have to run the script twice becasue nmap doesn't display all the devices. WTF nmap... Plz tell me what i'm doing wrong plz
nm = nmap.PortScanner()
nm.scan(hosts=target_ip, arguments="-sn -n")

ubiquiti_devices = []

for host in nm.all_hosts():
    if 'mac' in nm[host]['addresses']:
        mac = nm[host]['addresses']['mac']
        for prefix in mac_prefixes:
            if mac.startswith(prefix):
                ip = nm[host]['addresses']['ipv4']
                ubiquiti_devices.append(ip)
                print(f"{bcolors.OKBLUE}IP Address: {ip} | MAC Address: {mac}{bcolors.ENDC}")
                break

if len(ubiquiti_devices) == 0:
    print(f"{bcolors.FAIL}No Ubiquiti devices found.{bcolors.ENDC}")
else:
    print(f"{bcolors.OKGREEN}Found {len(ubiquiti_devices)} Ubiquiti Devices!{bcolors.ENDC}")

run_set_inform = input("Do you want to run a set-inform command on all devices? (y/n): ")

if run_set_inform.lower() == "y":
    use_custom_credentials = input(f"{bcolors.WARNING}Do you want to use custom SSH credentials? (y/n): {bcolors.ENDC}")

    if use_custom_credentials.lower() == "y":
        username = input("Enter the SSH username: ")
        password = input("Enter the SSH password: ")
    else:
        username = "ubnt"
        password = "ubnt"

    controller_ip = input(f"{bcolors.HEADER}Enter the IP address or FQDN of your UniFi controller: {bcolors.ENDC}")

    for device in ubiquiti_devices:
        ip = device

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(ip, username=username, password=password)

            time.sleep(.5)  # Add a delay of half a second after connecting. (Slow ass Ubiquiti devices... /s)

            command = f"/usr/bin/mca-cli-op set-inform http://{controller_ip}:8080/inform"
            stdin, stdout, stderr = ssh_client.exec_command(command)

            success_output = "Adoption request sent to"
            if success_output in stdout.read().decode():
                print(f"{bcolors.OKGREEN}Set-inform command sent successfully to {ip}{bcolors.ENDC}")
            else:
                print(f"{bcolors.FAIL}Failed to send set-inform command to {ip}{bcolors.ENDC}")

            ssh_client.close()
        except (paramiko.ssh_exception.SSHException, EOFError) as e:
            if "Error reading SSH protocol banner" in str(e):
                print(f"{bcolors.FAIL}Failed to connect to {ip}. This device likely doesn't support SSH.{bcolors.ENDC}")
            else:
                print(f"{bcolors.FAIL}Error connecting to {ip}: {str(e)}{bcolors.ENDC}")
        except Exception as e:
            print(f"{bcolors.FAIL}Error connecting to {ip}: {str(e)}{bcolors.ENDC}")
        finally:
            ssh_client.close()

print(f"{bcolors.HEADER}Thank you for using my script!{bcolors.ENDC}")
print(f"With {bcolors.FAIL}<3{bcolors.ENDC} - MaxBroome on GitHub")
time.sleep(3)
print("Exiting Now! Bye!")
time.sleep(5)
