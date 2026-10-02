[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,json,txt
icon.filename = icon.png
version = 7.1
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.home_app = True

android.api = 35
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

android.debug_artifact = apk
android.release_artifact = aab

# Use Buildozer/python-for-android current stable defaults.
p4a.bootstrap = sdl2
