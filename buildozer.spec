[app]
title = MPAPS Controller
package.name = mpaps
package.domain = org.mpaps
source.dir = android
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy==2.3.0,websocket-client
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.accept_sdk_license = True
android.arch = arm64-v8a
android.bootstrap = sdl2
p4a.branch = develop
p4a.blacklist_requirements = pyjnius
log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
#bin_dir = ./bin