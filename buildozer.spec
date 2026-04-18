[app]

# (str) Title of your application
title = MPAPS Controller

# (str) Package name
package.name = mpaps

# (str) Package domain (needed for android/ios packaging)
package.domain = org.mpaps

# (str) Source code directory (relative to this file)
source.dir = android

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements (space separated, e.g. requirements = kivy==2.1.0)
requirements = python3,kivy==2.3.0,websocket-client

# (str) Supported orientation (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE

# (int) Target Android API level
android.api = 33

# (int) Minimum Android API level
android.minapi = 24

# (bool) Accept Android SDK license
android.accept_sdk_license = True

# (str) Android architecture to build for (armeabi-v7a, arm64-v8a, x86, x86_64)
android.arch = arm64-v8a

# (str) Bootstrap name to use (android only)
android.bootstrap = sdl2

# (str) p4a branch to use (master, develop, etc)
p4a.branch = master

# (int) Log level (0 = error only, 1 = info, 2 = debug (with commands), 3 = trace)
log_level = 2

# (bool) Warn if buildozer.spec is older than the one in buildozer
warn_on_root = 1


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with commands), 3 = trace)
log_level = 2

# (int) Warn if buildozer.spec is older than the one in buildozer
warn_on_root = 1

# (str) Path to build output (i.e. .apk, .aab) storage
#bin_dir = ./bin