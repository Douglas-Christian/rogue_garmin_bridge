# Troubleshooting Guide

This comprehensive troubleshooting guide helps you resolve common issues with the Rogue Garmin Bridge application.

## Quick Diagnostic Checklist

Before diving into specific issues, run through this quick checklist:

1. **System Status**
   - [ ] Application is running (`http://localhost:5000` accessible)
   - [ ] Python 3.12+ is installed (`python --version`)
   - [ ] All dependencies are installed (`pip list`)
   - [ ] Bluetooth is enabled and functional

2. **Device Status**
   - [ ] Equipment is powered on
   - [ ] Equipment is in pairing/connection mode
   - [ ] Equipment is within range (< 10 meters)
   - [ ] No other apps are connected to equipment

3. **Connection Status**
   - [ ] Device appears in discovery scan
   - [ ] Connection status shows "Connected"
   - [ ] Signal strength is "Good" or better
   - [ ] Data is being received (check live metrics)

## Common Issues and Solutions

### Installation and Setup Issues

#### Python Version Compatibility

**Problem**: Application fails to start with Python version error
```
ERROR: pyftms requires Python 3.12 or higher
```

**Solution**:
1. Check current Python version:
   ```bash
   python --version
   ```

2. Install Python 3.12:
   - **Windows**: Download from [python.org](https://www.python.org/downloads/)
   - **macOS**: `brew install python@3.12`
   - **Linux**: `sudo apt install python3.12`

3. Create virtual environment with correct Python:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

#### Dependency Installation Failures

**Problem**: Package installation fails with permission or compilation errors

**Solution**:
1. Update pip to latest version:
   ```bash
   pip install --upgrade pip
   ```

2. Install with verbose output to identify issues:
   ```bash
   pip install -r requirements.txt -v
   ```

3. For compilation errors on Linux:
   ```bash
   sudo apt install build-essential python3.12-dev libbluetooth-dev
   ```

4. For Windows compilation issues:
   - Install Microsoft C++ Build Tools
   - Or use pre-compiled wheels: `pip install --only-binary=all -r requirements.txt`

#### Port Already in Use

**Problem**: Application fails to start with "Port 5000 already in use"

**Solution**:
1. Find and stop process using port 5000:
   ```bash
   # Linux/macOS
   lsof -i :5000
   kill -9 <PID>
   
   # Windows
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```

### Bluetooth and Device Connection Issues

#### Rogue Echo Rower Not Recognized

**Problem**: The Rogue Echo Rower connects but is treated as a bike, or workout data is not recorded correctly.

**Cause**: The Rogue Echo Rower advertises over BLE as **"ROGUE CONSOLE XXXXXX"** (not "Rogue Echo Rower"), so the application cannot auto-detect it as a rower.

**Solution**:
1. Navigate to the **Devices** page and click **Discover Devices**
2. When the device appears (it will show as "ROGUE CONSOLE XXXXXX"), select it
3. Before clicking **Connect**, change the **Device Type** dropdown to **"Rower"**
4. Click **Connect** — the app will now correctly record rower metrics (stroke rate, etc.)

> **Note**: The Rogue Echo Bike advertises as "ECHO\_BIKE\_XXXXXX" and is auto-detected correctly.

---

#### Device Not Found During Discovery

**Problem**: Equipment doesn't appear in device discovery scan

**Troubleshooting Steps**:

1. **Verify Equipment Setup**:
   - **Echo Bike**: Press and hold "Connect" button for 2 seconds until beeps
   - **Echo Rower**: Menu → Connect → Connect to App

2. **Check Bluetooth Status**:
   ```bash
   # Linux
   sudo systemctl status bluetooth
   bluetoothctl show
   
   # Windows
   # Check Bluetooth in Device Manager
   
   # macOS
   # Check Bluetooth in System Preferences
   ```

3. **Restart Bluetooth Service**:
   ```bash
   # Linux
   sudo systemctl restart bluetooth
   
   # Windows
   # Restart Bluetooth service in Services.msc
   
   # macOS
   # Turn Bluetooth off/on in System Preferences
   ```

4. **Clear Bluetooth Cache** (Windows):
   - Open Device Manager
   - Expand Bluetooth
   - Right-click adapter → Uninstall device
   - Restart computer
   - Let Windows reinstall driver

5. **Check Range and Interference**:
   - Move within 5 meters of equipment
   - Turn off other Bluetooth devices
   - Avoid WiFi interference (use 5GHz WiFi if possible)

#### Connection Drops Frequently

**Problem**: Device connects but disconnects repeatedly

**Diagnostic Steps**:

1. **Check Signal Strength**:
   - Navigate to Devices page
   - Monitor signal strength indicator
   - Move closer if signal is "Fair" or "Poor"

2. **Monitor Connection Quality**:
   - Check data rate indicators
   - Look for error messages in logs
   - Use built-in diagnostics tool

3. **Adjust Connection Settings**:
   - Navigate to Settings → System Configuration
   - Increase connection timeout values
   - Enable auto-reconnection
   - Adjust signal threshold

**Solutions**:

1. **Improve Signal Quality**:
   - Reduce distance to equipment
   - Remove physical obstructions
   - Use USB Bluetooth adapter with external antenna

2. **Update Drivers**:
   - Update Bluetooth adapter drivers
   - Update equipment firmware if available

3. **Adjust Power Management** (Windows):
   - Device Manager → Bluetooth adapter → Properties
   - Power Management → Uncheck "Allow computer to turn off this device"

#### Permission Denied Errors (Linux)

**Problem**: Bluetooth access denied or permission errors

**Solution**:
1. Add user to bluetooth group:
   ```bash
   sudo usermod -a -G bluetooth $USER
   ```

2. Logout and login again, or restart

3. Check bluetooth service permissions:
   ```bash
   sudo systemctl status bluetooth
   ```

4. For development, temporarily run with sudo:
   ```bash
   sudo python src/web/app.py
   ```

### Data Quality and Accuracy Issues

#### Inconsistent or Missing Data

**Problem**: Workout data shows gaps, spikes, or inconsistent values

**Diagnostic Steps**:

1. **Check Connection Quality**:
   - Monitor signal strength during workout
   - Check for connection drop notifications
   - Review data quality indicators

2. **Analyze Data Patterns**:
   - Look for correlation between data issues and connection problems
   - Check if issues occur at specific times or intensities
   - Compare with equipment display values

**Solutions**:

1. **Improve Connection Stability**:
   - Ensure stable positioning during workout
   - Minimize movement of computer/adapter
   - Use higher quality Bluetooth adapter

2. **Adjust Data Processing Settings**:
   - Enable data smoothing in Settings
   - Adjust outlier detection thresholds
   - Enable missing data interpolation

3. **Use Data Validation Tools**:
   - Review workout data after each session
   - Use built-in data analysis tools
   - Export and analyze in external tools if needed

#### Incorrect Speed Calculations

**Problem**: Speed values don't match equipment display

**Analysis**:
The application calculates speed from distance and time data. Discrepancies can occur due to:
- Equipment reporting errors
- Data transmission delays
- Calculation method differences

**Solutions**:

1. **Check Speed Calculation Settings**:
   - Navigate to Settings → Workout Preferences
   - Review speed calculation method
   - Enable speed smoothing if available

2. **Validate Against Distance**:
   - Compare total distance with equipment
   - Check for distance accumulation errors
   - Use distance-based speed validation

3. **Use Alternative Calculation**:
   - Enable instantaneous speed filtering
   - Use running average calculations
   - Apply outlier detection and removal

### FIT File and Garmin Connect Issues

#### FIT File Generation Failures

**Problem**: FIT file generation fails or produces invalid files

**Troubleshooting**:

1. **Check Workout Data Completeness**:
   - Ensure workout has minimum required data
   - Verify all timestamps are valid
   - Check for data gaps or corruption

2. **Validate FIT File Structure**:
   - Use built-in FIT analyzer tool
   - Check for required message types
   - Verify field value ranges

3. **Test with Minimal Data**:
   - Try generating FIT file with short, simple workout
   - Gradually increase complexity to identify issues

**Solutions**:

1. **Repair Workout Data**:
   - Use data repair tools in application
   - Fill missing data points with interpolation
   - Remove invalid data points

2. **Update FIT Generation Settings**:
   - Check device identification settings
   - Verify sport type mapping
   - Adjust training load calculation parameters

#### Garmin Connect Upload Issues

**Problem**: FIT files won't upload to Garmin Connect or show incorrect data

**Common Causes and Solutions**:

1. **Invalid Device Identification**:
   - **Problem**: Training load not calculated correctly
   - **Solution**: Verify device type settings in application
   - **Check**: Ensure proper manufacturer and product IDs

2. **Incorrect Sport Type**:
   - **Problem**: Activity appears as wrong type in Garmin Connect
   - **Solution**: Check sport type mapping in FIT generation settings

3. **Data Range Issues**:
   - **Problem**: Garmin Connect rejects file due to invalid values
   - **Solution**: Use FIT validation tools to check value ranges

4. **File Corruption**:
   - **Problem**: Upload fails with corruption error
   - **Solution**: Regenerate FIT file, check source workout data

### Web Interface Issues

#### Page Loading Problems

**Problem**: Web interface doesn't load or shows errors

**Troubleshooting**:

1. **Check Application Status**:
   ```bash
   # Verify application is running
   curl http://localhost:5000
   ```

2. **Check Browser Console**:
   - Open browser developer tools (F12)
   - Look for JavaScript errors
   - Check network requests for failures

3. **Clear Browser Cache**:
   - Clear browser cache and cookies
   - Try incognito/private browsing mode
   - Test with different browser

**Solutions**:

1. **Restart Application**:
   ```bash
   # Stop application (Ctrl+C)
   # Restart
   python src/web/app.py
   ```

2. **Check Static File Serving**:
   - Verify CSS and JavaScript files load correctly
   - Check file permissions
   - Ensure static directory is accessible

#### Real-time Data Not Updating

**Problem**: Live workout data doesn't update in web interface

**Diagnostic Steps**:

1. **Check Device Connection**:
   - Verify device shows "Connected" status
   - Check data is being received (look at logs)

2. **Check Browser Network Activity**:
   - Open developer tools → Network tab
   - Look for polling requests to `/api/live-data`
   - Check for WebSocket connections if used

**Solutions**:

1. **Refresh Page**:
   - Simple browser refresh often resolves temporary issues

2. **Check Polling Settings**:
   - Verify polling is enabled in settings
   - Adjust polling frequency if needed

3. **Restart Browser**:
   - Close and reopen browser
   - Clear cache if issues persist

### Performance Issues

#### Slow Response Times

**Problem**: Application responds slowly, especially during workouts

**Diagnostic Steps**:

1. **Check System Resources**:
   ```bash
   # Linux/macOS
   top
   htop
   
   # Windows
   # Task Manager → Performance tab
   ```

2. **Monitor Database Performance**:
   - Check database file size
   - Look for long-running queries in logs
   - Monitor disk I/O during workouts

**Solutions**:

1. **Optimize Database**:
   - Run database maintenance in Settings
   - Archive old workout data
   - Rebuild database indexes

2. **Adjust Performance Settings**:
   - Reduce chart update frequency
   - Decrease data retention period
   - Enable data compression

3. **System Optimization**:
   - Close unnecessary applications
   - Increase available RAM
   - Use SSD storage if possible

#### Memory Usage Issues

**Problem**: Application uses excessive memory or causes system slowdown

**Monitoring**:
```bash
# Check memory usage
ps aux | grep python  # Linux/macOS
# Task Manager on Windows
```

**Solutions**:

1. **Restart Application Regularly**:
   - Restart after long workout sessions
   - Schedule regular restarts for continuous operation

2. **Adjust Memory Settings**:
   - Enable automatic memory cleanup
   - Reduce data caching
   - Limit concurrent operations

3. **Upgrade System**:
   - Add more RAM if consistently running out
   - Use 64-bit Python for larger memory space

### Advanced Troubleshooting

#### Log Analysis

**Application Logs Location**: `logs/` directory

**Key Log Files**:
- `rogue_garmin_bridge.log`: Main application log
- `bluetooth.log`: Bluetooth connection details
- `data_flow.log`: Data processing information
- `error.log`: Error messages and stack traces
- `performance.log`: Performance metrics

**Log Analysis Commands**:
```bash
# View recent errors
tail -f logs/error.log

# Search for specific issues
grep -i "connection" logs/bluetooth.log

# Monitor real-time activity
tail -f logs/rogue_garmin_bridge.log
```

#### Database Issues

**Database Location**: `data/workouts.db`

**Common Database Problems**:

1. **Database Corruption**:
   ```bash
   # Check database integrity
   sqlite3 data/workouts.db "PRAGMA integrity_check;"
   ```

2. **Performance Issues**:
   ```bash
   # Analyze database
   sqlite3 data/workouts.db "ANALYZE;"
   
   # Vacuum database
   sqlite3 data/workouts.db "VACUUM;"
   ```

3. **Recovery from Backup**:
   - Use backup/restore functionality in Settings
   - Or manually restore from backup files

#### Network and Firewall Issues

**Problem**: Web interface not accessible from other devices

**Solutions**:

1. **Bind to All Interfaces**:
   ```bash
   python src/web/app.py --host 0.0.0.0
   ```

2. **Check Firewall Settings**:
   ```bash
   # Linux
   sudo ufw allow 5000
   
   # Windows
   # Add rule in Windows Firewall
   ```

3. **Test Network Connectivity**:
   ```bash
   # From another device
   telnet <computer-ip> 5000
   ```

## Getting Additional Help

### Built-in Diagnostic Tools

1. **Device Diagnostics**:
   - Navigate to Devices page
   - Click "Run Diagnostics"
   - Review system health report

2. **Performance Monitor**:
   - Check Settings → System Information
   - Monitor resource usage
   - Review performance metrics

3. **Data Validation Tools**:
   - Use FIT file analyzer
   - Run workout data validation
   - Check data integrity reports

### Collecting Debug Information

When reporting issues, include:

1. **System Information**:
   - Operating system and version
   - Python version
   - Application version
   - Bluetooth adapter details

2. **Error Details**:
   - Complete error messages
   - Steps to reproduce
   - Screenshots if applicable
   - Relevant log file excerpts

3. **Configuration**:
   - Settings configuration (anonymized)
   - Device types and models
   - Network configuration if relevant

### Support Resources

1. **Documentation**:
   - User Manual: `docs/user-guide/user-manual.md`
   - Installation Guide: `docs/user-guide/installation.md`
   - Developer Documentation: `docs/developer-guide/`

2. **Community Support**:
   - GitHub Issues: Report bugs and request features
   - Community Forums: User discussions and tips
   - FAQ: Common questions and answers

3. **Professional Support**:
   - Commercial support options
   - Custom development services
   - Training and consultation

### Emergency Recovery

#### Complete System Reset

If all else fails, perform a complete reset:

1. **Backup Important Data**:
   - Export all workout data
   - Save FIT files
   - Note custom settings

2. **Clean Installation**:
   ```bash
   # Remove virtual environment
   rm -rf venv
   
   # Recreate environment
   python3.12 -m venv venv
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

3. **Reset Configuration**:
   - Delete `data/` directory (after backup)
   - Remove `logs/` directory
   - Restart application for fresh setup

4. **Restore Data**:
   - Import workout data from backup
   - Reconfigure settings
   - Test functionality

This complete reset should resolve most persistent issues and provide a clean starting point.