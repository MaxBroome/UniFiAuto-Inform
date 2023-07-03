import sys
import socket
import nmap
import paramiko
import qdarkstyle
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QInputDialog, QMessageBox, QFrame
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor



class DeviceScannerThread(QThread):
    scan_complete = pyqtSignal(list)

    def __init__(self, parent=None):
        super(DeviceScannerThread, self).__init__(parent)
        self.target_ip = ""
        self.mac_prefixes = [
            "00:15:6D", "00:27:22", "00:50:C2", "04:18:D6", "18:E8:29", "24:5A:4C",
            "24:A4:3C", "28:70:4E", "44:D9:E7", "60:22:32", "68:72:51", "68:D7:9A",
            "70:A7:41", "74:83:C2", "74:AC:B9", "78:45:58", "78:8A:20", "80:2A:A8",
            "94:2A:6F", "9C:05:D6", "AC:8B:A9", "B4:FB:E4", "D0:21:F9", "D8:B3:70",
            "DC:9F:DB", "E0:63:DA", "E4:38:83", "F0:9F:C2", "F4:92:BF", "F4:E2:C6",
            "FC:EC:DA"
        ]
        self.controller_ip = ""

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        local_ip = s.getsockname()[0]
        split_ip = local_ip.rsplit(".", 1)
        self.target_ip = split_ip[0] + ".0/24"

        nm = nmap.PortScanner()
        nm.scan(hosts=self.target_ip, arguments="-sn -n -vv")

        ubiquiti_devices = []

        for host in nm.all_hosts():
            if 'mac' in nm[host]['addresses']:
                mac = nm[host]['addresses']['mac']
                for prefix in self.mac_prefixes:
                    if mac.startswith(prefix):
                        ip = nm[host]['addresses']['ipv4']
                        ubiquiti_devices.append({"ip": ip, "mac": mac})
                        break

        self.scan_complete.emit(ubiquiti_devices)


class SetInformThread(QThread):
    device_processed = pyqtSignal(str, bool)

    def __init__(self, device_ip, username, password, controller_ip, parent=None):
        super(SetInformThread, self).__init__(parent)
        self.device_ip = device_ip
        self.username = username
        self.password = password
        self.controller_ip = controller_ip

    def run(self):
        success = self.set_inform(self.device_ip, self.username, self.password)
        self.device_processed.emit(self.device_ip, success)

    def set_inform(self, device_ip, username, password):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, username=username, password=password, timeout=5)
            stdin, stdout, stderr = ssh.exec_command("/usr/bin/mca-cli-op set-inform http://"+self.controller_ip+":8080/inform")
            stdout.readlines()
            ssh.close()
            return True
        except:
            return False


class UbiquitiDeviceScannerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.devices_found = False
        self.devices_count = 0

        self.setWindowTitle("UniFi Auto-Inform Tool")
        self.setGeometry(100, 100, 500, 400)

        self.layout = QVBoxLayout()

        self.feedback_label = QLabel("Click 'Start Scan' to search for Ubiquiti devices.")
        self.layout.addWidget(self.feedback_label)

        self.devices_list = QListWidget()
        self.devices_list.setFrameShape(QFrame.NoFrame)
        self.layout.addWidget(self.devices_list)
        self.devices_list.setVisible(False)

        self.divider_line = QFrame()
        self.divider_line.setFrameShape(QFrame.HLine)
        self.divider_line.setFrameShadow(QFrame.Sunken)
        self.divider_line.setVisible(False)
        self.layout.addWidget(self.divider_line)

        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.layout.addWidget(self.scan_button)

        self.set_inform_button = QPushButton("Run Set-Inform on All Devices")
        self.set_inform_button.clicked.connect(self.run_set_inform)
        self.set_inform_button.setVisible(False)
        self.layout.addWidget(self.set_inform_button)

        self.setLayout(self.layout)

        self.device_scanner_thread = None
        self.set_inform_threads = []

    def start_scan(self):
        self.scan_button.setDisabled(True)
        self.devices_list.clear()
        self.devices_list.setVisible(False)
        self.divider_line.setVisible(False)
        self.set_inform_button.setVisible(False)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        local_ip = s.getsockname()[0]
        split_ip = local_ip.rsplit(".", 1)
        subnet = split_ip[0] + ".0/24"

        self.feedback_label.setText(f"Scanning for devices on {subnet}...")

        self.device_scanner_thread = DeviceScannerThread()
        self.device_scanner_thread.scan_complete.connect(self.devices_scanned)
        self.device_scanner_thread.finished.connect(self.scan_complete)
        self.device_scanner_thread.start()

    def devices_scanned(self, devices):
        self.devices_found = True
        self.devices_count = len(devices)

        for device in devices:
            item = f"IP address: {device['ip']}\nMAC address: {device['mac']}"
            self.devices_list.addItem(item)

        self.devices_list.setVisible(True)
        self.divider_line.setVisible(True)
        self.set_inform_button.setVisible(True)

    def scan_complete(self):
        if not self.devices_found:
            self.feedback_label.setText("No devices found.")
        else:
            self.feedback_label.setText(f"Found {self.devices_count} devices.")

        self.scan_button.setEnabled(True)
        self.scan_button.setText("Re-Scan for devices")

    def run_set_inform(self):
        if not self.devices_found:
            return

        self.set_inform_button.setEnabled(False)
        self.feedback_label.setText("Running Set-Inform...")

        ip, ok = QInputDialog.getText(
            self, "Ubiquiti Device Scanner", "Enter the IP or FQDN of the UniFi controller:"
        )
        if ok:
            self.controller_ip = ip.strip()
        else:
            self.set_inform_button.setEnabled(True)
            return

        use_custom_credentials = QMessageBox.question(
            self, "Ubiquiti Device Scanner", "Do you want to use custom SSH credentials?",
            QMessageBox.No | QMessageBox.Yes, QMessageBox.No
        )
        if use_custom_credentials == QMessageBox.Yes:
            username, username_ok = QInputDialog.getText(self, "Ubiquiti Device Scanner", "Enter SSH username:")
            password, password_ok = QInputDialog.getText(self, "Ubiquiti Device Scanner", "Enter SSH password:")
            if not username_ok or not password_ok:
                self.set_inform_button.setEnabled(True)
                return
        else:
            username = "ubnt"
            password = "ubnt"

        for i in range(self.devices_list.count()):
            item = self.devices_list.item(i)
            item_text = item.text()
            ip_address = item_text.split("\n")[0].replace("IP address: ", "")

            set_inform_thread = SetInformThread(ip_address, username, password, self.controller_ip)
            set_inform_thread.device_processed.connect(self.device_processed)
            set_inform_thread.start()
            self.set_inform_threads.append(set_inform_thread)

    def device_processed(self, device_ip, success):
        for i in range(self.devices_list.count()):
            item = self.devices_list.item(i)
            item_text = item.text()
            ip_address = item_text.split("\n")[0].replace("IP address: ", "")

            if ip_address == device_ip:
                device_status = "Success" if success else "Failed"
                item.setText(f"{item_text}\nStatus: {device_status}")
                item.setForeground(QColor("green" if success else "red"))
                break

        self.check_set_inform_complete()

    def check_set_inform_complete(self):
        all_complete = all([not thread.isRunning() for thread in self.set_inform_threads])

        if all_complete:
            self.feedback_label.setText("Set-Inform completed.")
            self.set_inform_button.setEnabled(True)

    def closeEvent(self, event):
        if self.device_scanner_thread is not None and self.device_scanner_thread.isRunning():
            self.device_scanner_thread.terminate()
            self.device_scanner_thread.wait()

        for thread in self.set_inform_threads:
            if thread.isRunning():
                thread.terminate()
                thread.wait()

        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    window = UbiquitiDeviceScannerApp()
    window.show()

    sys.exit(app.exec_())
