# Installing a watch face on a Galaxy Watch (Windows)

These steps work for every face in `faces/`. Each face is its own Android Studio project. Written for a Galaxy Watch 6 and a Windows PC, but any Wear OS 4+ watch works the same way.

## One-time setup

### 1. Install Android Studio
Install [Android Studio](https://developer.android.com/studio). The default options are fine.

### 2. Turn on debugging on the watch
1. On the watch, go to **Settings > About watch > Software information**.
2. Tap **Software version** 5 times. A message appears saying Developer mode is on.
3. Go back to **Settings > Developer options** and turn on **ADB debugging** and **Wireless debugging**.
4. Make sure the watch is connected to the same Wi-Fi network as your PC, not just to your phone over Bluetooth.

### 3. Pair the PC with the watch
1. On the watch, in **Wireless debugging**, tap **Pair new device**. It shows a 6-digit code and an `IP:port`.
2. In Android Studio, open the **Terminal** tab (bottom of the window) and run:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" pair <IP:port shown on the pairing screen> <6-digit code>
   ```

You only pair once per PC.

## Each time you install or update a face

### 4. Open the face's folder
In Android Studio, choose **File > Open** and select the face's folder, for example `faces\earth-day-night`. Don't open the repository root, which isn't a Gradle project.

The first sync downloads several hundred MB. If Android Studio offers to install a missing SDK platform (Android 13 / API 33), accept.

### 5. Connect to the watch
On the watch's **Wireless debugging** screen, note the **IP address & port**. This port is different from the pairing port, and it changes when Wireless debugging is turned off and on again. Then run:
```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" connect <that IP:port>
```
The watch should appear in the device drop-down at the top of Android Studio.

### 6. Install
1. The first time you open each face, choose **Run > Edit Configurations…** and select **watchface**. Under **Launch Options**, set **Launch** to **Nothing** (there's no app screen to open), then click **OK**.
2. Pick the watch in the device drop-down and press the green **Run ▶** button.

A newer build replaces the old one in place. If the face is showing, the watch switches to the new version.

### 7. Select the face (first install only)
On the watch, long-press the current face, swipe to the end, tap **+ Add**, and pick the new face. You can also use the Galaxy Wearable app on your phone. Faces with settings have a **Customise** button when you long-press them.

You can turn Wireless debugging off afterwards. Installed faces stay installed.

## When something goes wrong
The watch face runtime logs errors such as bad expressions or missing images:
```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb logcat --pid=$(& $adb shell pidof -s com.google.wear.watchface.runtime)
```
Leave this running while you reproduce the problem, then paste the output to Claude.

**To remove a face:** in Android Studio's terminal, run `& $adb uninstall <applicationId>`, using the `applicationId` from the face's `watchface/build.gradle.kts`.
