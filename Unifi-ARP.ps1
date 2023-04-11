$macPrefixes = "00-15-6D", "00-27-22", "00-50-C2", "04-18-D6", "18-E8-29", "24-5A-4C", "24-A4-3C", "28-70-4E", "44-D9-E7", "60-22-32", "68-72-51", "68-D7-9A", "70-A7-41", "74-83-C2", "74-AC-B9", "78-45-58", "78-8A-20", "80-2A-A8", "94-2A-6F", "9C-05-D6", "AC-8B-A9", "B4-FB-E4", "D0-21-F9", "D8-B3-70", "DC-9F-DB", "E0-63-DA", "E4-38-83", "F0-9F-C2", "F4-92-BF", "F4-E2-C6", "FC-EC-DA"

# Subnet identifier for ping sweep
$subnet = "192.168.200"

# Host IP to start ping sweep
$start = 1

# Host IP to finish ping sweep
$end = 254

# Define a scriptblock for the ping command
$pingScriptBlock = {param($IP) ping -n 1 -w 100 $IP}

# Output a message indicating that the ping sweep is starting
Write-Host "Starting ping sweep of subnet $subnet ..."

# Start a job for each IP
$jobs = ($start..$end).ForEach({
    $ip = "$subnet.$_"
    Start-Job -ScriptBlock $pingScriptBlock -ArgumentList $ip
})

# Wait for all jobs to finish and collect the results
$pingResults = $jobs | Wait-Job | Receive-Job

# Output a message indicating that the ping sweep is complete
Write-Host "Ping sweep of subnet $subnet is complete."

# Print the ping results
$pingResults | ForEach-Object {
    $ip = $_.Input
    $result = $_.Output
    if ($result) {
        Write-Host $ip
    }
}


Write-Host "Searching for Ubiquiti Devices..." -ForegroundColor Yellow

Start-Job -ScriptBlock { arp /a } | Out-Null

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
