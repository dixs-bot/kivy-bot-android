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
source.include_exts = py,png,jpg,kv,atlas,ttf

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# Dihilangkan ==3.10.13 agar buildozer mencari versi yang cocok
requirements = python3,kivy==2.3.0,websocket-client

# (str) Supported orientation
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

# (str) Android architecture
android.arch = arm64-v8a

# (str) Bootstrap name to use (WAJIB SDL2)
android.bootstrap = sdl2

# (str) p4a branch to use
p4a.branch = master

# (int) Log level
log_level = 2

# (bool) Warn if buildozer.spec is older than the one in buildozer
warn_on_root = 1


[buildozer]

# (int) Log level
log_level = 2

# (int) Warn if buildozer.spec is older than the one in buildozer
warn_on_root = 1

# (str) Path to build output (i.e. .apk, .aab) storage
#bin_dir = ./bin