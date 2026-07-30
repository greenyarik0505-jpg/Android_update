[app]
# (str) Title of your application
title = BrawlUpdaterAndroid

# (str) Package name
package.name = brawlupdater
package.domain = org.example

# (str) Source code where the main.py is located
source.dir = .
source.include_exts = py,png,jpg,kv

# (list) Application requirements
requirements = python3,kivy,requests

# (str) Supported orientation (default: all)
orientation = portrait

# (int) Android API to use
android.api = 31

# (int) Minimum API your APK will support
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 20

# (str) Android entry point, leaving default

# (list) Permissions
android.permissions = INTERNET

# (str) Package version
version = 0.1

# (bool) If True, the buildozer will not try to accept licenses interactively
android.accept_sdk_license = True


