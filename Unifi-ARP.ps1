$macPrefixes = "00-15-6D", "00-27-22", "00-50-C2", "04-18-D6", "18-E8-29", "24-5A-4C", "24-A4-3C", "28-70-4E", "44-D9-E7", "60-22-32", "68-72-51", "68-D7-9A", "70-A7-41", "74-83-C2", "74-AC-B9", "78-45-58", "78-8A-20", "80-2A-A8", "94-2A-6F", "9C-05-D6", "AC-8B-A9", "B4-FB-E4", "D0-21-F9", "D8-B3-70", "DC-9F-DB", "E0-63-DA", "E4-38-83", "F0-9F-C2", "F4-92-BF", "F4-E2-C6", "FC-EC-DA"

$subnets = Read-Host "Please enter the first 3 octets of your subnet (e.g. 192.168.1)"

Write-Host "Searching for Ubiquiti Devices..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Write-Host "This takes a while, running a full ping sweep on your network..." -ForegroundColor Red

$pingJob = Start-Job -ScriptBlock {
    param($subnet)
    $Subnet = "$subnet."
    1..254 | ForEach-Object {
        ping.exe -n 1 -l 0 -f -i 2 -w 1 -4 "$Subnet$_" | Out-Null
    }
} -ArgumentList $subnets

Wait-Job $pingJob | Out-Null

$arpOutput = arp -a | Select-String -Pattern "([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}"

$ubiquitiDevices = @()

foreach ($line in $arpOutput) {
    foreach ($prefix in $macPrefixes) {
        if ($line -match $prefix) {
            $ip = ($line -split '\s+')[1]
            $mac = ($line -match "([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}")[0]
            $mac = $mac -replace '\s+dynamic', '' -replace '\s', ''
            $ubiquitiDevices += [PSCustomObject]@{
                IPAddress = $ip
                MACAddress = $mac
            }
            break
        }
    }
}

if ($ubiquitiDevices.Count -eq 0) {
    Write-Host "No Ubiquiti devices found." -ForegroundColor Red
}
else {
    Write-Host "Found $($ubiquitiDevices.Count) Ubiquiti Devices!" -ForegroundColor Green

    foreach ($device in $ubiquitiDevices) {
        $ip = $device.IPAddress
        $mac = $device.MACAddress
        Write-Host "IP Address: $($ip)" -ForegroundColor Blue
    }
}

$runCommand = Read-Host "Do you want to run the set-inform command on all devices? (Y/N)"
if ($runCommand -eq "Y") {
    $controller = Read-Host "What is the IP or FQDN of your UniFi Controller"
    # Run set-inform command on all devices
    foreach ($device in $ubiquitiDevices) {
        $ip = $device.IPAddress
        Write-Host "Running set-inform command on device $ip" -ForegroundColor Yellow
        try {
            $sshSession = New-SSHSession -ComputerName $ip -Credential (Get-Credential -UserName "ubnt" Password "ubnt")
            $command = "set-inform http://${controller}:8080/inform"
            $response = Invoke-SSHCommand -Index $sshSession.SessionId -Command $command -ErrorAction Stop
            Write-Host "Successfully ran set-inform command on device $ip" -ForegroundColor Green
            # Wait for response from the device
            $stream = $sshSession.Session.CreateShellStream("PS-SSH", 0, 0, 0, 0, 1000)
            $output = ""
            while ($stream.Length -eq 0) {
                Start-Sleep -Milliseconds 500
            }
            while (!$stream.EOF) {
                $buffer = New-Object byte[] 1024
                $count = $stream.Read($buffer, 0, 1024)
                $output += ([System.Text.Encoding]::UTF8.GetString($buffer, 0, $count)).TrimEnd()
            }
            Write-Host "Response from device $ip $output" -ForegroundColor Green
            # Wait for device to respond
            $maxAttempts = 10
            $attempts = 0
            do {
                Start-Sleep -Seconds 5
                $ping = Test-Connection -ComputerName $ip -Count 1 -Quiet
                $attempts++
            } while (!$ping -and $attempts -lt $maxAttempts)
            if ($ping) {
                Write-Host "Device $ip responded to ping" -ForegroundColor Green
            } else {
                Write-Host "Device $ip did not respond to ping" -ForegroundColor Yellow
            }
            Remove-SSHSession -Index $sshSession.SessionId
        } catch {
            Write-Host "Failed to run set-inform command on device $ip" -ForegroundColor Red
        }
    }
} else {
    # Do nothing
}
