[app]

# Title
title = MPAPS Controller

# Package
package.name = mpaps
package.domain = org.mpaps

# 🔥 FIX PENTING (WAJIB)
source.dir = .

# Include files
source.include_exts = py,png,jpg,kv,atlas

# Version
version = 1.0.0

# 🔥 REQUIREMENTS (SUDAH AMAN)
requirements = python3,kivy==2.3.0,websocket-client,setuptools

# Orientation
orientation = portrait

# Fullscreen
fullscreen = 0

# 🔥 PERMISSION (DITAMBAH)
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# API
android.api = 33
android.minapi = 21

# Accept license
android.accept_sdk_license = True

# Architecture
android.arch = arm64-v8a

# Bootstrap
android.bootstrap = sdl2

# Python for Android
p4a.branch = master

# Logging
log_level = 2
warn_on_root = 1


[buildozer]

log_level = 2
warn_on_root = 1