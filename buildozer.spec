[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,json,txt
version = 6.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
home_app = True

android.api = 36
android.minapi = 24
android.ndk = 28b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

android.debug_artifact = apk
android.release_artifact = aab

# Use Buildozer's current python-for-android unless a later compatibility pin is required.
p4a.branch = develop
p4a.commit = d2ee8c5
